import os
import django
import sys

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from main.models import Order

print("Listing last 10 orders:")
orders = Order.objects.all().order_by('-id')[:10]
for o in orders:
    print(f"Order #{o.id} - {o.created_at}")
    print(f"  Items: {o.items}")
    print(f"  Total: {o.total}")
