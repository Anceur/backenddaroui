import os
import django
import sys
from datetime import date

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from main.models import Order, OrderItem

try:
    today = date.today()
    print(f"Searching for orders created today ({today})...")
    
    orders = Order.objects.filter(created_at__date=today).order_by('-id')
    print(f"Found {orders.count()} orders today.")
    
    for order in orders:
        if "Special Poulet Hache" in str(order.items):
            print(f"MATCH FOUND: Order #{order.id}")
            print(f"  Customer: {order.customer}")
            print(f"  Items (JSON): {order.items}")
            
            order_items = OrderItem.objects.filter(order=order)
            print(f"  OrderItem count: {order_items.count()}")
            if order_items.exists():
                for item in order_items:
                    print(f"    - Item: {item.item.name}")
                    print(f"      Size: {item.size.size if item.size else 'None'}")
                    if item.size:
                        print(f"      Size Price: {item.size.price}")
                    else:
                        print(f"      Item Price: {item.item.price}")
            else:
                print("    !! NO OrderItem records found !!")
            print("-" * 30)

except Exception as e:
    print(f"Error: {e}")
