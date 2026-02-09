"""
Cashier Manual Online Order Creation
Allows cashiers to manually create online orders (delivery/takeaway) with fixed 100 DA tax
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from decimal import Decimal
import logging

from .models import Order, OrderItem, MenuItem, MenuItemSize, ClientFidele
from .serializers import OrderSerializer
from .permissions import IsCashierOrAdmin

logger = logging.getLogger(__name__)


class CashierManualOrderCreateView(APIView):
    """
    Cashier endpoint for manually creating online orders
    """
    permission_classes = [IsAuthenticated, IsCashierOrAdmin]
    
    def post(self, request):
        """
        Create a new online order manually from the cashier panel
        Expected data: {
            "customer": "Customer Name",
            "phone": "Phone Number",
            "address": "Delivery Address" (optional for takeaway),
            "order_type": "delivery" or "takeaway",
            "items": [
                {
                    "menu_item_id": 1,
                    "size": "M",  # Size code matches MenuItemSize.size
                    "size_id": 10, # Optional: Specific MenuItemSize ID
                    "quantity": 2
                }
            ],
            "notes": "Special instructions" (optional),
            "loyalty_number": "LOYALTY123" (optional)
        }
        """
        try:
            data = request.data
            
            # Validate required fields
            required_fields = ['customer', 'phone', 'order_type', 'items']
            missing_fields = [field for field in required_fields if not data.get(field)]
            if missing_fields:
                return Response({
                    'error': 'Missing required fields',
                    'details': f'Required: {", ".join(missing_fields)}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate order type
            order_type = data.get('order_type')
            if order_type not in ['delivery', 'takeaway']:
                return Response({
                    'error': 'Invalid order type',
                    'details': 'Order type must be "delivery" or "takeaway"'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate address for delivery orders
            if order_type == 'delivery' and not data.get('address'):
                return Response({
                    'error': 'Address required',
                    'details': 'Delivery address is required for delivery orders'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate items
            items_data = data.get('items', [])
            if not items_data or len(items_data) == 0:
                return Response({
                    'error': 'No items provided',
                    'details': 'Order must have at least one item'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Calculate totals
            subtotal = Decimal('0.00')
            revenue = Decimal('0.00')
            items_list = []  # For JSONField
            order_items_to_create = []  # For OrderItem records
            
            for item_data in items_data:
                try:
                    menu_item_id = item_data.get('menu_item_id')
                    size_code = item_data.get('size')
                    size_id = item_data.get('size_id')
                    quantity = int(item_data.get('quantity', 1))
                    
                    if not menu_item_id or quantity <= 0:
                        return Response({
                            'error': 'Invalid item data',
                            'details': 'Each item must have menu_item_id and quantity > 0'
                        }, status=status.HTTP_400_BAD_REQUEST)
                    
                    # Fetch menu item
                    menu_item = MenuItem.objects.get(id=menu_item_id)
                    
                    # Fetch size (if applicable)
                    size = None
                    if size_id:
                         try:
                             size = MenuItemSize.objects.get(id=size_id)
                         except MenuItemSize.DoesNotExist:
                             # Fallback or error? Let's check if it belongs to item
                             logger.warning(f"Size ID {size_id} not found, trying fallback")
                    
                    if not size and size_code:
                        try:
                            size = MenuItemSize.objects.get(menu_item=menu_item, size=size_code)
                        except MenuItemSize.DoesNotExist:
                             pass
                             
                    # If still no size, try to find "Standard" or assume no size (use base price)
                    # NOTE: OrderItem model requires 'size' (ForeignKey to MenuItemSize) to be nullable if we want to support items without size.
                    # Assuming it IS nullable as per standard practice or handled by logic.
                    # If strictly required, we'd fail here. Assuming robust logic:
                    
                    if size:
                        item_price = size.price
                        item_cost = size.cost_price
                        size_str = f" ({size.size})"
                    else:
                        item_price = menu_item.price
                        item_cost = menu_item.cost_price
                        size_str = ""
                    
                    item_subtotal = item_price * quantity
                    item_revenue = (item_price - (item_cost or 0)) * quantity
                    
                    subtotal += item_subtotal
                    revenue += item_revenue
                    
                    # Add to items list as object instead of string for better ticket printing
                    items_list.append({
                        'name': menu_item.name,
                        'size': size.size if size else None,
                        'quantity': quantity,
                        'price': float(item_price)
                    })
                    
                    # Prepare OrderItem data
                    order_items_to_create.append({
                        'menu_item': menu_item,
                        'size': size,
                        'quantity': quantity,
                        'price': item_price
                    })
                    
                except MenuItem.DoesNotExist:
                    return Response({
                        'error': 'Invalid menu item',
                        'details': f'Menu item {menu_item_id} not found'
                    }, status=status.HTTP_404_NOT_FOUND)
                except (ValueError, TypeError) as e:
                    return Response({
                        'error': 'Invalid item data',
                        'details': str(e)
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # Fixed tax for online orders
            tax_amount = Decimal('100.00')
            total = subtotal + tax_amount
            
            # Handle loyalty number
            loyalty_number = data.get('loyalty_number', '').strip() or None
            loyal_customer = None
            if loyalty_number:
                try:
                    loyal_customer = ClientFidele.objects.get(loyalty_card_number=loyalty_number)
                except ClientFidele.DoesNotExist:
                    pass
            
            # Create order
            order = Order.objects.create(
                customer=data.get('customer'),
                phone=data.get('phone'),
                address=data.get('address', ''),
                order_type=order_type,
                items=items_list,
                subtotal=subtotal,
                tax_amount=tax_amount,
                total=total,
                revenue=revenue,
                notes=data.get('notes', ''),
                loyalty_number=loyalty_number,
                loyal_customer=loyal_customer,
                status='Confirmed',  # Manually created orders are pre-confirmed
                is_confirmed_cashier=True  # Mark as cashier-created
            )
            
            # Create OrderItem records
            for order_item_data in order_items_to_create:
                OrderItem.objects.create(
                    order=order,
                    item=order_item_data['menu_item'],
                    size=order_item_data['size'],
                    quantity=order_item_data['quantity']
                )
            
            logger.info(f"Cashier {request.user.email} created manual Order #{order.id} for {order.customer}")
            
            # Return created order
            serializer = OrderSerializer(order)
            return Response({
                'success': True,
                'order': serializer.data,
                'message': f'Order #{order.id} created successfully'
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error creating manual order: {e}", exc_info=True)
            return Response({
                'error': 'Failed to create order',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
