from django.shortcuts import render
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import (
    CustomTokenObtainPairSerializer, ProfileSerializer, UserWithProfileSerializer, 
    OrderSerializer, MenuItemSerializer, MenuItemSizeSerializer, OrderItemSerializer,
    IngredientSerializer, MenuItemIngredientSerializer, MenuItemSizeIngredientSerializer,
    IngredientStockSerializer, IngredientTraceSerializer, TableSerializer,
    OfflineOrderSerializer, OfflineOrderItemSerializer, TableSessionSerializer
)
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from .serializers import UserSerializer
from django.contrib.auth.hashers import check_password
from .permissions import IsAdmin, IsChefOrAdmin, IsCashier
from .models import (
    Profile, CustomUser, Order, MenuItem, MenuItemSize, OrderItem, 
    Ingredient, MenuItemIngredient, MenuItemSizeIngredient, IngredientStock, IngredientTrace,
    Table, OfflineOrder, OfflineOrderItem, TableSession
)
from django.db.models import Q, Count, Sum, Avg, F, DecimalField, Max, Min
from django.db.models.functions import TruncDate, TruncHour
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings as django_settings
from decimal import Decimal
import secrets
import hashlib
import logging
from .notification_utils import notify_order_confirmed_by_cashier

logger = logging.getLogger(__name__)
class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Extract tokens
        access_token = data['access']
        refresh_token = data['refresh']

        # Create response
        response = Response({
            'username': data['username'],
            'roles': data['roles'],
        }, status=status.HTTP_200_OK)

        # Set cookies
        # For development (localhost), use secure=False
        # For production, use secure=True
        is_secure = not django_settings.DEBUG  # Only secure in production
        
        response.set_cookie(
            "access_token",
            str(access_token),
            httponly=True,
            samesite="Lax" if django_settings.DEBUG else "None",  # Lax for localhost, None for cross-site
            secure=is_secure,
        )
        response.set_cookie(
            "refresh_token",
            str(refresh_token),
            httponly=True,
            samesite="Lax" if django_settings.DEBUG else "None",
            secure=is_secure,
        )


        return response
class CheckAuthenticatedView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        return Response({'message': 'You are authenticated'}, status=status.HTTP_200_OK)
class LogoutView(APIView):
    permission_classes = [IsAuthenticated ]
    def post(self, request):
        response = Response({'message': 'You are logged out'}, status=status.HTTP_200_OK)
        response.delete_cookie('access_token')
        response.delete_cookie('refresh_token')
        return response

class ReturnRole(APIView):
    permission_classes=[IsAuthenticated]
    def get(self, request):
        user = request.user
        role = getattr(user, "roles", None)
        return Response({"role": role})
