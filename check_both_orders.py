import os
import django
import sys

# Setup Django environment FIRST
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

# THEN import models
from main.models import Order, OfflineOrder, OrderItem, OfflineOrderItem

def check_offline_order(order_id):
    try:
        order = OfflineOrder.objects.get(id=order_id)
        print(f"OFFLINE Order #{order.id} found.")
        print(f"  Status: {order.status}")
        print(f"  Total: {order.total}")
        
        items = OfflineOrderItem.objects.filter(offline_order=order)
        print(f"  OfflineOrderItem count: {items.count()}")
        
        for item in items:
            print(f"    - Item: {item.item.name}")
            print(f"      Size: {item.size.size if item.size else 'None'}")
            print(f"      Price: {item.price}") # OfflineOrderItem stores price directly
            
    except OfflineOrder.DoesNotExist:
        print(f"OFFLINE Order #{order_id} not found.")

def check_online_order(order_id):
    try:
        order = Order.objects.get(id=order_id)
        print(f"ONLINE Order #{order.id} found.")
        print(f"  Customer: {order.customer}")
        print(f"  Items (JSON): {order.items}")
        
        items = OrderItem.objects.filter(order=order)
        print(f"  OrderItem count: {items.count()}")
        
        if items.exists():
            for item in items:
                print(f"    - Item: {item.item.name}")
                if item.size:
                    print(f"      Size: {item.size.size} - Price: {item.size.price}")
                else:
                    print(f"      Item Price: {item.item.price}")
        else:
            print("  NO OrderItem records found.")
                
    except Order.DoesNotExist:
        print(f"ONLINE Order #{order_id} not found.")

print("Checking Order 22...")
check_online_order(22)
check_offline_order(22)

# Also search for 'Special Poulet Hache' just in case
print("\nSearching for 'Special Poulet Hache' in recent orders...")
recent_orders = Order.objects.filter(created_at__year=2026, created_at__month=2, created_at__day=9).order_by('-id')[:5]
# Assuming we can print items directly
for o in recent_orders:
    print(f"Order #{o.id}: {o.items}")
