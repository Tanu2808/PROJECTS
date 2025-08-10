import pandas as pd
import numpy as np
# import joblib
import os

INPUT_CSV = r"D:\Programming Projects\PROJECTS_\Customer Churn Prediction\Data\Telco_Customer_Chern_Cleaned.csv"
OUTPUT_DIR = r"D:\Programming Projects\PROJECTS_\Customer Churn Prediction\Data\processed"
OUTPUT_CSV = os.path.join(OUTPUT_DIR, "Telco_Customer_Churn_Featured.csv")
os.makedirs(OUTPUT_DIR, exist_ok = True)

def normalize_column_names(dataFrame):
    col_map = {c: c.strip().replace(' ','_').replace('(','').replace(')','') for c in dataFrame.columns}
    dataFrame = dataFrame.rename(columns = col_map)
    return dataFrame

def detect_scaled(dataFrame, cols = ['tenure','MonthlyCharges','TotalCharges']):
    scaled = {}
    for c in dataFrame.columns:
        mean = dataFrame[c].mean()
        std = dataFrame[c].std()
        scaled[c] = (abs(mean) < 1e-3 and abs(std - 1.0) < 1e-2)
    return scaled

def safe_divide(a, b, fill_with=0):
    with np.errstate(divide='ignore', invalid='ignore'):
        res = np.where(b!=0, a / b, np.nan)
    if fill_with is not None:
        res = np.where(np.isnan(res), fill_with, res)
    return res

def create_features(df):
    df = normalize_column_names(df)

    if 'Churn' not in df.columns:
        if 'Churn_Yes' in df.columns:
            df['Churn_Label'] = df['Churn_Yes'].map({1: 'Yes', 0: 'No', True: 'Yes', False: 'No'})
        else:
            possible = [c for c in df.columns if 'churn' in c.lower()]
            if possible:
                df['Churn_Label'] = df[possible[0]].astype(str)
            else:
                df['Churn_Label'] = 'Unknown'
    else:
        df['Churn_Label'] = df['Churn'].astype(str)

    scaled_flags = detect_scaled(df)
    if any(scaled_flags.values()):
        print("WARNING: Numeric columns seem scaled (means ~0, std ~1).")
        print("It's recommended to run feature engineering on unscaled raw numbers or re-create raw versions.")

    if 'TotalCharges' in df.columns and 'tenure' in df.columns:
        
        df['avg_charges_per_month'] = np.where(df['tenure'] > 0, df['TotalCharges'] / df['tenure'], df.get('MonthlyCharges', np.nan))
    else:
        df['avg_charges_per_month'] = np.nan

    if 'tenure' in df.columns:
        try:
            if df['tenure'].mean() > 5:  
                bins = [0, 12, 24, 48, 60, np.inf]
                labels = ['0-12', '13-24', '25-48', '49-60', '61+']
                df['tenure_group'] = pd.cut(df['tenure'], bins=bins, labels=labels, right=False)
            else:
                df['tenure_group'] = pd.qcut(df['tenure'].rank(method='first'), q=5, labels=['Q1','Q2','Q3','Q4','Q5'])
        except Exception as e:
            df['tenure_group'] = np.nan

    service_keys = ['PhoneService','MultipleLines','OnlineSecurity','OnlineBackup',
                    'DeviceProtection','TechSupport','StreamingTV','StreamingMovies']
    service_cols = []
    for k in service_keys:
        candidates = [c for c in df.columns if k in c]
        for c in candidates:
            if c.endswith('_Yes') or c.endswith('_True') or df[c].dropna().isin([True,1]).any():
                service_cols.append(c)
        if not any(k in c for c in service_cols) and candidates:
            service_cols.extend(candidates)

    service_cols = list(dict.fromkeys(service_cols))

    if not service_cols:
        boolean_cols = df.select_dtypes(include=['bool','int','int64']).columns.tolist()
        for c in boolean_cols:
            if any(k.lower() in c.lower() for k in service_keys):
                service_cols.append(c)
    if service_cols:
        df['num_services'] = df[service_cols].sum(axis=1)
    else:
        df['num_services'] = 0

    internet_cols = [c for c in df.columns if c.lower().startswith('internetservice')]
    if internet_cols:
        no_col = next((c for c in internet_cols if 'no' in c.lower()), None)
        if no_col:
            df['has_internet'] = ~df[no_col]
        else:
            df['has_internet'] = df[internet_cols].any(axis=1)

        fiber_col = next((c for c in internet_cols if 'fiber' in c.lower()), None)
        df['is_fiber'] = df.get(fiber_col, False)
    else:
        if 'InternetService' in df.columns:
            df['has_internet'] = df['InternetService'].apply(lambda x: False if str(x).lower() == 'no' else True)
            df['is_fiber'] = df['InternetService'].apply(lambda x: True if str(x).lower() == 'fiber optic' else False)
        else:
            df['has_internet'] = False
            df['is_fiber'] = False

    contract_cols = [c for c in df.columns if c.lower().startswith('contract')]
    if contract_cols:
        df['long_term_contract'] = df[[c for c in contract_cols if ('two' in c.lower() or 'one' in c.lower())]].any(axis=1)

        if 'Contract_Two_year' in df.columns or 'Contract_One_year' in df.columns:
            df['contract_term'] = np.where(df.get('Contract_Two_year', False), 'Two year',
                                 np.where(df.get('Contract_One_year', False), 'One year', 'Month-to-month'))
    else:
        if 'Contract' in df.columns:
            df['long_term_contract'] = df['Contract'].apply(lambda x: True if 'year' in str(x) else False)
        else:
            df['long_term_contract'] = False

    df['is_autopay'] = df.get('PaymentMethod_Credit_card_automatic', df.get('PaymentMethod_Credit_card_(automatic)', df.get('PaymentMethod_Credit_card_automatic', False)))

    df['is_autopay'] = df['is_autopay'].fillna(False)
    df['is_electronic_check'] = df.get('PaymentMethod_Electronic_check', False)
    df['is_electronic_check'] = df['is_electronic_check'].fillna(False)

    if 'Partner_Yes' in df.columns or 'Dependents_Yes' in df.columns:
        df['family_flag'] = df.get('Partner_Yes', False) | df.get('Dependents_Yes', False)
    else:
        df['family_flag'] = False

    if 'tenure' in df.columns and 'MonthlyCharges' in df.columns:
        df['tenure_x_monthly'] = df['tenure'] * df['MonthlyCharges']
        df['charges_per_service'] = df['MonthlyCharges'] / (df['num_services'] + 1)
    else:
        df['tenure_x_monthly'] = np.nan
        df['charges_per_service'] = np.nan

    bool_cols = [c for c in df.columns if df[c].dropna().isin([True, False, 0, 1]).all()]
    for c in bool_cols:
        df[c] = df[c].astype('Int64')

    return df

if __name__ == "__main__":
    df = pd.read_csv(INPUT_CSV)
    df_feat = create_features(df)
    df_feat.to_csv(OUTPUT_CSV, index=False)
    print("Saved featured dataset to:", OUTPUT_CSV)