class ReturnUser(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        serializer = UserSerializer(user)
        return Response(serializer.data)
class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        old_password = request.data.get("old_password")
        new_password = request.data.get("new_password")

        if not old_password or not new_password:
            return Response({"error": "Both old_password and new_password are required"}, status=status.HTTP_400_BAD_REQUEST)

        if not check_password(old_password, user.password):
            return Response({"error": "Old password is incorrect"}, status=status.HTTP_400_BAD_REQUEST)

        # Set the new password (this hashes it automatically)
        user.set_password(new_password)
        # Save with update_fields to ensure password is saved properly
        user.save(update_fields=['password'])
        
        # Refresh from database to ensure it's saved
        user.refresh_from_db()
        
        return Response({"success": "Password changed successfully"})
class ProfileView(APIView):
    permission_classes = [IsAuthenticated,IsAdmin]
    
    def get(self, request):
        user = request.user
        # Get or create profile for the user
        profile, created = Profile.objects.get_or_create(user=user)
        serializer = ProfileSerializer(profile)
        return Response(serializer.data)
    
    def post(self, request):
        user = request.user
        # Get or create profile for the user
        profile, created = Profile.objects.get_or_create(user=user)
        serializer = ProfileSerializer(profile, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request):
        """Full update of profile"""
        user = request.user
        try:
            profile = Profile.objects.get(user=user)
        except Profile.DoesNotExist:
            return Response({"error": "Profile not found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = ProfileSerializer(profile, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request):
        """Partial update of profile"""
        user = request.user
        try:
            profile = Profile.objects.get(user=user)
        except Profile.DoesNotExist:
            return Response({"error": "Profile not found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = ProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request):
        """Delete profile"""
        user = request.user
        try:
            profile = Profile.objects.get(user=user)
            profile.delete()
            return Response({"message": "Profile deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
        except Profile.DoesNotExist:
            return Response({"error": "Profile not found"}, status=status.HTTP_404_NOT_FOUND)

class CreateUserWithProfileView(APIView):
    """View for admin to create users with profiles"""
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def post(self, request):
        """Create a new user with profile"""
        serializer = UserWithProfileSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def get(self, request, user_id=None):
        """Get all users with their profiles or a specific user"""
        if user_id:
            try:
                user = CustomUser.objects.get(id=user_id)
                serializer = UserWithProfileSerializer(user, context={'request': request})
                return Response(serializer.data)
            except CustomUser.DoesNotExist:
                return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        
        users = CustomUser.objects.all()
        serializer = UserWithProfileSerializer(users, many=True, context={'request': request})
        return Response(serializer.data)
    
    def put(self, request, user_id):
        """Full update of user and profile"""
        try:
            user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = UserWithProfileSerializer(user, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request, user_id):
        """Partial update of user and profile"""
        try:
            user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = UserWithProfileSerializer(user, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, user_id):
        """Delete user and their profile"""
        try:
            user = CustomUser.objects.get(id=user_id)
            user.delete()  # This will cascade delete the profile
            return Response({"message": "User deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
        except CustomUser.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

class OrderListCreateView(APIView):
    """View for listing all orders and creating new orders"""
    permission_classes = [IsChefOrAdmin]
    
    def get_queryset(self):
        """Return queryset filtered by user role"""
        user = self.request.user
        if user.roles == 'chef':
            # Chef only sees confirmed orders
            return Order.objects.filter(
                status__in=['Pending', 'Preparing', 'Ready'],
                is_confirmed_cashier=True
            )
        return Order.objects.all()
        
    def get(self, request):
        """Get all orders with optional filtering"""
        try:
            orders = self.get_queryset()
            
            # Get query parameters with safe defaults
            status_filter = request.query_params.get('status', None)
            search = request.query_params.get('search', None)
            
            # Safely parse page and page_size with defaults
            try:
                page = int(request.query_params.get('page', 1))
                if page < 1:
                    page = 1
            except (ValueError, TypeError):
                page = 1
                
            try:
                page_size = int(request.query_params.get('page_size', 10))
                if page_size < 1:
                    page_size = 10
            except (ValueError, TypeError):
                page_size = 10
            
            # Apply status filter
            if status_filter and status_filter != 'All':
                orders = orders.filter(status=status_filter)
            
            # Apply search filter
            if search:
                search_clean = search.replace('#', '')
                orders = orders.filter(
                    Q(id__icontains=search_clean) |
                    Q(customer__icontains=search) |
                    Q(phone__icontains=search)
                )
            
            # Calculate pagination
            total_count = orders.count()
            start_index = (page - 1) * page_size
            end_index = start_index + page_size
            paginated_orders = orders[start_index:end_index]
            
            # Serialize orders
            serializer = OrderSerializer(paginated_orders, many=True)
            
            # Calculate total pages safely
            total_pages = (total_count + page_size - 1) // page_size if page_size > 0 else 0
            
            return Response({
                'orders': serializer.data,
                'total': total_count,
                'page': page,
                'page_size': page_size,
                'total_pages': total_pages
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            import traceback
            traceback.print_exc()  # Print full traceback for debugging
            return Response({
                'error': 'Failed to retrieve orders',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request):
        """Create a new order"""
        try:
            serializer = OrderSerializer(data=request.data)
            if serializer.is_valid():
                order = serializer.save()
                return Response(
                    OrderSerializer(order).data,
                    status=status.HTTP_201_CREATED
                )
            return Response({
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response({
                'error': 'Failed to create order',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class OrderDetailView(APIView):
    """View for retrieving, updating, or deleting a specific order"""
    permission_classes = [IsChefOrAdmin]
    
    def get_order(self, order_id):
        """Helper method to get order by ID with role-based access"""
        try:
            # Clean order_id - remove '#' if present
            if isinstance(order_id, str):
                order_id = order_id.replace('#', '').strip()
            order_id = int(order_id)
            
            order = Order.objects.get(id=order_id)
            
            # If user is chef, only allow access to Pending/Preparing/Ready orders
            # But also allow access if they're trying to update it (for status transitions)
            if self.request.user.roles == 'chef':
                if order.status not in ['Pending', 'Preparing', 'Ready', 'Delivered']:
                    return None
            return order
        except Order.DoesNotExist:
            return None
        except (ValueError, TypeError) as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error parsing order_id '{order_id}': {e}")
            return None
    
    def get(self, request, order_id):
        """Get a specific order by ID"""
        try:
            order = self.get_order(order_id)
            if order is None:
                return Response({
                    'error': 'Order not found or access denied'
                }, status=status.HTTP_404_NOT_FOUND)
            
            serializer = OrderSerializer(order)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': 'Failed to retrieve order',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    def patch(self, request, order_id):
        """Update order status (partial update)"""
        try:
            order = self.get_order(order_id)
            if order is None:
                return Response({
                    'error': 'Order not found or access denied'
                }, status=status.HTTP_404_NOT_FOUND)
                
            # Only allow updating status field for PATCH requests
            if 'status' not in request.data:
                return Response({
                    'error': 'Status field is required'
                }, status=status.HTTP_400_BAD_REQUEST)
                
            # For chefs, only allow updating status to 'Preparing', 'Ready', or 'Delivered'
            if request.user.roles == 'chef':
                if request.data['status'] not in ['Preparing', 'Ready', 'Delivered']:
                    return Response({
                        'error': 'Invalid status update for chef role'
                    }, status=status.HTTP_403_FORBIDDEN)
                
                # Only allow updating status in sequence: Pending -> Preparing -> Ready -> Delivered
                # Allow: Pending -> Preparing, Preparing -> Ready, Ready -> Delivered
                invalid_transitions = [
                    (order.status == 'Pending' and request.data['status'] == 'Ready'),
                    (order.status == 'Pending' and request.data['status'] == 'Delivered'),
                    (order.status == 'Ready' and request.data['status'] == 'Preparing'),
                    (order.status == 'Preparing' and request.data['status'] == 'Delivered'),
                    (order.status == 'Delivered' and request.data['status'] in ['Preparing', 'Ready']),
                ]
                
                if any(invalid_transitions):
                    return Response({
                        'error': f'Invalid status transition: Cannot change from {order.status} to {request.data["status"]}'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # Store the user who is updating the order for the signal
            order._updated_by_user = request.user
            
            # Mark if status is changing to 'Ready' for the signal
            old_status = order.status
            new_status = request.data['status']
            
            if new_status == 'Ready' and old_status != 'Ready':
                order._status_changed_to_ready = True
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"Order #{order.id} status changing from '{old_status}' to '{new_status}'")
            
            # Update the order status directly on the model to avoid serializer validation issues
            order.status = new_status
            order.save(update_fields=['status'])
            
            # Log after save to confirm signal should fire
            if new_status == 'Ready':
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"Order #{order.id} saved with status 'Ready', signal should fire")
            
            # Return the updated order
            serializer = OrderSerializer(order)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': 'Failed to update order status',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def put(self, request, order_id):
        """Full update of an order"""
        try:
            order = self.get_order(order_id)
            if order is None:
                return Response({
                    'error': 'Order not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            serializer = OrderSerializer(order, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            
            return Response({
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response({
                'error': 'Failed to update order',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def delete(self, request, order_id):
        """Delete an order"""
        try:
            order = self.get_order(order_id)
            if order is None:
                return Response({
                    'error': 'Order not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            order.delete()
            return Response({
                'message': 'Order deleted successfully'
            }, status=status.HTTP_204_NO_CONTENT)
            
        except Exception as e:
            return Response({
                'error': 'Failed to delete order',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class OrderStatusCountView(APIView):
    """View to get count of orders by status"""
    permission_classes = [IsChefOrAdmin]

    def get(self, request):
        """Get count of orders grouped by status"""
        try:
            # Get base queryset based on user role
            if request.user.roles == 'chef':
                # Chef only sees confirmed orders
                orders = Order.objects.filter(
                    status__in=['Pending', 'Preparing'],
                    is_confirmed_cashier=True
                )
            else:
                orders = Order.objects.all()
            
            status_counts = orders.values('status').annotate(count=Count('id'))
            
            # Convert to a dictionary for easier access
            counts_dict = {item['status'].lower(): item['count'] for item in status_counts}
            
            # Include all possible statuses, defaulting to 0 if not present
            result = {
                'all': sum(counts_dict.values()),
                'new': counts_dict.get('pending', 0),
                'preparing': counts_dict.get('preparing', 0),
                'ready': counts_dict.get('ready', 0),
                'delivered': counts_dict.get('delivered', 0) if request.user.roles != 'chef' else 0,
                'canceled': counts_dict.get('canceled', 0) if request.user.roles != 'chef' else 0
            }
            
            return Response(result, status=status.HTTP_200_OK)
                
        except Exception as e:
            import traceback
            traceback.print_exc()  # Print full traceback for debugging
            return Response({
                'error': 'Failed to retrieve order counts',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class PublicOrderCreateView(APIView):
    """Public endpoint for creating orders (no authentication required)"""
    permission_classes = [AllowAny]
    
    def get_authenticators(self):
        """Disable authentication for public order creation"""
        return []  # No authentication required
    
    def post(self, request):
        """Create a new order from client side"""
        try:
            # Prepare order data
            order_data = request.data.copy()
            
            # Store original items data BEFORE converting to strings (needed for OrderItem creation)
            original_items_data = request.data.get('items', [])
            
            # Ensure items is a list of item names/descriptions for the JSONField
            if 'items' in order_data:
                # If items is a list of objects, extract names
                if isinstance(order_data['items'], list) and len(order_data['items']) > 0:
                    if isinstance(order_data['items'][0], dict):
                        # Extract item names from cart items
                        items_list = []
                        for item in order_data['items']:
                            item_name = item.get('name', '')
                            quantity = item.get('quantity', 1)
                            if item_name:
                                items_list.append(f"{item_name} x{quantity}")
                        order_data['items'] = items_list
            
            # Set default values
            if 'order_type' not in order_data and 'orderType' not in order_data:
                order_data['order_type'] = 'delivery'
            if 'status' not in order_data:
                order_data['status'] = 'Pending'
            
            # Validate required fields
            required_fields = ['customer', 'phone', 'total']
            missing_fields = [field for field in required_fields if not order_data.get(field)]
            if missing_fields:
                return Response({
                    'error': 'Missing required fields',
                    'details': f'The following fields are required: {", ".join(missing_fields)}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate items
            items = order_data.get('items', [])
            if not items or len(items) == 0:
                return Response({
                    'error': 'Validation failed',
                    'details': {'items': ['Order must have at least one item']}
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate and round total to 2 decimal places
            try:
                total = float(order_data.get('total', 0))
                if total <= 0:
                    return Response({
                        'error': 'Validation failed',
                        'details': {'total': ['Total must be greater than zero']}
                    }, status=status.HTTP_400_BAD_REQUEST)
                # Round to 2 decimal places to avoid precision issues
                total = round(total, 2)
                order_data['total'] = total
            except (ValueError, TypeError):
                return Response({
                    'error': 'Validation failed',
                    'details': {'total': ['Total must be a valid number']}
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Create serializer and validate
            serializer = OrderSerializer(data=order_data)
            if serializer.is_valid():
                order = serializer.save()
                
                # Create OrderItem records from cart items
                # Cart items have id format: "menu_item_id" + "size" (e.g., "1M", "2L", "3Mega")
                # Use original_items_data which was saved before conversion to strings
                items_data = original_items_data if isinstance(original_items_data, list) else []
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"Creating OrderItems for Order #{order.id}, received {len(items_data)} items")
                
                if isinstance(items_data, list) and len(items_data) > 0:
                    from main.models import MenuItem, MenuItemSize, OrderItem
                    import re
                    
                    created_count = 0
                    failed_count = 0
                    
                    for item_data in items_data:
                        try:
                            # Parse cart item ID to extract menu_item_id and size
                            cart_item_id = str(item_data.get('id', ''))
                            quantity = item_data.get('quantity', 1)
                            
                            if not cart_item_id:
                                continue
                            
                            # Try to extract menu_item_id and size from ID
                            # Format: "menu_item_id" + "size" (e.g., "1M", "2L", "3Mega")
                            # Try to match: digits followed by optional size letters
                            # Also handle cases where size might be at the end: "1M", "2L", "3Mega"
                            match = re.match(r'^(\d+)(M|L|Mega)?$', cart_item_id)
                            
                            if match:
                                menu_item_id = int(match.group(1))
                                size_code = match.group(2)  # M, L, Mega, or None
                                
                                # Get menu item
                                menu_item = MenuItem.objects.get(id=menu_item_id)
                                
                                # Find MenuItemSize if size is specified
                                size = None
                                if size_code:
                                    try:
                                        size = MenuItemSize.objects.get(
                                            menu_item=menu_item,
                                            size=size_code
                                        )
                                        logger.info(f"Found MenuItemSize: {size.id} for {menu_item.name} size {size_code}")
                                    except MenuItemSize.DoesNotExist:
                                        # Try to find by matching size code
                                        size_map = {'M': 'M', 'L': 'L', 'Mega': 'Mega'}
                                        size_value = size_map.get(size_code, size_code)
                                        size = MenuItemSize.objects.filter(
                                            menu_item=menu_item,
                                            size=size_value
                                        ).first()
                                        if size:
                                            logger.info(f"Found MenuItemSize by filter: {size.id}")
                                        else:
                                            logger.warning(f"No MenuItemSize found for {menu_item.name} size {size_code}")
                                else:
                                    logger.info(f"No size code in cart item ID: {cart_item_id}, creating OrderItem without size")
                                
                                # Create OrderItem
                                order_item = OrderItem.objects.create(
                                    order=order,
                                    item=menu_item,
                                    size=size,
                                    quantity=quantity
                                )
                                created_count += 1
                                logger.info(f"Created OrderItem {order_item.id}: {menu_item.name} [{size_code or 'No size'}] x{quantity}")
                            else:
                                # If ID format doesn't match, try to find by name
                                item_name = item_data.get('name', '')
                                if item_name:
                                    try:
                                        menu_item = MenuItem.objects.filter(name__icontains=item_name).first()
                                        if menu_item:
                                            order_item = OrderItem.objects.create(
                                                order=order,
                                                item=menu_item,
                                                size=None,
                                                quantity=quantity
                                            )
                                            created_count += 1
                                            logger.info(f"Created OrderItem {order_item.id} by name: {menu_item.name} x{quantity}")
                                        else:
                                            failed_count += 1
                                            logger.warning(f"No MenuItem found matching name: {item_name}")
                                    except Exception as e:
                                        failed_count += 1
                                        logger.error(f"Error creating OrderItem by name: {e}")
                                else:
                                    failed_count += 1
                                    logger.warning(f"Cart item ID format doesn't match and no name provided: {cart_item_id}")
                                
                        except (MenuItem.DoesNotExist, ValueError, KeyError, TypeError) as e:
                            # Log error but don't fail the order creation
                            failed_count += 1
                            logger.error(f"Failed to create OrderItem for cart item {item_data.get('id', 'unknown')}: {e}", exc_info=True)
                    
                    logger.info(f"OrderItem creation summary for Order #{order.id}: {created_count} created, {failed_count} failed")
                
                # Return success response with order details
                return Response({
                    'success': True,
                    'message': 'Order placed successfully',
                    'order': OrderSerializer(order).data
                }, status=status.HTTP_201_CREATED)
            
            # Return validation errors
            return Response({
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({
                'error': 'Failed to create order',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OfflineOrderCreateView(APIView):
    """Public endpoint for creating offline orders (requires valid table session token)"""
    permission_classes = [AllowAny]
    
    def get_authenticators(self):
        """Disable authentication for public offline order creation"""
        return []
    
    def post(self, request):
        """Create a new offline order from table client"""
        try:
            import logging
            logger = logging.getLogger(__name__)
            
            # Get table number and token from request
            table_number = request.data.get('table_number') or request.data.get('tableNumber')
            token = request.data.get('token') or request.query_params.get('token')
            
            if not table_number:
                return Response({
                    'error': 'Missing required field',
                    'details': 'table_number is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate token if provided (security check)
            if token:
                try:
                    session = TableSession.objects.select_related('table').get(token=token)
                    if not session.is_valid():
                        return Response({
                            'error': 'Invalid session',
                            'details': 'Your table session has expired or is inactive. Please scan the QR code again.'
                        }, status=status.HTTP_403_FORBIDDEN)
                    
                    # Verify table number matches
                    if str(session.table.number) != str(table_number):
                        return Response({
                            'error': 'Token mismatch',
                            'details': 'Token does not match the specified table number.'
                        }, status=status.HTTP_400_BAD_REQUEST)
                    
                    # Mark session as having an order
                    session.order_placed = True
                    session.save(update_fields=['order_placed'])
                    
                    table = session.table
                except TableSession.DoesNotExist:
                    return Response({
                        'error': 'Invalid token',
                        'details': 'The provided token is not valid.'
                    }, status=status.HTTP_403_FORBIDDEN)
            else:
                # Get existing table only - do not create new tables
                try:
                    table = Table.objects.get(number=str(table_number))
                except Table.DoesNotExist:
                    return Response({
                        'error': 'Table not found',
                        'details': f'Table {table_number} does not exist. Please scan a valid QR code or contact staff.'
                    }, status=status.HTTP_404_NOT_FOUND)
            
            # Get items from request
            items_data = request.data.get('items', [])
            if not items_data or len(items_data) == 0:
                return Response({
                    'error': 'Validation failed',
                    'details': {'items': ['Order must have at least one item']}
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Calculate total
            try:
                total = float(request.data.get('total', 0))
                if total <= 0:
                    return Response({
                        'error': 'Validation failed',
                        'details': {'total': ['Total must be greater than zero']}
                    }, status=status.HTTP_400_BAD_REQUEST)
                total = round(total, 2)
            except (ValueError, TypeError):
                return Response({
                    'error': 'Validation failed',
                    'details': {'total': ['Total must be a valid number']}
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Create offline order
            offline_order = OfflineOrder.objects.create(
                table=table,
                total=total,
                status='Pending',
                notes=request.data.get('notes', '')
            )
            
            # Create offline order items
            created_count = 0
            failed_count = 0
            
            for item_data in items_data:
                try:
                    cart_item_id = str(item_data.get('id', ''))
                    quantity = item_data.get('quantity', 1)
                    price = float(item_data.get('price', 0))
                    
                    if not cart_item_id:
                        continue
                    
                    # Parse cart item ID: "menu_item_id" + "size" (e.g., "1M", "2L", "3Mega")
                    import re
                    match = re.match(r'^(\d+)([ML]|Mega)?$', cart_item_id)
                    if not match:
                        logger.warning(f"Could not parse cart item ID: {cart_item_id}")
                        failed_count += 1
                        continue
                    
                    menu_item_id = int(match.group(1))
                    size_code = match.group(2) if match.group(2) else None
                    
                    # Get menu item
                    try:
                        menu_item = MenuItem.objects.get(id=menu_item_id)
                    except MenuItem.DoesNotExist:
                        logger.warning(f"Menu item not found: {menu_item_id}")
                        failed_count += 1
                        continue
                    
                    # Get size if provided
                    size = None
                    if size_code:
                        try:
                            size = MenuItemSize.objects.get(menu_item=menu_item, size=size_code)
                            # Use size price if available
                            if size.price:
                                price = float(size.price)
                        except MenuItemSize.DoesNotExist:
                            logger.warning(f"Size not found for item {menu_item_id}: {size_code}")
                    
                    # Create offline order item
                    OfflineOrderItem.objects.create(
                        offline_order=offline_order,
                        item=menu_item,
                        size=size,
                        quantity=quantity,
                        price=price,
                        notes=item_data.get('notes', '')
                    )
                    created_count += 1
                    
                except Exception as e:
                    logger.error(f"Error creating offline order item: {e}", exc_info=True)
                    failed_count += 1
            
            logger.info(f"OfflineOrder #{offline_order.id} created: {created_count} items created, {failed_count} failed")
            
            # Mark table as occupied when order is created
            table.is_available = False
            table.save(update_fields=['is_available'])
            logger.info(f"Table {table.number} marked as occupied due to order #{offline_order.id}")
            
            # Return success response
            return Response({
                'success': True,
                'message': 'Offline order placed successfully',
                'order': OfflineOrderSerializer(offline_order).data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({
                'error': 'Failed to create offline order',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OfflineOrderListView(APIView):
    """View for listing offline orders (for chef panel)"""
    permission_classes = [IsAuthenticated, IsChefOrAdmin]
    
    def get(self, request):
        """Get all offline orders with optional filtering"""
        try:
            status_filter = request.query_params.get('status')
            
            queryset = OfflineOrder.objects.all().select_related('table').prefetch_related('items__item', 'items__size')
            
            # Chef only sees confirmed orders
            if request.user.roles == 'chef':
                queryset = queryset.filter(is_confirmed_cashier=True)
            
            if status_filter:
                queryset = queryset.filter(status=status_filter)
            
            # Order by creation time (newest first)
            queryset = queryset.order_by('-created_at')
            
            serializer = OfflineOrderSerializer(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({
                'error': 'Failed to retrieve offline orders',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OfflineOrderDetailView(APIView):
    """View for retrieving, updating, or deleting a specific offline order"""
    permission_classes = [IsAuthenticated, IsChefOrAdmin]
    
    def get(self, request, offline_order_id):
        """Get a specific offline order"""
        try:
            offline_order = OfflineOrder.objects.prefetch_related('items__item', 'items__size').get(id=offline_order_id)
            serializer = OfflineOrderSerializer(offline_order)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except OfflineOrder.DoesNotExist:
            return Response({
                'error': 'Offline order not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': 'Failed to retrieve offline order',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def patch(self, request, offline_order_id):
        """Update offline order status"""
        try:
            offline_order = OfflineOrder.objects.get(id=offline_order_id)
            new_status = request.data.get('status')
            
            if not new_status:
                return Response({
                    'error': 'Status is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate status
            valid_statuses = [choice[0] for choice in OfflineOrder.STATUS_CHOICES]
            if new_status not in valid_statuses:
                return Response({
                    'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Store the user who is updating the order for the signal
            offline_order._updated_by_user = request.user
            
            # Mark if status is changing to 'Ready' for the signal
            old_status = offline_order.status
            if new_status == 'Ready' and old_status != 'Ready':
                offline_order._status_changed_to_ready = True
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"OfflineOrder #{offline_order.id} status changing from '{old_status}' to '{new_status}'")
            
            # Update the order status directly on the model to avoid serializer validation issues
            offline_order.status = new_status
            offline_order.save(update_fields=['status'])
            
            # Note: Tables remain occupied until cashier manually frees them
            # Do not automatically unoccupy tables when orders are paid/canceled
            
            # Log after save to confirm signal should fire
            if new_status == 'Ready':
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"OfflineOrder #{offline_order.id} saved with status 'Ready', signal should fire")
            
            serializer = OfflineOrderSerializer(offline_order)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except OfflineOrder.DoesNotExist:
            return Response({
                'error': 'Offline order not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': 'Failed to update offline order',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MenuItemListCreateView(APIView):
    """View for listing all menu items and creating new menu items"""
    permission_classes = [AllowAny]  # Default to public, check manually in POST
    
    def get_authenticators(self):
        """Disable authentication for GET requests, enable for POST"""
        if self.request.method == 'GET':
            return []  # No authentication for GET
        # Use default authentication for POST
        return super().get_authenticators()
    
    def get(self, request):
        """Get all menu items (public access)"""
        try:
            menu_items = MenuItem.objects.all().order_by('id')
            serializer = MenuItemSerializer(menu_items, many=True, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({
                'error': 'Failed to retrieve menu items',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request):
        """Create a new menu item (chef or admin)"""
        # Check authentication and permission manually
        if not request.user.is_authenticated:
            return Response({
                'error': 'Authentication required',
                'detail': 'You must be logged in to create menu items'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        if not hasattr(request.user, 'roles') or request.user.roles not in ['admin', 'chef']:
            return Response({
                'error': 'Permission denied',
                'detail': 'Only administrators and chefs can create menu items'
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            serializer = MenuItemSerializer(data=request.data, context={'request': request})
            if serializer.is_valid():
                menu_item = serializer.save()
                return Response(
                    MenuItemSerializer(menu_item, context={'request': request}).data,
                    status=status.HTTP_201_CREATED
                )
            return Response({
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'error': 'Failed to create menu item',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class MenuItemDetailView(APIView):
    """View for retrieving, updating, or deleting a specific menu item"""
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get(self, request, item_id):
        """Get a specific menu item by ID"""
        try:
            menu_item = MenuItem.objects.get(id=item_id)
            serializer = MenuItemSerializer(menu_item, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except MenuItem.DoesNotExist:
            return Response({
                'error': 'Menu item not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': 'Failed to retrieve menu item',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def put(self, request, item_id):
        """Full update of a menu item"""
        try:
            menu_item = MenuItem.objects.get(id=item_id)
            serializer = MenuItemSerializer(menu_item, data=request.data, context={'request': request})
            if serializer.is_valid():
                menu_item = serializer.save()
                return Response(
                    MenuItemSerializer(menu_item, context={'request': request}).data,
                    status=status.HTTP_200_OK
                )
            return Response({
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except MenuItem.DoesNotExist:
            return Response({
                'error': 'Menu item not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': 'Failed to update menu item',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def patch(self, request, item_id):
        """Partial update of a menu item"""
        try:
            menu_item = MenuItem.objects.get(id=item_id)
            serializer = MenuItemSerializer(menu_item, data=request.data, partial=True, context={'request': request})
            if serializer.is_valid():
                menu_item = serializer.save()
                return Response(
                    MenuItemSerializer(menu_item, context={'request': request}).data,
                    status=status.HTTP_200_OK
                )
            return Response({
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except MenuItem.DoesNotExist:
            return Response({
                'error': 'Menu item not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': 'Failed to update menu item',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def delete(self, request, item_id):
        """Delete a menu item"""
        try:
            menu_item = MenuItem.objects.get(id=item_id)
            menu_item.delete()
            return Response({
                'message': 'Menu item deleted successfully'
            }, status=status.HTTP_204_NO_CONTENT)
        except MenuItem.DoesNotExist:
            return Response({
                'error': 'Menu item not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': 'Failed to delete menu item',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class PublicMenuItemListView(APIView):
    """Public endpoint for listing menu items (no authentication required)"""
    permission_classes = [AllowAny]
    
    def get_authenticators(self):
        """Disable authentication for public menu items listing"""
        return []  # No authentication required
    
    def get(self, request):
        """Get all menu items for public access"""
        try:
            menu_items = MenuItem.objects.all()
            serializer = MenuItemSerializer(menu_items, many=True, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({
                'error': 'Failed to retrieve menu items',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# MenuItemSize Views
class MenuItemSizeListCreateView(APIView):
    """View for listing all menu item sizes and creating new sizes"""
    permission_classes = [IsAuthenticated, IsChefOrAdmin]
    
    def get(self, request):
        """Get all menu item sizes"""
        try:
            sizes = MenuItemSize.objects.all()
            serializer = MenuItemSizeSerializer(sizes, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'error': 'Failed to retrieve menu item sizes',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request):
        """Create a new menu item size"""
        try:
            serializer = MenuItemSizeSerializer(data=request.data)
            if serializer.is_valid():
                size = serializer.save()
                return Response(
                    MenuItemSizeSerializer(size).data,
                    status=status.HTTP_201_CREATED
                )
            return Response({
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'error': 'Failed to create menu item size',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class MenuItemSizeDetailView(APIView):
    """View for retrieving, updating, or deleting a specific menu item size"""
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get(self, request, size_id):
        """Get a specific menu item size by ID"""
        try:
            size = MenuItemSize.objects.get(id=size_id)
            serializer = MenuItemSizeSerializer(size)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except MenuItemSize.DoesNotExist:
            return Response({
                'error': 'Menu item size not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': 'Failed to retrieve menu item size',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def put(self, request, size_id):
        """Full update of a menu item size"""
        try:
            size = MenuItemSize.objects.get(id=size_id)
            serializer = MenuItemSizeSerializer(size, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response({
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except MenuItemSize.DoesNotExist:
            return Response({
                'error': 'Menu item size not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': 'Failed to update menu item size',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def patch(self, request, size_id):
        """Partial update of a menu item size"""
        try:
            size = MenuItemSize.objects.get(id=size_id)
            serializer = MenuItemSizeSerializer(size, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response({
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except MenuItemSize.DoesNotExist:
            return Response({
                'error': 'Menu item size not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': 'Failed to update menu item size',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def delete(self, request, size_id):
        """Delete a menu item size"""
        try:
            size = MenuItemSize.objects.get(id=size_id)
            size.delete()
            return Response({
                'message': 'Menu item size deleted successfully'
            }, status=status.HTTP_204_NO_CONTENT)
        except MenuItemSize.DoesNotExist:
            return Response({
                'error': 'Menu item size not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': 'Failed to delete menu item size',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# OrderItem Views
class OrderItemListCreateView(APIView):
    """View for listing all order items and creating new order items"""
    permission_classes = [IsChefOrAdmin]
    
    def get(self, request):
        """Get all order items"""
        try:
            order_id = request.query_params.get('order', None)
            if order_id:
                # Remove '#' if present
                order_id = str(order_id).replace('#', '')
                order_items = OrderItem.objects.filter(order_id=order_id)
            else:
                order_items = OrderItem.objects.all()
            serializer = OrderItemSerializer(order_items, many=True, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'error': 'Failed to retrieve order items',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request):
        """Create a new order item"""
        try:
            serializer = OrderItemSerializer(data=request.data, context={'request': request})
            if serializer.is_valid():
                order_item = serializer.save()
                return Response(
                    OrderItemSerializer(order_item, context={'request': request}).data,
                    status=status.HTTP_201_CREATED
                )
            return Response({
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'error': 'Failed to create order item',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class OrderItemDetailView(APIView):
    """View for retrieving, updating, or deleting a specific order item"""
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get(self, request, item_id):
        """Get a specific order item by ID"""
        try:
            order_item = OrderItem.objects.get(id=item_id)
            serializer = OrderItemSerializer(order_item, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except OrderItem.DoesNotExist:
            return Response({
                'error': 'Order item not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': 'Failed to retrieve order item',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def put(self, request, item_id):
        """Full update of an order item"""
        try:
            order_item = OrderItem.objects.get(id=item_id)
            serializer = OrderItemSerializer(order_item, data=request.data, context={'request': request})
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response({
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except OrderItem.DoesNotExist:
            return Response({
                'error': 'Order item not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': 'Failed to update order item',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def patch(self, request, item_id):
        """Partial update of an order item"""
        try:
            order_item = OrderItem.objects.get(id=item_id)
            serializer = OrderItemSerializer(order_item, data=request.data, partial=True, context={'request': request})
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response({
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except OrderItem.DoesNotExist:
            return Response({
                'error': 'Order item not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': 'Failed to update order item',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def delete(self, request, item_id):
        """Delete an order item"""
        try:
            order_item = OrderItem.objects.get(id=item_id)
            order_item.delete()
            return Response({
                'message': 'Order item deleted successfully'
            }, status=status.HTTP_204_NO_CONTENT)
        except OrderItem.DoesNotExist:
            return Response({
                'error': 'Order item not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': 'Failed to delete order item',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Ingredient Views
class IngredientListCreateView(APIView):
    """View for listing all ingredients and creating new ingredients"""
    permission_classes = [IsAuthenticated, IsChefOrAdmin]
    
    def get(self, request):
        """Get all ingredients"""
        try:
            ingredients = Ingredient.objects.all()
            serializer = IngredientSerializer(ingredients, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'error': 'Failed to retrieve ingredients',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request):
        """Create a new ingredient"""
        try:
            serializer = IngredientSerializer(data=request.data)
            if serializer.is_valid():
                ingredient = serializer.save()
                return Response(
                    IngredientSerializer(ingredient).data,
                    status=status.HTTP_201_CREATED
                )
            return Response({
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'error': 'Failed to create ingredient',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class IngredientDetailView(APIView):
    """View for retrieving, updating, or deleting a specific ingredient"""
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get(self, request, ingredient_id):
        """Get a specific ingredient by ID"""
        try:
            ingredient = Ingredient.objects.get(id=ingredient_id)
            serializer = IngredientSerializer(ingredient)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Ingredient.DoesNotExist:
            return Response({
                'error': 'Ingredient not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': 'Failed to retrieve ingredient',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def put(self, request, ingredient_id):
        """Full update of an ingredient"""
        try:
            ingredient = Ingredient.objects.get(id=ingredient_id)
            serializer = IngredientSerializer(ingredient, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response({
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except Ingredient.DoesNotExist:
            return Response({
                'error': 'Ingredient not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': 'Failed to update ingredient',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def patch(self, request, ingredient_id):
        """Partial update of an ingredient"""
        try:
            ingredient = Ingredient.objects.get(id=ingredient_id)
            serializer = IngredientSerializer(ingredient, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response({
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except Ingredient.DoesNotExist:
            return Response({
                'error': 'Ingredient not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': 'Failed to update ingredient',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def delete(self, request, ingredient_id):
        """Delete an ingredient"""
        try:
            ingredient = Ingredient.objects.get(id=ingredient_id)
            ingredient.delete()
            return Response({
                'message': 'Ingredient deleted successfully'
            }, status=status.HTTP_204_NO_CONTENT)
        except Ingredient.DoesNotExist:
            return Response({
                'error': 'Ingredient not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': 'Failed to delete ingredient',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# MenuItemIngredient Views (for items without sizes)
class MenuItemIngredientListCreateView(APIView):
    """View for listing and creating menu item ingredients (for items without sizes)"""
    permission_classes = [IsAuthenticated, IsChefOrAdmin]
    
    def get(self, request):
        """Get all menu item ingredients"""
        try:
            menu_item_id = request.query_params.get('menu_item', None)
            if menu_item_id:
                item_ingredients = MenuItemIngredient.objects.filter(menu_item_id=menu_item_id)
            else:
                item_ingredients = MenuItemIngredient.objects.all()
            serializer = MenuItemIngredientSerializer(item_ingredients, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'error': 'Failed to retrieve menu item ingredients',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request):
        """Create a new menu item ingredient - chef or admin"""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            logger.info(f"Creating menu item ingredient. Request data: {request.data}")
            logger.info(f"Request user: {request.user}, Roles: {getattr(request.user, 'roles', 'N/A')}")
            
            serializer = MenuItemIngredientSerializer(data=request.data)
            logger.info(f"Serializer created. Validating...")
            
            if serializer.is_valid():
                logger.info(f"Serializer is valid. Data: {serializer.validated_data}")
                
                # Check for duplicate (unique_together constraint)
                menu_item_id = request.data.get('menu_item_id')
                ingredient_id = request.data.get('ingredient_id')
                logger.info(f"Checking for duplicates: menu_item_id={menu_item_id}, ingredient_id={ingredient_id}")
                
                if menu_item_id and ingredient_id:
                    existing = MenuItemIngredient.objects.filter(
                        menu_item_id=menu_item_id,
                        ingredient_id=ingredient_id
                    ).exists()
                    if existing:
                        logger.warning(f"Duplicate found: menu_item_id={menu_item_id}, ingredient_id={ingredient_id}")
                        return Response({
                            'error': 'This ingredient is already added to this menu item',
                            'details': {'non_field_errors': ['Ingredient already exists for this menu item']}
                        }, status=status.HTTP_400_BAD_REQUEST)
                
                logger.info("Saving menu item ingredient...")
                item_ingredient = serializer.save()
                logger.info(f"Menu item ingredient saved successfully. ID: {item_ingredient.id}")
                
                return Response(
                    MenuItemIngredientSerializer(item_ingredient).data,
                    status=status.HTTP_201_CREATED
                )
            else:
                logger.error(f"Serializer validation failed. Errors: {serializer.errors}")
                return Response({
                    'error': 'Validation failed',
                    'details': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            import traceback
            error_detail = str(e)
            logger.error(f"Exception in MenuItemIngredientListCreateView.post: {error_detail}")
            traceback.print_exc()
            # Check if it's a unique constraint violation
            if 'unique' in error_detail.lower() or 'already exists' in error_detail.lower():
                return Response({
                    'error': 'This ingredient is already added to this menu item',
                    'details': {'non_field_errors': ['Ingredient already exists for this menu item']}
                }, status=status.HTTP_400_BAD_REQUEST)
            return Response({
                'error': 'Failed to create menu item ingredient',
                'detail': error_detail,
                'details': {'exception': error_detail}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class MenuItemIngredientDetailView(APIView):
    """View for retrieving, updating, or deleting a specific menu item ingredient"""
    permission_classes = [IsAuthenticated, IsChefOrAdmin]
    
    def get(self, request, item_ingredient_id):
        """Get a specific menu item ingredient by ID"""
        try:
            item_ingredient = MenuItemIngredient.objects.get(id=item_ingredient_id)
            serializer = MenuItemIngredientSerializer(item_ingredient)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except MenuItemIngredient.DoesNotExist:
            return Response({
                'error': 'Menu item ingredient not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': 'Failed to retrieve menu item ingredient',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def delete(self, request, item_ingredient_id):
        """Delete a menu item ingredient"""
        try:
            item_ingredient = MenuItemIngredient.objects.get(id=item_ingredient_id)
            item_ingredient.delete()
            return Response({
                'message': 'Menu item ingredient deleted successfully'
            }, status=status.HTTP_200_OK)
        except MenuItemIngredient.DoesNotExist:
            return Response({
                'error': 'Menu item ingredient not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': 'Failed to delete menu item ingredient',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# MenuItemSizeIngredient Views
class MenuItemSizeIngredientListCreateView(APIView):
    """View for listing all menu item size ingredients and creating new ones"""
    permission_classes = [IsAuthenticated, IsChefOrAdmin]
    
    def get(self, request):
        """Get all menu item size ingredients - allowed for chefs and admins"""
        try:
            size_id = request.query_params.get('size', None)
            if size_id:
                size_ingredients = MenuItemSizeIngredient.objects.filter(size_id=size_id)
            else:
                size_ingredients = MenuItemSizeIngredient.objects.all()
            serializer = MenuItemSizeIngredientSerializer(size_ingredients, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'error': 'Failed to retrieve menu item size ingredients',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request):
        """Create a new menu item size ingredient - chef or admin"""
        # Check chef or admin permission for POST
        if not IsChefOrAdmin().has_permission(request, self):
            return Response({
                'error': 'Permission denied. Chef or admin access required.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            serializer = MenuItemSizeIngredientSerializer(data=request.data)
            if serializer.is_valid():
                size_ingredient = serializer.save()
                return Response(
                    MenuItemSizeIngredientSerializer(size_ingredient).data,
                    status=status.HTTP_201_CREATED
                )
            return Response({
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'error': 'Failed to create menu item size ingredient',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class MenuItemSizeIngredientDetailView(APIView):
    """View for retrieving, updating, or deleting a specific menu item size ingredient"""
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get(self, request, size_ingredient_id):
        """Get a specific menu item size ingredient by ID"""
        try:
            size_ingredient = MenuItemSizeIngredient.objects.get(id=size_ingredient_id)
            serializer = MenuItemSizeIngredientSerializer(size_ingredient)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except MenuItemSizeIngredient.DoesNotExist:
            return Response({
                'error': 'Menu item size ingredient not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': 'Failed to retrieve menu item size ingredient',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def put(self, request, size_ingredient_id):
        """Full update of a menu item size ingredient"""
        try:
            size_ingredient = MenuItemSizeIngredient.objects.get(id=size_ingredient_id)
            serializer = MenuItemSizeIngredientSerializer(size_ingredient, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response({
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except MenuItemSizeIngredient.DoesNotExist:
            return Response({
                'error': 'Menu item size ingredient not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': 'Failed to update menu item size ingredient',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def patch(self, request, size_ingredient_id):
        """Partial update of a menu item size ingredient"""
        try:
            size_ingredient = MenuItemSizeIngredient.objects.get(id=size_ingredient_id)
            serializer = MenuItemSizeIngredientSerializer(size_ingredient, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response({
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except MenuItemSizeIngredient.DoesNotExist:
            return Response({
                'error': 'Menu item size ingredient not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': 'Failed to update menu item size ingredient',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def delete(self, request, size_ingredient_id):
        """Delete a menu item size ingredient"""
        try:
            size_ingredient = MenuItemSizeIngredient.objects.get(id=size_ingredient_id)
            size_ingredient.delete()
            return Response({
                'message': 'Menu item size ingredient deleted successfully'
            }, status=status.HTTP_204_NO_CONTENT)
        except MenuItemSizeIngredient.DoesNotExist:
            return Response({
                'error': 'Menu item size ingredient not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': 'Failed to delete menu item size ingredient',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================
# TABLE MANAGEMENT ENDPOINTS
# ============================================

class TableListCreateView(APIView):
    """View for listing all tables and creating new tables"""
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get(self, request):
        """Get all tables"""
        try:
            tables = Table.objects.all().order_by('number')
            serializer = TableSerializer(tables, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'error': 'Failed to retrieve tables',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request):
        """Create a new table"""
        try:
            serializer = TableSerializer(data=request.data)
            if serializer.is_valid():
                table = serializer.save()
                return Response(
                    TableSerializer(table).data,
                    status=status.HTTP_201_CREATED
                )
            return Response({
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'error': 'Failed to create table',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PublicTableValidateView(APIView):
    """Public endpoint to validate if a table exists (for offline client)"""
    permission_classes = [AllowAny]
    
    def get_authenticators(self):
        """Disable authentication for public table validation"""
        return []
    
    def get(self, request):
        """Check if a table exists by number and if it's occupied"""
        try:
            table_number = request.query_params.get('number')
            
            if not table_number:
                return Response({
                    'error': 'Table number is required',
                    'details': 'Please provide a table number in the query parameter'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                table = Table.objects.get(number=str(table_number))
                
                # Use is_available as the primary source of truth
                # is_occupied is simply the inverse of is_available
                # Cashier has full control over table availability
                is_occupied = not table.is_available
                
                return Response({
                    'exists': True,
                    'is_occupied': is_occupied,
                    'table': {
                        'id': table.id,
                        'number': table.number,
                        'capacity': table.capacity,
                        'is_available': table.is_available,
                    }
                }, status=status.HTTP_200_OK)
            except Table.DoesNotExist:
                return Response({
                    'exists': False,
                    'message': f'Table {table_number} does not exist'
                }, status=status.HTTP_404_NOT_FOUND)
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({
                'error': 'Failed to validate table',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TableDetailView(APIView):
    """View for retrieving, updating, or deleting a specific table"""
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get(self, request, table_id):
        """Get a specific table"""
        try:
            table = Table.objects.get(id=table_id)
            serializer = TableSerializer(table)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Table.DoesNotExist:
            return Response({
                'error': 'Table not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': 'Failed to retrieve table',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def patch(self, request, table_id):
        """Update a table"""
        try:
            table = Table.objects.get(id=table_id)
            serializer = TableSerializer(table, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response({
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except Table.DoesNotExist:
            return Response({
                'error': 'Table not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': 'Failed to update table',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def delete(self, request, table_id):
        """Delete a table"""
        try:
            table = Table.objects.get(id=table_id)
            table.delete()
            return Response({
                'message': 'Table deleted successfully'
            }, status=status.HTTP_204_NO_CONTENT)
        except Table.DoesNotExist:
            return Response({
                'error': 'Table not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': 'Failed to delete table',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




# ============================================
# DASHBOARD STATISTICS ENDPOINT
# ============================================

class DashboardStatsView(APIView):
    """View for dashboard statistics"""
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get(self, request):
        """Get dashboard statistics"""
        try:
            today = datetime.now().date()
            start_of_today = datetime.combine(today, datetime.min.time())
            end_of_today = datetime.combine(today, datetime.max.time())
            
            # Orders today
            orders_today = Order.objects.filter(created_at__date=today)
            orders_today_count = orders_today.count()
            
            # Revenue today (from both online and offline orders)
            revenue_online = orders_today.filter(status__in=['Ready', 'Delivered']).aggregate(
                total=Sum('total', output_field=DecimalField(max_digits=15, decimal_places=2))
            )['total'] or 0
            
            revenue_offline = OfflineOrder.objects.filter(
                created_at__date=today,
                status__in=['Ready', 'Served', 'Paid']
            ).aggregate(
                total=Sum('total', output_field=DecimalField(max_digits=15, decimal_places=2))
            )['total'] or 0
            
            revenue_today = float(revenue_online) + float(revenue_offline)
            
            # Pending orders
            pending_orders = Order.objects.filter(status='Pending').count()
            pending_offline = OfflineOrder.objects.filter(status='Pending').count()
            pending_total = pending_orders + pending_offline
            
            # Active staff (users with roles)
            active_staff = CustomUser.objects.filter(roles__in=['chef', 'cashier', 'admin']).count()
            
            # Recent orders (last 10)
            recent_orders = Order.objects.order_by('-created_at')[:10].values(
                'id', 'customer', 'status', 'total', 'created_at', 'order_type'
            )
            
            # Top selling items (last 7 days)
            seven_days_ago = today - timedelta(days=7)
            top_items = OrderItem.objects.filter(
                order__created_at__gte=seven_days_ago
            ).values('item__name').annotate(
                total_quantity=Sum('quantity')
            ).order_by('-total_quantity')[:5]
            
            # Orders by status
            orders_by_status = Order.objects.values('status').annotate(
                count=Count('id')
            )
            
            offline_by_status = OfflineOrder.objects.values('status').annotate(
                count=Count('id')
            )
            
            # Combine status counts
            status_counts = {}
            for item in orders_by_status:
                status_counts[item['status']] = status_counts.get(item['status'], 0) + item['count']
            for item in offline_by_status:
                status_counts[item['status']] = status_counts.get(item['status'], 0) + item['count']
            
            # Low stock ingredients
            low_stock_ingredients = Ingredient.objects.filter(
                stock__lte=F('reorder_level')
            ).values('id', 'name', 'stock', 'reorder_level', 'unit')
            
            return Response({
                'orders_today': orders_today_count,
                'revenue_today': round(revenue_today, 2),
                'pending_orders': pending_total,
                'active_staff': active_staff,
                'recent_orders': list(recent_orders),
                'top_items': list(top_items),
                'status_counts': status_counts,
                'low_stock_ingredients': list(low_stock_ingredients),
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({
                'error': 'Failed to retrieve dashboard statistics',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================
# ANALYTICS ENDPOINTS
# ============================================

class AnalyticsView(APIView):
    """View for analytics data"""
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get(self, request):
        """Get analytics data"""
        try:
            # Get date range from query params (default: last 30 days)
            days = int(request.query_params.get('days', 30))
            start_date = datetime.now().date() - timedelta(days=days)
            
            # Sales over time
            sales_data = Order.objects.filter(
                created_at__date__gte=start_date,
                status__in=['Ready', 'Delivered']
            ).annotate(
                date=TruncDate('created_at')
            ).values('date').annotate(
                total=Sum('total', output_field=DecimalField(max_digits=15, decimal_places=2)),
                count=Count('id')
            ).order_by('date')
            
            # Offline sales
            offline_sales = OfflineOrder.objects.filter(
                created_at__date__gte=start_date,
                status__in=['Ready', 'Served', 'Paid']
            ).annotate(
                date=TruncDate('created_at')
            ).values('date').annotate(
                total=Sum('total', output_field=DecimalField(max_digits=15, decimal_places=2)),
                count=Count('id')
            ).order_by('date')
            
            # Combine sales data
            sales_by_date = {}
            for item in sales_data:
                date_str = item['date'].isoformat() if item['date'] else None
                if date_str:
                    if date_str not in sales_by_date:
                        sales_by_date[date_str] = {'total': 0, 'count': 0}
                    sales_by_date[date_str]['total'] += float(item['total'] or 0)
                    sales_by_date[date_str]['count'] += item['count']
            
            for item in offline_sales:
                date_str = item['date'].isoformat() if item['date'] else None
                if date_str:
                    if date_str not in sales_by_date:
                        sales_by_date[date_str] = {'total': 0, 'count': 0}
                    sales_by_date[date_str]['total'] += float(item['total'] or 0)
                    sales_by_date[date_str]['count'] += item['count']
            
            # Top selling items
            top_items = OrderItem.objects.filter(
                order__created_at__date__gte=start_date
            ).values('item__name', 'item__category').annotate(
                total_quantity=Sum('quantity'),
                total_revenue=Sum(F('order__total') * F('quantity') / F('order__items__count'), output_field=DecimalField(max_digits=15, decimal_places=2))
            ).order_by('-total_quantity')[:10]
            
            # Top offline items
            offline_top_items = OfflineOrderItem.objects.filter(
                offline_order__created_at__date__gte=start_date
            ).values('item__name', 'item__category').annotate(
                total_quantity=Sum('quantity'),
                total_revenue=Sum(F('price') * F('quantity'), output_field=DecimalField(max_digits=15, decimal_places=2))
            ).order_by('-total_quantity')[:10]
            
            # Combine top items
            combined_items = {}
            for item in top_items:
                name = item['item__name']
                if name not in combined_items:
                    combined_items[name] = {
                        'name': name,
                        'category': item['item__category'],
                        'total_quantity': 0,
                        'total_revenue': 0
                    }
                combined_items[name]['total_quantity'] += item['total_quantity'] or 0
                combined_items[name]['total_revenue'] += float(item['total_revenue'] or 0)
            
            for item in offline_top_items:
                name = item['item__name']
                if name not in combined_items:
                    combined_items[name] = {
                        'name': name,
                        'category': item['item__category'],
                        'total_quantity': 0,
                        'total_revenue': 0
                    }
                combined_items[name]['total_quantity'] += item['total_quantity'] or 0
                combined_items[name]['total_revenue'] += float(item['total_revenue'] or 0)
            
            top_items_list = sorted(combined_items.values(), key=lambda x: x['total_quantity'], reverse=True)[:10]
            
            # Orders by hour (peak hours)
            orders_by_hour = Order.objects.filter(
                created_at__date__gte=start_date
            ).annotate(
                hour=TruncHour('created_at')
            ).values('hour').annotate(
                count=Count('id')
            ).order_by('hour')
            
            # Average order value
            avg_order_value = Order.objects.filter(
                created_at__date__gte=start_date,
                status__in=['Ready', 'Delivered']
            ).aggregate(
                avg=Avg('total', output_field=DecimalField(max_digits=15, decimal_places=2))
            )['avg'] or 0
            
            avg_offline_value = OfflineOrder.objects.filter(
                created_at__date__gte=start_date,
                status__in=['Ready', 'Served', 'Paid']
            ).aggregate(
                avg=Avg('total', output_field=DecimalField(max_digits=15, decimal_places=2))
            )['avg'] or 0
            
            # Combine averages
            total_orders = Order.objects.filter(
                created_at__date__gte=start_date,
                status__in=['Ready', 'Delivered']
            ).count() + OfflineOrder.objects.filter(
                created_at__date__gte=start_date,
                status__in=['Ready', 'Served', 'Paid']
            ).count()
            
            total_revenue = sum([v.get('total', 0) for v in sales_by_date.values()]) if sales_by_date else 0
            overall_avg = float(total_revenue) / total_orders if total_orders > 0 else 0
            
            return Response({
                'sales_by_date': [{'date': k, **v} for k, v in sales_by_date.items()],
                'top_items': top_items_list,
                'orders_by_hour': list(orders_by_hour),
                'average_order_value': round(overall_avg, 2),
                'total_revenue': round(total_revenue, 2),
                'total_orders': total_orders,
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({
                'error': 'Failed to retrieve analytics data',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================
# CUSTOMERS ENDPOINT
# ============================================

class CustomersListView(APIView):
    """View for listing customers (aggregated from orders)"""
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get(self, request):
        """Get all customers with their order statistics"""
        try:
            # Aggregate customers from orders
            customers_data = Order.objects.values('customer', 'phone', 'address').annotate(
                total_orders=Count('id'),
                total_spent=Sum('total', output_field=DecimalField(max_digits=15, decimal_places=2)),
                last_order_date=Max('created_at'),
                first_order_date=Min('created_at')
            ).order_by('-total_spent')
            
            # Format the data
            customers = []
            for customer in customers_data:
                customers.append({
                    'name': customer['customer'],
                    'phone': customer['phone'],
                    'address': customer['address'],
                    'total_orders': customer['total_orders'],
                    'total_spent': float(customer['total_spent'] or 0),
                    'last_order_date': customer['last_order_date'].isoformat() if customer['last_order_date'] else None,
                    'first_order_date': customer['first_order_date'].isoformat() if customer['first_order_date'] else None,
                })
            
            return Response({
                'customers': customers,
                'total': len(customers)
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({
                'error': 'Failed to retrieve customers',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================
# OFFLINE ORDERS ADMIN VIEW
# ============================================

class OfflineOrderAdminListView(APIView):
    """Admin view for listing all offline orders with full access"""
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get(self, request):
        """Get all offline orders with optional filtering"""
        try:
            status_filter = request.query_params.get('status')
            search = request.query_params.get('search')
            
            queryset = OfflineOrder.objects.all().select_related('table').prefetch_related('items__item', 'items__size')
            
            if status_filter and status_filter != 'All':
                queryset = queryset.filter(status=status_filter)
            
            if search:
                queryset = queryset.filter(
                    Q(table__number__icontains=search) |
                    Q(id__icontains=search)
                )
            
            # Order by creation time (newest first)
            queryset = queryset.order_by('-created_at')
            
            serializer = OfflineOrderSerializer(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({
                'error': 'Failed to retrieve offline orders',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================
# TABLE SESSION & SECURITY ENDPOINTS
# ============================================

class TableSessionGenerateView(APIView):
    """Generate a secure token for table access (Admin only)"""
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def post(self, request):
        """Generate a new session token for a table"""
        try:
            table_id = request.data.get('table_id')
            table_number = request.data.get('table_number')
            duration_hours = int(request.data.get('duration_hours', 2))  # Default 2 hours
            
            if not table_id and not table_number:
                return Response({
                    'error': 'Validation failed',
                    'details': {'table': ['table_id or table_number is required']}
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get table
            try:
                if table_id:
                    table = Table.objects.get(id=table_id)
                else:
                    table = Table.objects.get(number=table_number)
            except Table.DoesNotExist:
                return Response({
                    'error': 'Table not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Deactivate any existing active sessions for this table
            TableSession.objects.filter(
                table=table,
                is_active=True
            ).update(is_active=False)
            
            # Generate secure token
            token = secrets.token_urlsafe(32)  # 32 bytes = 43 characters base64
            
            # Calculate expiration
            expires_at = timezone.now() + timedelta(hours=duration_hours)
            
            # Get client info
            ip_address = self._get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')[:255]
            
            # Create session
            session = TableSession.objects.create(
                table=table,
                token=token,
                expires_at=expires_at,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            # Mark table as in use
            table.is_available = False
            table.save()
            
            # Generate QR code URL
            qr_url = f"{request.scheme}://{request.get_host()}/{table.number}?token={token}"
            
            return Response({
                'success': True,
                'session': TableSessionSerializer(session).data,
                'token': token,
                'qr_url': qr_url,
                'expires_at': expires_at.isoformat(),
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({
                'error': 'Failed to generate table session',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class TableSessionValidateView(APIView):
    """Validate a table session token (Public endpoint with rate limiting)"""
    permission_classes = [AllowAny]
    
    def get_authenticators(self):
        """Disable authentication for token validation"""
        return []
    
    def post(self, request):
        """Validate a table session token"""
        try:
            token = request.data.get('token')
            table_number = request.data.get('table_number')
            
            if not token:
                return Response({
                    'error': 'Validation failed',
                    'details': {'token': ['Token is required']}
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Rate limiting check
            ip_address = self._get_client_ip(request)
            cache_key = f'table_session_validate_{ip_address}'
            attempts = cache.get(cache_key, 0)
            
            if attempts >= 10:  # Max 10 attempts per minute
                return Response({
                    'error': 'Rate limit exceeded',
                    'details': 'Too many validation attempts. Please try again later.'
                }, status=status.HTTP_429_TOO_MANY_REQUESTS)
            
            cache.set(cache_key, attempts + 1, 60)  # 1 minute window
            
            # Get session
            try:
                session = TableSession.objects.select_related('table').get(token=token)
            except TableSession.DoesNotExist:
                return Response({
                    'error': 'Invalid token',
                    'details': 'The provided token is not valid or has been revoked.'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Validate table number if provided
            if table_number and str(session.table.number) != str(table_number):
                return Response({
                    'error': 'Token mismatch',
                    'details': 'Token does not match the specified table number.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if session is valid
            if not session.is_valid():
                if session.is_expired():
                    return Response({
                        'error': 'Session expired',
                        'details': 'This session has expired. Please scan a new QR code.'
                    }, status=status.HTTP_410_GONE)
                else:
                    return Response({
                        'error': 'Session inactive',
                        'details': 'This session is no longer active.'
                    }, status=status.HTTP_403_FORBIDDEN)
            
            # Check if table is occupied by another active session
            other_active_sessions = TableSession.objects.filter(
                table=session.table,
                is_active=True
            ).exclude(id=session.id)
            
            # Check if there are active orders for this table
            has_active_order = OfflineOrder.objects.filter(
                table=session.table,
                status__in=['Pending', 'Preparing', 'Ready']
            ).exists()
            
            if other_active_sessions.exists() or has_active_order:
                # Check if the other session is valid
                for other_session in other_active_sessions:
                    if other_session.is_valid():
                        return Response({
                            'error': 'Table occupied',
                            'details': 'This table is currently in use. Please wait or contact staff.'
                        }, status=status.HTTP_409_CONFLICT)
            
            # Update last accessed
            session.last_accessed = timezone.now()
            session.save(update_fields=['last_accessed'])
            
            return Response({
                'valid': True,
                'session': TableSessionSerializer(session).data,
                'table': TableSerializer(session.table).data,
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({
                'error': 'Failed to validate session',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class TableSessionListView(APIView):
    """List all table sessions (Admin only)"""
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get(self, request):
        """Get all table sessions with optional filtering"""
        try:
            table_id = request.query_params.get('table_id')
            active_only = request.query_params.get('active_only', 'false').lower() == 'true'
            
            queryset = TableSession.objects.select_related('table').all()
            
            if table_id:
                queryset = queryset.filter(table_id=table_id)
            
            if active_only:
                queryset = queryset.filter(is_active=True)
            
            queryset = queryset.order_by('-created_at')
            
            serializer = TableSessionSerializer(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': 'Failed to retrieve table sessions',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TableSessionDetailView(APIView):
    """Manage a specific table session (Admin only)"""
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get(self, request, session_id):
        """Get a specific table session"""
        try:
            session = TableSession.objects.select_related('table').get(id=session_id)
            serializer = TableSessionSerializer(session)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except TableSession.DoesNotExist:
            return Response({
                'error': 'Table session not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': 'Failed to retrieve table session',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def patch(self, request, session_id):
        """Update a table session (e.g., deactivate, extend expiration)"""
        try:
            session = TableSession.objects.select_related('table').get(id=session_id)
            
            # Handle deactivation
            if 'is_active' in request.data and not request.data['is_active']:
                session.is_active = False
                session.save(update_fields=['is_active'])
                
                # Unlock table if no other active sessions
                active_sessions = TableSession.objects.filter(
                    table=session.table,
                    is_active=True
                ).exclude(id=session.id).exists()
                
                if not active_sessions:
                    session.table.is_available = True
                    session.table.save(update_fields=['is_available'])
            
            # Handle expiration extension
            if 'extend_hours' in request.data:
                extend_hours = int(request.data['extend_hours'])
                session.expires_at = session.expires_at + timedelta(hours=extend_hours)
                session.save(update_fields=['expires_at'])
            
            serializer = TableSessionSerializer(session)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except TableSession.DoesNotExist:
            return Response({
                'error': 'Table session not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': 'Failed to update table session',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def delete(self, request, session_id):
        """Delete a table session"""
        try:
            session = TableSession.objects.select_related('table').get(id=session_id)
            table = session.table
            session.delete()
            
            # Unlock table if no other active sessions
            active_sessions = TableSession.objects.filter(
                table=table,
                is_active=True
            ).exists()
            
            if not active_sessions:
                table.is_available = True
                table.save(update_fields=['is_available'])
            
            return Response({
                'message': 'Table session deleted successfully'
            }, status=status.HTTP_200_OK)
            
        except TableSession.DoesNotExist:
            return Response({
                'error': 'Table session not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': 'Failed to delete table session',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================
# CASHIER PANEL ENDPOINTS
# ============================================

class CashierTablesStatusView(APIView):
    """Get all tables with their current status (occupied/available)"""
    permission_classes = [IsAuthenticated, IsCashier]
    
    def get(self, request):
        """Get all tables with occupancy status - uses is_available field as primary source"""
        try:
            tables = Table.objects.all().order_by('number')
            
            # Build response with table status - use is_available from database as primary source
            tables_data = []
            for table in tables:
                # is_available is the primary source of truth from database
                # is_occupied is the inverse of is_available
                is_occupied = not table.is_available
                
                tables_data.append({
                    'id': table.id,
                    'number': table.number,
                    'capacity': table.capacity,
                    'location': table.location,
                    'is_available': table.is_available,  # Primary source from database
                    'is_occupied': is_occupied,  # Inverse of is_available
                    'notes': table.notes,
                })
            
            return Response({
                'tables': tables_data,
                'total': len(tables_data),
                'occupied': sum(1 for t in tables_data if not t['is_available']),
                'available': sum(1 for t in tables_data if t['is_available'])
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({
                'error': 'Failed to retrieve table status',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CashierPendingOrdersView(APIView):
    """Get all pending orders (unconfirmed by cashier)"""
    permission_classes = [IsAuthenticated, IsCashier]
    
    def get(self, request):
        """Get all unconfirmed orders (online + offline)"""
        try:
            # Get unconfirmed online orders
            online_orders = Order.objects.filter(
                is_confirmed_cashier=False,
                status__in=['Pending', 'Preparing']
            ).order_by('-created_at')
            
            # Get unconfirmed offline orders
            offline_orders = OfflineOrder.objects.filter(
                is_confirmed_cashier=False,
                status__in=['Pending', 'Preparing']
            ).select_related('table').prefetch_related('items__item', 'items__size').order_by('-created_at')
            
            online_serializer = OrderSerializer(online_orders, many=True)
            offline_serializer = OfflineOrderSerializer(offline_orders, many=True)
            
            return Response({
                'online_orders': online_serializer.data,
                'offline_orders': offline_serializer.data,
                'total_pending': online_orders.count() + offline_orders.count()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({
                'error': 'Failed to retrieve pending orders',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CashierConfirmOrderView(APIView):
    """Confirm an order (online or offline)"""
    permission_classes = [IsAuthenticated, IsCashier]
    
    def post(self, request):
        """Confirm an order by setting is_confirmed_cashier=True"""
        try:
            order_type = request.data.get('order_type')  # 'online' or 'offline'
            order_id = request.data.get('order_id')
            
            if not order_type or not order_id:
                return Response({
                    'error': 'Validation failed',
                    'details': {'order_type': ['order_type and order_id are required']}
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Clean order_id - remove '#' prefix if present and convert to int
            if isinstance(order_id, str):
                order_id = order_id.replace('#', '').strip()
            try:
                order_id = int(order_id)
            except (ValueError, TypeError):
                return Response({
                    'error': 'Invalid order ID',
                    'details': 'order_id must be a valid number'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if order_type == 'online':
                try:
                    order = Order.objects.get(id=order_id)
                    if order.is_confirmed_cashier:
                        return Response({
                            'error': 'Order already confirmed',
                            'details': 'This order has already been confirmed by the cashier.'
                        }, status=status.HTTP_400_BAD_REQUEST)
                    
                    # Update order confirmation status
                    order.is_confirmed_cashier = True
                    order.save(update_fields=['is_confirmed_cashier'])
                    
                    logger.info(f"Order {order.id} confirmed by cashier")
                    
                    # Notify chefs that order has been confirmed and is ready to prepare
                    print(f"NOTIFICATION: About to call notify_order_confirmed_by_cashier for order {order.id}")
                    logger.info(f"NOTIFICATION: About to call notify_order_confirmed_by_cashier for order {order.id}")
                    try:
                        result = notify_order_confirmed_by_cashier(order, order_type='online')
                        logger.info(f"NOTIFICATION: Function returned {len(result) if result else 0} notifications")
                        if not result:
                            logger.warning(f"NOTIFICATION: WARNING - No notifications were created for order {order.id}")
                        else:
                            logger.info(f"NOTIFICATION: SUCCESS - Created notifications: {[n.id for n in result]}")
                    except Exception as e:
                        logger.error(f"NOTIFICATION: ERROR calling notify_order_confirmed_by_cashier for order {order.id}: {e}", exc_info=True)
                        import traceback
                        logger.error(f"NOTIFICATION: Full traceback: {traceback.format_exc()}")
                    
                    # Build order data manually - avoid using serializer to prevent ID validation issues
                    # Format ID as string with # prefix for display
                    order_data = {
                        'id': f"#{order.id}",
                        'customer': order.customer,
                        'phone': order.phone,
                        'address': order.address or '',
                        'total': str(order.total),
                        'status': order.status,
                        'orderType': order.order_type,
                        'tableNumber': order.table_number or '',
                        'is_confirmed_cashier': order.is_confirmed_cashier,
                        'items': order.items if order.items else [],
                        'date': order.created_at.strftime('%Y-%m-%d'),
                        'time': order.created_at.strftime('%H:%M'),
                        'created_at': order.created_at.isoformat(),
                        'updated_at': order.updated_at.isoformat(),
                    }
                    
                    logger.info(f"Returning order data with ID: {order_data['id']}")
                    
                    # Return plain dictionary response - no serialization
                    response_data = {
                        'success': True,
                        'message': 'Order confirmed successfully',
                        'order': order_data
                    }
                    
                    return Response(response_data, status=status.HTTP_200_OK)
                    
                except Order.DoesNotExist:
                    return Response({
                        'error': 'Order not found'
                    }, status=status.HTTP_404_NOT_FOUND)
                except Exception as e:
                    import traceback
                    error_trace = traceback.format_exc()
                    traceback.print_exc()
                    logger.error(f"Error confirming online order {order_id}: {e}\n{error_trace}")
                    return Response({
                        'error': 'Failed to confirm order',
                        'detail': str(e),
                        'traceback': error_trace if django_settings.DEBUG else None
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                    
            elif order_type == 'offline':
                try:
                    offline_order = OfflineOrder.objects.select_related('table').prefetch_related('items__item', 'items__size').get(id=order_id)
                    if offline_order.is_confirmed_cashier:
                        return Response({
                            'error': 'Order already confirmed',
                            'details': 'This order has already been confirmed by the cashier.'
                        }, status=status.HTTP_400_BAD_REQUEST)
                    
                    offline_order.is_confirmed_cashier = True
                    offline_order.save(update_fields=['is_confirmed_cashier'])
                    
                    logger.info(f"Offline order {offline_order.id} confirmed by cashier")
                    
                    # Notify chefs that order has been confirmed and is ready to prepare
                    logger.info(f"NOTIFICATION: About to call notify_order_confirmed_by_cashier for offline order {offline_order.id}")
                    try:
                        result = notify_order_confirmed_by_cashier(offline_order, order_type='offline')
                        logger.info(f"NOTIFICATION: Function returned {len(result) if result else 0} notifications")
                        if not result:
                            logger.warning(f"NOTIFICATION: WARNING - No notifications were created for offline order {offline_order.id}")
                        else:
                            logger.info(f"NOTIFICATION: SUCCESS - Created notifications: {[n.id for n in result]}")
                    except Exception as e:
                        logger.error(f"NOTIFICATION: ERROR calling notify_order_confirmed_by_cashier for offline order {offline_order.id}: {e}", exc_info=True)
                        import traceback
                        logger.error(f"NOTIFICATION: Full traceback: {traceback.format_exc()}")
                    
                    serializer = OfflineOrderSerializer(offline_order)
                    return Response({
                        'success': True,
                        'message': 'Order confirmed successfully',
                        'order': serializer.data
                    }, status=status.HTTP_200_OK)
                    
                except OfflineOrder.DoesNotExist:
                    return Response({
                        'error': 'Order not found'
                    }, status=status.HTTP_404_NOT_FOUND)
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    logger.error(f"Error confirming offline order {order_id}: {e}", exc_info=True)
                    return Response({
                        'error': 'Failed to confirm order',
                        'detail': str(e)
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            else:
                return Response({
                    'error': 'Invalid order type',
                    'details': 'order_type must be "online" or "offline"'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            traceback.print_exc()
            logger.error(f"Error in CashierConfirmOrderView: {e}\n{error_trace}")
            return Response({
                'error': 'Failed to confirm order',
                'detail': str(e),
                'traceback': error_trace if settings.DEBUG else None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CashierOrderDetailView(APIView):
    """Get detailed information about a specific order"""
    permission_classes = [IsAuthenticated, IsCashier]
    
    def get(self, request):
        """Get order details by type and ID"""
        try:
            order_type = request.query_params.get('order_type')  # 'online' or 'offline'
            order_id = request.query_params.get('order_id')
            
            if not order_type or not order_id:
                return Response({
                    'error': 'Validation failed',
                    'details': {'order_type': ['order_type and order_id are required']}
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Clean order_id - remove '#' prefix if present and convert to int
            if isinstance(order_id, str):
                order_id = order_id.replace('#', '').strip()
            try:
                order_id = int(order_id)
            except (ValueError, TypeError):
                return Response({
                    'error': 'Invalid order ID',
                    'details': 'order_id must be a valid number'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if order_type == 'online':
                try:
                    order = Order.objects.get(id=order_id)
                    serializer = OrderSerializer(order)
                    return Response(serializer.data, status=status.HTTP_200_OK)
                except Order.DoesNotExist:
                    return Response({
                        'error': 'Order not found'
                    }, status=status.HTTP_404_NOT_FOUND)
                    
            elif order_type == 'offline':
                try:
                    offline_order = OfflineOrder.objects.select_related('table').prefetch_related('items__item', 'items__size').get(id=order_id)
                    serializer = OfflineOrderSerializer(offline_order)
                    return Response(serializer.data, status=status.HTTP_200_OK)
                except OfflineOrder.DoesNotExist:
                    return Response({
                        'error': 'Order not found'
                    }, status=status.HTTP_404_NOT_FOUND)
            else:
                return Response({
                    'error': 'Invalid order type',
                    'details': 'order_type must be "online" or "offline"'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({
                'error': 'Failed to retrieve order details',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CashierCreateOfflineOrderView(APIView):
    """Cashier endpoint for manually creating offline orders for tables"""
    permission_classes = [IsAuthenticated, IsCashier]
    
    def post(self, request):
        """Create a new offline order manually by cashier"""
        try:
            import logging
            logger = logging.getLogger(__name__)
            
            # Get table ID from request
            table_id = request.data.get('table_id')
            if not table_id:
                return Response({
                    'error': 'Missing required field',
                    'details': 'table_id is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get table
            try:
                table = Table.objects.get(id=table_id)
            except Table.DoesNotExist:
                return Response({
                    'error': 'Table not found',
                    'details': f'Table with ID {table_id} does not exist'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Get items from request
            items = request.data.get('items', [])
            if not items or len(items) == 0:
                return Response({
                    'error': 'Validation failed',
                    'details': 'At least one item is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Calculate total
            total = Decimal('0.00')
            created_count = 0
            failed_count = 0
            
            # Create offline order
            offline_order = OfflineOrder.objects.create(
                table=table,
                status='Pending',
                is_confirmed_cashier=False,
                total=Decimal('0.00')  # Will be calculated
            )
            
            # Create offline order items
            for item_data in items:
                try:
                    item_id = item_data.get('item_id')
                    size_id = item_data.get('size_id')  # Can be null
                    quantity = int(item_data.get('quantity', 1))
                    
                    if not item_id:
                        failed_count += 1
                        logger.warning(f"Missing item_id in order item data: {item_data}")
                        continue
                    
                    # Get menu item
                    try:
                        menu_item = MenuItem.objects.get(id=item_id)
                    except MenuItem.DoesNotExist:
                        failed_count += 1
                        logger.warning(f"Menu item {item_id} not found")
                        continue
                    
                    # Get size if provided
                    menu_item_size = None
                    item_price = menu_item.price  # Default to menu item price
                    
                    if size_id:
                        try:
                            menu_item_size = MenuItemSize.objects.get(id=size_id, menu_item=menu_item)
                            item_price = menu_item_size.price
                        except MenuItemSize.DoesNotExist:
                            logger.warning(f"Menu item size {size_id} not found for item {item_id}")
                            # Continue with menu item price
                    
                    # Calculate item total
                    item_total = Decimal(str(item_price)) * Decimal(str(quantity))
                    total += item_total
                    
                    # Create offline order item (price is required field)
                    OfflineOrderItem.objects.create(
                        offline_order=offline_order,
                        item=menu_item,
                        size=menu_item_size,
                        quantity=quantity,
                        price=Decimal(str(item_price))  # Store price at time of order
                    )
                    created_count += 1
                    
                except Exception as e:
                    failed_count += 1
                    logger.error(f"Error creating offline order item: {e}", exc_info=True)
            
            # Update order total
            offline_order.total = total
            offline_order.save(update_fields=['total'])
            
            logger.info(f"Cashier created OfflineOrder #{offline_order.id}: {created_count} items created, {failed_count} failed")
            
            # Mark table as occupied when order is created
            if table.is_available:
                table.is_available = False
                table.save(update_fields=['is_available'])
                logger.info(f"Table {table.number} marked as occupied (is_available=False) due to order #{offline_order.id}")
            
            # Refresh from database to ensure all relationships are loaded
            offline_order.refresh_from_db()
            
            # Prefetch related items for serialization
            offline_order = OfflineOrder.objects.prefetch_related('items__item', 'items__size').get(id=offline_order.id)
            
            # Serialize and return
            serializer = OfflineOrderSerializer(offline_order)
            return Response({
                'success': True,
                'message': 'Offline order created successfully',
                'order': serializer.data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            logger.error(f"Error creating cashier offline order: {e}\n{error_trace}")
            return Response({
                'error': 'Failed to create offline order',
                'detail': str(e),
                'traceback': error_trace if django_settings.DEBUG else None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CashierTableOccupancyView(APIView):
    """Cashier can manually occupy or unoccupy tables"""
    permission_classes = [IsAuthenticated, IsCashier]
    
    def patch(self, request, table_id):
        """Update table occupancy status"""
        try:
            table = Table.objects.get(id=table_id)
            is_occupied = request.data.get('is_occupied')
            
            if is_occupied is None:
                return Response({
                    'error': 'Validation failed',
                    'details': {'is_occupied': ['is_occupied field is required']}
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Ensure is_occupied is a boolean (handle string "true"/"false" from frontend)
            if isinstance(is_occupied, str):
                is_occupied = is_occupied.lower() in ('true', '1', 'yes')
            is_occupied = bool(is_occupied)
            
            # Cashier can freely mark tables as available/occupied without validation
            # Deactivate any active sessions when marking table as available
            if not is_occupied:
                sessions_deactivated = TableSession.objects.filter(
                    table=table,
                    is_active=True
                ).update(is_active=False)
                
                if sessions_deactivated > 0:
                    logger.info(f"Deactivated {sessions_deactivated} active session(s) for table {table.number}")
            
            # Update is_available field in database
            # When is_occupied is False, table should be available (is_available = True)
            # When is_occupied is True, table should not be available (is_available = False)
            old_is_available = table.is_available
            table.is_available = not is_occupied
            
            # Save the change to database - use save() without update_fields to ensure it's saved
            table.save()
            
            # Refresh from database to verify the change was saved
            table.refresh_from_db()
            
            # Verify the change was actually saved
            if table.is_available != (not is_occupied):
                logger.error(
                    f"❌ ERROR: Table {table.number} is_available was not saved correctly! "
                    f"Expected: {not is_occupied}, Got: {table.is_available}"
                )
                # Try saving again without update_fields
                table.is_available = not is_occupied
                table.save()
                table.refresh_from_db()
            
            logger.info(
                f"✅ Table {table.number} updated: "
                f"is_occupied={is_occupied}, is_available changed from {old_is_available} to {table.is_available} (saved to database)"
            )
            
            # Notify admin about table status change (medium priority - real-time, no sound)
            from .notification_utils import notify_table_change
            change_type = 'occupied' if is_occupied else 'free'
            notify_table_change(table, change_type=change_type)
            
            serializer = TableSerializer(table)
            return Response({
                'success': True,
                'message': f'Table {table.number} is now {"occupied" if is_occupied else "available"}',
                'table': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Table.DoesNotExist:
            return Response({
                'error': 'Table not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({
                'error': 'Failed to update table occupancy',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
