
import json
from os.path import exists

class Product:
    def __init__(self, product_id: str, name: str, price: float, quantity_available:int):
        self._product_id = product_id
        self._name = name
        self._price = price
        self._quantity_available = quantity_available

    @property
    def show_product_id(self):
        return self._product_id

    @property
    def show_name(self):
        return self._name

    @property
    def show_price(self):
        return self._price

    @property
    def show_quantity_available(self):
        return self._quantity_available

    @show_quantity_available.setter
    def show_quantity_available(self, value):
        if value >= 0:
            self._quantity_available = value
        else:
            print("Quantity cannot be negative")

    def decrease_quantity(self, quantity: int) -> bool:
        if quantity > 0 and quantity <= self._quantity_available:
            self._quantity_available -= quantity
            return True
        return False

    def increase_quantity(self, quantity: int) -> None:
        if quantity > 0:
            self._quantity_available += quantity

    def display_details(self) -> str:
        return f"Product ID: {self._product_id}\nName: {self._name}\nPrice: ₹{self._price}\nStock: {self._quantity_available}\n"

    def to_dict(self) -> dict:
        return {
            "type": "product",
            "product_id": self._product_id,
            "name": self._name,
            "price": self._price,
            "quantity_available": self._quantity_available
        }

class PhysicalProduct(Product):
    def __init__(self, product_id, name, price, quantity_available, weight):
        super().__init__(product_id, name, price, quantity_available)
        self._weight = weight

    @property
    def weight(self):
        return self._weight

    def display_details(self) -> str:
        return f"{super().display_details()}Weight: {self.weight} Kg"

    def to_dict(self) -> dict:
        data = super().to_dict()
        data["type"] = "physical"
        data["weight"] = self._weight
        return data

class DigitalProduct(Product):
    def __init__(self, product_id, name, price, quantity_available, download_link):
        super().__init__(product_id, name, price, quantity_available)
        self._download_link = download_link

    @property
    def download_link(self):
        return self._download_link

    def display_details(self) -> str:
        return f"{super().display_details()}Download Link: {self.download_link}"

    def to_dict(self) -> dict:
        data = super().to_dict()
        data["type"] = "digital"
        data["download_link"] = self._download_link
        return data

class CartItem:
    def __init__(self, product: Product, quantity: int):
        self._product = product
        self._quantity = quantity

    @property
    def product(self):
        return self._product

    @property
    def quantity(self):
        return self._quantity

    @quantity.setter
    def quantity(self, value):
        if value < 0:
            raise ValueError("Quantity cannot be negative.")
        self._quantity = value

    def calculate_subtotal(self) -> float:
        return self._product.show_price * self._quantity

    def __str__(self) -> str:
        return (f"\nItem: {self._product.show_name}\nQuantity: {self._quantity}\nPrice: ₹{self._product.show_price:.2f}\nSubtotal: ₹{self.calculate_subtotal():.2f}")

    def to_dict(self) -> dict:
        return {
            "product_id": self._product.show_product_id,
            "quantity": self._quantity
        }

