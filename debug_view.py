import os
import django
import sys
from decimal import Decimal

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from rest_framework.test import APIRequestFactory, force_authenticate
from main.views import CashierCreateOfflineOrderView
from main.models import CustomUser, Table, MenuItem, OfflineOrder

# Create Factory
factory = APIRequestFactory()

# Get User (Cashier)
user = CustomUser.objects.filter(roles='cashier').first()
if not user:
    # Create temp cashier
    print("Creating temp cashier user...")
    user = CustomUser.objects.create_user(username='temp_cashier', password='password', roles='cashier')

# Get Table & Item
table = Table.objects.first()
item = MenuItem.objects.first()

print(f"Testing with User: {user.username}, Table: {table.id}, Item: {item.id}")

# Payload
data = {
    'table_id': table.id,
    'items': [
        {
            'item_id': item.id,
            'size_id': None,
            'quantity': 1
        }
    ],
    'is_imported': False
}

# Request
print("Sending Request to CashierCreateOfflineOrderView...")
request = factory.post('/api/cashier/create-order/', data, format='json')
force_authenticate(request, user=user)

view = CashierCreateOfflineOrderView.as_view()

try:
    response = view(request)
    print(f"Response Status: {response.status_code}")
    print(f"Response Data: {response.data}")
except Exception as e:
    import traceback
    print("\n!!! VIEW CRASHED !!!")
    print(traceback.format_exc())
