import os
import django
import sys

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from main.models import Order, OrderItem

try:
    order = Order.objects.get(id=22)
    print(f"Order #{order.id} found.")
    print(f"Customer: {order.customer}")
    print(f"Total: {order.total}")
    print(f"Items (JSON): {order.items}")
    
    order_items = OrderItem.objects.filter(order=order)
    print(f"OrderItem count: {order_items.count()}")
    
    if order_items.exists():
        for item in order_items:
            print(f"  - OrderItem ID: {item.id}")
            print(f"    Item: {item.item.name}")
            print(f"    Size: {item.size.size if item.size else 'None'}")
            if item.size:
                print(f"    Size Price: {item.size.price}")
            print(f"    Item Price: {item.item.price}")
    else:
        print("!! NO OrderItem records found !!")

except Order.DoesNotExist:
    print("Order #22 not found.")
except Exception as e:
    print(f"Error: {e}")