class ShoppingCart:
    
    def __init__(self, product_catalog_file='product.json', cart_state_file='cart.json'):
        self._product_catalog_file = product_catalog_file
        self._cart_state_file = cart_state_file
        self.catalog = self._load_catalog()
        self._items = {}
        self._load_cart_state()
        self._admin_username = "admin"
        self._admin_password = "admin123"


    def _load_catalog(self):
        catalog = {}
        if not exists(self._product_catalog_file):
            return catalog

        with open(self._product_catalog_file, 'r') as file:
            products = json.load(file)
            for p in products.values():
                p_type = p.get('type')
                if p_type == 'physical':
                    product = PhysicalProduct(
                        p["product_id"], p["name"], p["price"], p["quantity_available"], p["weight"]
                    )
                elif p_type == 'digital':
                    product = DigitalProduct(
                        p["product_id"], p["name"], p["price"], p["quantity_available"], p["download_link"]
                    )
                else:
                    product = Product(
                        p["product_id"], p["name"], p["price"], p["quantity_available"]
                    )
                catalog[product.show_product_id] = product
        return catalog


    def _load_cart_state(self):
        if not exists(self._cart_state_file):
            return
        with open(self._cart_state_file, 'r') as file:
            cart_data = json.load(file)
            for item in cart_data:
                pid = item['product_id']
                qty = item['quantity']
                product = self.catalog.get(pid)
                if product:
                    self._items[pid] = CartItem(product, qty)

    def _save_catalog(self):
        with open(self._product_catalog_file, 'w') as file:
            json.dump({p.show_product_id: p.to_dict() for p in self.catalog.values()}, file, indent=4)

    def _save_cart_state(self):
        with open(self._cart_state_file, 'w') as file:
            json.dump([item.to_dict() for item in self._items.values()], file, indent=4)

    def add_item(self, product_id, quantity):
        product = self.catalog.get(product_id)
        if not product or product.show_quantity_available < quantity:
            return False

        if product_id in self._items:
            self._items[product_id].quantity += quantity
        else:
            self._items[product_id] = CartItem(product, quantity)
        product.decrease_quantity(quantity)
        self._save_cart_state()
        self._save_catalog()
        return True

    def remove_item(self, product_id):
        if product_id in self._items:
            item = self._items.pop(product_id)
            item.product.increase_quantity(item.quantity)
            self._save_cart_state()
            self._save_catalog()
            return True
        return False

    def update_quantity(self, product_id, new_quantity):
        if product_id not in self._items or new_quantity < 0:
            return False

        item = self._items[product_id]
        delta = new_quantity - item.quantity

        if delta > 0 and item.product.show_quantity_available < delta:
            return False

        if delta > 0:
            item.product.decrease_quantity(delta)
        else:
            item.product.increase_quantity(-delta)

        item.quantity = new_quantity

        if new_quantity == 0:
            del self._items[product_id]

        self._save_cart_state()
        self._save_catalog()
        return True

    def get_total(self):
        return sum(item.calculate_subtotal() for item in self._items.values())

    def display_cart(self):
        if not self._items:
            print("Your cart is empty.")
            return

        for item in self._items.values():
            print(item)
        print(f"\nGrand Total: ₹{self.get_total():.2f}")

    def display_products(self):
        if not self.catalog:
            print("No products available.")
            return

        for product in self.catalog.values():
            print(product.display_details())
            print()
    
    def _input_or_menu(self, prompt):
        value = input(prompt).strip()
        if value.upper() == "MENU":
            return
        return value

    def add_product_to_store(self):
        print("\nAdd New Product to Store")
        print("----------------------------")
        p_type = input("Enter product type (physical/digital): ").strip().lower()

        if p_type not in ["physical", "digital"]:
            print("Invalid product type.")
            return
    
        product_id = input("Enter Product ID: ").strip()
        if product_id in self.catalog:
            print("Product ID already exists.")
            return

        name = input("Enter Product Name: ").strip()

        try:
            price = float(input("Enter Product Price (₹): "))
            quantity = int(input("Enter Quantity Available: "))
        except ValueError:
            print("Invalid numeric input.")
            return

        if p_type == "physical":
            try:
                weight = float(input("Enter Weight in Kg: "))
            except ValueError:
                print("Invalid weight.")
                return
            product = PhysicalProduct(product_id, name, price, quantity, weight)
        else:  # digital
            download_link = input("Enter Download Link: ").strip()
            product = DigitalProduct(product_id, name, price, quantity, download_link)

        self.catalog[product_id] = product
        self._save_catalog()
        print("Product added successfully!")

    def authenticate_admin(self):
        print("\nAdmin Authentication")
        username = input("Enter admin username: ").strip()
        password = input("Enter admin password: ").strip()

        if username == self._admin_username and password == self._admin_password:
            print("Authentication successful!")
            return True
        else:
            print("Authentication failed. Access denied.")
            return False

    def run(self):
        print("\nWelcome to the Online Shopping Cart!")

        while True:
            print("\n============= MENU =============\n")
            print("1. View Available Products")
            print("2. Add Item to Cart")
            print("3. View Cart")
            print("4. Update Item Quantity")
            print("5. Remove Item from Cart")
            print("6. Checkout")
            print("7. Add New Product to Store")
            print("8. Exit")
            print("\n================================\n")

            choice = input("Enter your choice (1-8): ")

            if choice == '1':
                self.display_products()

            elif choice == '2':
                product_id = self._input_or_menu("Enter Product ID to add (or type MENU to back to menu): ")
                if product_id is None:
                    continue
                
                qty_input = self._input_or_menu("Enter quantity: ")
                if qty_input is None:
                    continue

                try:
                    quantity = int(qty_input)

                    if self.add_item(product_id, quantity):
                        print("Item added to cart successfully.")
                    else:
                        print("Failed to add item. Check product ID or stock.")
                except ValueError:
                    print("Quantity must be a valid number.")

            elif choice == '3':
                self.display_cart()

            elif choice == '4':
                if not self._items:
                    print("Cart is empty. Nothing to update.")
                    continue
                product_id = self._input_or_menu("Enter Product ID to update (or type MENU to back to menu): ")
                if product_id is None:
                    continue

                qty_input = self._input_or_menu("Enter new quantity: ")
                if qty_input is None:
                   continue

                try:
                    new_quantity = int(qty_input)

                    if self.update_quantity(product_id, new_quantity):
                        print("Quantity updated successfully.")
                    else:
                        print("Failed to update quantity. Invalid input or stock issue.")
                except ValueError:
                    print("Quantity must be a valid number.")

            elif choice == '5':
                if not self._items:
                    print("Cart is empty. Nothing to remove.")
                    continue
                product_id = self._input_or_menu("Enter Product ID to remove (or type MENU to back to menu): ")
                if product_id is None:
                    continue

                if self.remove_item(product_id):
                    print("Item removed from cart.")
                else:
                    print("Item not found in cart.")

            elif choice == '6':
                total = self.get_total()
                print("\nFinal Cart Summary:")
                self.display_cart()
                print("Thank you for shopping with us!")
                
                self._items.clear()
                self._save_cart_state()

            elif choice == '8':
                print("Exiting program. Have a nice day!")
                break

            elif choice == '7':
                if self.authenticate_admin():
                    self.add_product_to_store()
                else:
                    print("Access denied. Returning to main menu.")

            else:
                print("Invalid choice. Please select a number between 1 and 7.")

cart = ShoppingCart()
cart.run()
