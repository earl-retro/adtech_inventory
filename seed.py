import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adtech.settings')
django.setup()

from django.contrib.auth import get_user_model
from customers.models import Customer
from inventory.models import Category, Supplier, Product, StockIn
from sales.models import Sale, SaleItem
import random

User = get_user_model()

def seed():
    # 1. Create Admin User
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@adtech.com', 'admin123')
        print("Admin user created (admin / admin123)")

    if not User.objects.filter(username='user').exists():
        User.objects.create_user('user', 'user@adtech.com', 'user123', role='user')
        print("User created (user / user123)")

    # 2. Categories
    cat_names = ['Laptops', 'Desktops', 'Accessories', 'Components']
    categories = []
    for name in cat_names:
        cat, _ = Category.objects.get_or_create(name=name)
        categories.append(cat)

    # 3. Suppliers
    suppliers = []
    for i in range(1, 4):
        sup, _ = Supplier.objects.get_or_create(name=f'Supplier {i}', contact_info=f'0912345678{i}')
        suppliers.append(sup)

    # 4. Products
    products = [
        {"name": "Gaming Laptop Pro", "cat": categories[0], "brand": "TechBrand", "cost": 45000, "sell": 55000, "stock": 10},
        {"name": "Office PC Setup", "cat": categories[1], "brand": "WorkTech", "cost": 20000, "sell": 25000, "stock": 15},
        {"name": "Wireless Mouse", "cat": categories[2], "brand": "ClickCorp", "cost": 500, "sell": 1200, "stock": 50},
        {"name": "Mechanical Keyboard", "cat": categories[2], "brand": "KeyMaster", "cost": 2000, "sell": 3500, "stock": 30},
        {"name": "1TB SSD", "cat": categories[3], "brand": "StoragePlus", "cost": 3000, "sell": 4500, "stock": 20},
        {"name": "16GB RAM", "cat": categories[3], "brand": "MemKing", "cost": 2500, "sell": 3800, "stock": 4}, # low stock!
    ]
    
    db_products = []
    for p in products:
        prod, _ = Product.objects.get_or_create(
            name=p['name'],
            defaults={
                'category': p['cat'],
                'brand': p['brand'],
                'cost_price': p['cost'],
                'selling_price': p['sell'],
                'stock_quantity': p['stock'],
                'reorder_level': 5
            }
        )
        db_products.append(prod)

    # 5. Customers
    customers = []
    for i in range(1, 6):
        c, _ = Customer.objects.get_or_create(
            full_name=f"Customer {i}",
            defaults={'contact_number': f'099988877{i}', 'email': f'customer{i}@example.com'}
        )
        customers.append(c)

    print("Seed data generated successfully.")

if __name__ == '__main__':
    seed()
