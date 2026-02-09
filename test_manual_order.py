import os
import django
import sys
from decimal import Decimal

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from main.models import Order, OrderItem, MenuItem, MenuItemSize

def create_test_manual_order():
    try:
        # Get a menu item
        item = MenuItem.objects.first()
        size = MenuItemSize.objects.filter(menu_item=item).first()
        
        print(f"Using item: {item.name}, size: {size.size if size else 'None'}")
        
        # Create order
        order = Order.objects.create(
            customer="Test Customer",
            phone="12345678",
            total=Decimal("700.00"),
            subtotal=Decimal("600.00"),
            tax_amount=Decimal("100.00"),
            order_type='delivery',
            items=[{
                'name': item.name,
                'quantity': 1,
                'price': float(size.price if size else item.price),
                'size': size.size if size else None
            }] # New format
        )
        print(f"Order #{order.id} created.")
        
        # Create OrderItem
        OrderItem.objects.create(
            order=order,
            item=item,
            size=size,
            quantity=1
        )
        print(f"OrderItem created for Order #{order.id}.")
        
        # Check print view logic
        order_items = OrderItem.objects.filter(order=order)
        print(f"OrderItem count via filter: {order_items.count()}")
        
        # Check fallback
        if not order_items.exists():
            print("FALLBACK would be used.")
            if isinstance(order.items, list) and len(order.items) > 0:
                print(f"Fallback item 0 price: {order.items[0].get('price')}")
        else:
            print("OrderItem logic would be used.")
            item0 = order_items.first()
            p = item0.size.price if item0.size else item0.item.price
            print(f"OrderItem price: {p}")

    except Exception as e:
        print(f"Error: {e}")

create_test_manual_order()
