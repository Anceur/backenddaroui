import os
import django
import sys

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from main.models import Table, MenuItem, OfflineOrder, OfflineOrderItem
from decimal import Decimal
from django.contrib.auth import get_user_model

try:
    print("--- DEBUGGING DATA ---")
    
    # Get a table
    table = Table.objects.first()
    if not table:
        print("ERROR: No tables found!")
        table = Table.objects.create(number="1", capacity=4)
        print("Created Table 1")
    else:
        print(f"Using Table: {table.id} (Number: {table.number})")

    # Get a menu item
    item = MenuItem.objects.first()
    if not item:
        print("ERROR: No menu items found!")
        item = MenuItem.objects.create(name="Test Item", price=Decimal('100.00'), category="Main")
        print("Created Test Item")
    else:
        print(f"Using Item: {item.id} (Name: {item.name}, Price: {item.price})")

    # Simulate Views Logic Manually
    print("\n--- SIMULATING ORDER CREATION ---")
    
    try:
        from main.notification_utils import send_notification_to_role
        print("Imported notification_utils successfully")
    except ImportError as e:
        print(f"CRITICAL: Failed to import notification_utils: {e}")

    # Step 1: Create Order
    print("Attempting to create OfflineOrder...")
    offline_order = OfflineOrder.objects.create(
        table=table,
        status='Pending',
        is_confirmed_cashier=False,
        is_imported=False,
        total=Decimal('0.00')
    )
    print(f"Created OfflineOrder #{offline_order.id}")

    # Step 2: Create Item
    print(f"Creating item for order #{offline_order.id} with item #{item.id}")
    OfflineOrderItem.objects.create(
        offline_order=offline_order,
        item=item,
        quantity=1,
        price=item.price
    )
    print("Created OfflineOrderItem")

    # Step 3: Update Totals & Save (This triggers Signals!)
    print("Updating totals and Saving (Triggers Signals)...")
    offline_order.total = item.price
    offline_order.save()
    print("Saved Successfully!")
    
    # Step 4: Notifications (Explicit)
    print("Attempting Explicit Notification...")
    from main.notification_utils import send_notification_to_role
    send_notification_to_role(
        role='admin',
        notification_type='order',
        title=f"DEBUG ORDER #{offline_order.id}",
        message="Debug message",
        priority='medium',
        related_offline_order=offline_order
    )
    print("Explicit Notification Sent!")

    print("\nSUCCESS: Order creation flow works in script.")

except Exception as e:
    import traceback
    print("\n!!! CRASH DETECTED !!!")
    print(traceback.format_exc())
