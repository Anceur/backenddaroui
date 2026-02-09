import os
import django
import sys

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from main.models import Order

print("Searching for 'Special Poulet Hache' in ALL orders...")
# Filter by JSON content containing the string
orders = Order.objects.filter(items__icontains="Special Poulet Hache")
print(f"Found {orders.count()} orders.")

for o in orders:
    print(f"Order #{o.id} - Date: {o.created_at}")
    print(f"  Items: {o.items}")
