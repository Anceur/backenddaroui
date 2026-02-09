import os
import django
import sys

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from main.models import Order, OrderItem

try:
    order_id = 72
    order = Order.objects.get(id=order_id)
    print(f"Order #{order.id} found.")
    print(f"Items (JSON): {order.items}")
    
    order_items = OrderItem.objects.filter(order=order)
    print(f"OrderItem count: {order_items.count()}")
    
    for item in order_items:
        print(f"  - Item: {item.item.name}, Price: {item.item.price}")

except Order.DoesNotExist:
    print(f"Order #{order_id} not found.")
except Exception as e:
    print(f"Error: {e}")
