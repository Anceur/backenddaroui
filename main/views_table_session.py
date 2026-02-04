"""
Views for Table Session Management
Handles secure table access via unique URLs and session management
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import secrets
import hashlib
import logging
from django.db import transaction

from .models import Table, TableSession, OfflineOrder, OfflineOrderItem, MenuItem, MenuItemSize, ClientFidele, RestaurantInfo
from .serializers import (
    TableSessionSerializer, TableSerializer, OfflineOrderSerializer,
    OfflineOrderItemSerializer, MenuItemSerializer
)
from .permissions import IsAdmin, IsCashierOrAdmin

logger = logging.getLogger(__name__)


class TableSessionCreateView(APIView):
    """
    Create or retrieve a table session via table ID or token
    Public endpoint - no authentication required
    """
    permission_classes = [AllowAny]
    
    def get_authenticators(self):
        """Disable authentication for public table access"""
        return []
    
    def post(self, request):
        """
        Create a new table session
        Expected data: { "table_id": 1 } or { "table_number": "5" }
        """
        try:
            # Check restaurant opening hours
            try:
                restaurant_info = RestaurantInfo.objects.first()
                if restaurant_info:
                    current_time = datetime.now().time()
                    is_open = False
                    
                    if restaurant_info.opening_time < restaurant_info.closing_time:
                        if restaurant_info.opening_time <= current_time <= restaurant_info.closing_time:
                            is_open = True
                    else:
                        if current_time >= restaurant_info.opening_time or current_time <= restaurant_info.closing_time:
                            is_open = True
                    
                    if not is_open:
                        return Response({
                            'error': 'Restaurant is closed',
                            'details': f'Hours: {restaurant_info.opening_time.strftime("%H:%M")} - {restaurant_info.closing_time.strftime("%H:%M")}'
                        }, status=status.HTTP_403_FORBIDDEN)
            except Exception as e:
                logger.error(f"Error checking hours: {e}")

            table_id = request.data.get('table_id')
            table_number = request.data.get('table_number')
            
            # Find table by ID or number
            table = None
            if table_id:
                try:
                    table = Table.objects.get(id=table_id)
                except Table.DoesNotExist:
                    return Response({'error': 'Table not found'}, status=status.HTTP_404_NOT_FOUND)
            elif table_number:
                try:
                    table = Table.objects.get(number=table_number)
                except Table.DoesNotExist:
                    return Response({'error': 'Table not found'}, status=status.HTTP_404_NOT_FOUND)
            else:
                return Response({'error': 'table_id or table_number is required'}, status=status.HTTP_400_BAD_REQUEST)

            # --- ATOMIC TRANSACTION START ---
            # Use nowait=True to fail fast instead of blocking if lock is held
            with transaction.atomic():
                try:
                    # Lock the table record to prevent race conditions
                    # Removed nowait=True to prevent 500 errors on databases that don't support it
                    table = Table.objects.select_for_update().get(id=table.id)
                except Exception as lock_error:
                    # Lock couldn't be acquired - another request is processing this table
                    logger.warning(f"Table {table.number} lock busy, rejecting request")
                    return Response({
                        'error': f'Table {table.number} is currently being accessed. Please try again in a moment.',
                        'retry': True
                    }, status=status.HTTP_409_CONFLICT)

                # Find any current active session for this table
                existing_session = TableSession.objects.filter(
                    table=table,
                    is_active=True
                ).order_by('-created_at').first()

                client_ip = self.get_client_ip(request)
                client_ua = request.META.get('HTTP_USER_AGENT', '')[:255]

                if existing_session:
                    # Check if it's the SAME USER (by IP AND User Agent) attempting to resume
                    if existing_session.ip_address == client_ip and existing_session.user_agent == client_ua:
                        logger.info(f"Session {existing_session.id} RESUMED for Table {table.number}")
                        existing_session.expires_at = timezone.now() + timedelta(hours=12)
                        existing_session.save()
                        
                        # Sync table state
                        if table.is_available:
                            table.is_available = False
                            table.save()

                        serializer = TableSessionSerializer(existing_session)
                        return Response({
                            'success': True,
                            'session': serializer.data,
                            'message': f'Session resumed for Table {table.number}',
                            'resumed': True
                        }, status=status.HTTP_200_OK)
                    
                    # If different user -> BLOCK
                    # Ensure table is marked as unavailable since an active session exists
                    if table.is_available:
                        table.is_available = False
                        table.save()

                    logger.warning(f"CONFLICT: Table {table.number} occupied by session {existing_session.id}. Blocked {client_ip}.")
                    return Response({
                        'error': f'Table {table.number} is currently occupied by another client. Please wait or ask staff.',
                        'is_occupied': True
                    }, status=status.HTTP_409_CONFLICT)

                # NO ACTIVE SESSION -> OK to create a new one
                # First, ensure ALL other sessions for this table are definitely deactivated (Cleanup ghost sessions)
                TableSession.objects.filter(table=table, is_active=True).update(is_active=False)

                # Generate secure token
                token = secrets.token_urlsafe(32)
                expires_at = timezone.now() + timedelta(hours=12)

                # Create new session
                session = TableSession.objects.create(
                    table=table,
                    token=token,
                    is_active=True,
                    expires_at=expires_at,
                    ip_address=client_ip,
                    user_agent=client_ua
                )

                # Mark table as occupied
                table.is_available = False
                table.save()

                logger.info(f"NEW Session {session.id} created for Table {table.number}")
                serializer = TableSessionSerializer(session)
                return Response({
                    'success': True,
                    'session': serializer.data,
                    'message': f'Session created for Table {table.number}'
                }, status=status.HTTP_201_CREATED)
            # --- ATOMIC TRANSACTION END ---

        except Exception as e:
            logger.error(f"Error in TableSessionCreate: {e}", exc_info=True)
            return Response({
                'error': 'Internal server error during session creation',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def get_client_ip(self, request):
        """Get client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class TableSessionValidateView(APIView):
    """
    Validate a table session token
    Public endpoint - no authentication required
    """
    permission_classes = [AllowAny]
    
    def get_authenticators(self):
        """Disable authentication for public table access"""
        return []
    
    def post(self, request):
        """
        Validate session token
        Expected data: { "token": "session_token" }
        """
        try:
            # Check restaurant opening hours
            try:
                restaurant_info = RestaurantInfo.objects.first()
                if restaurant_info:
                    current_time = datetime.now().time()
                    is_open = False
                    
                    if restaurant_info.opening_time < restaurant_info.closing_time:
                        if restaurant_info.opening_time <= current_time <= restaurant_info.closing_time:
                            is_open = True
                    else:
                        if current_time >= restaurant_info.opening_time or current_time <= restaurant_info.closing_time:
                            is_open = True
                    
                    if not is_open:
                        return Response({
                            'error': 'Restaurant is closed',
                            'details': f'Hours: {restaurant_info.opening_time} - {restaurant_info.closing_time}'
                        }, status=status.HTTP_403_FORBIDDEN)
            except Exception as e:
                logger.error(f"Error checking hours: {e}")

            token = request.data.get('token')
            
            if not token:
                return Response({
                    'error': 'Token is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Find session
            try:
                session = TableSession.objects.get(token=token)
            except TableSession.DoesNotExist:
                return Response({
                    'error': 'Invalid session token',
                    'valid': False
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Check if session is valid
            if not session.is_valid():
                # Session expired or inactive
                if session.is_expired():
                    # DO NOT FREE THE TABLE AUTOMATICALLY
                    # Just report session expired, client should re-scan QR which will resume and refresh token/expiry
                    return Response({
                        'error': 'Session has expired',
                        'valid': False,
                        'expired': True
                    }, status=status.HTTP_401_UNAUTHORIZED)
                else:
                    return Response({
                        'error': 'Session is not active',
                        'valid': False
                    }, status=status.HTTP_401_UNAUTHORIZED)
            
            # Update last accessed time
            session.last_accessed = timezone.now()
            session.save()
            
            serializer = TableSessionSerializer(session)
            
            return Response({
                'valid': True,
                'session': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error validating session: {e}", exc_info=True)
            return Response({
                'error': 'Failed to validate session',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TableSessionOrderCreateView(APIView):
    """
    Create an order for a table session
    Public endpoint - requires valid session token
    """
    permission_classes = [AllowAny]
    
    def get_authenticators(self):
        """Disable authentication for public table access"""
        return []
    
    def post(self, request):
        """
        Create order with session token
        Expected data: {
            "session_token": "token",
            "items": [{"item_id": 1, "size_id": 1, "quantity": 2, "notes": ""}],
            "notes": "Special instructions"
        }
        """
        try:
            session_token = request.data.get('session_token')
            items_data = request.data.get('items', [])
            notes = request.data.get('notes', '')
            loyalty_number = request.data.get('loyalty_number') or request.data.get('loyaltyNumber')
            
            # Check restaurant opening hours
            try:
                restaurant_info = RestaurantInfo.objects.first()
                if restaurant_info:
                    current_time = datetime.now().time()
                    is_open = False
                    
                    if restaurant_info.opening_time < restaurant_info.closing_time:
                        if restaurant_info.opening_time <= current_time <= restaurant_info.closing_time:
                            is_open = True
                    else:
                        if current_time >= restaurant_info.opening_time or current_time <= restaurant_info.closing_time:
                            is_open = True
                    
                    if not is_open:
                        return Response({
                            'error': 'Restaurant is closed',
                            'details': f'Hours: {restaurant_info.opening_time} - {restaurant_info.closing_time}'
                        }, status=status.HTTP_403_FORBIDDEN)
            except Exception as e:
                logger.error(f"Error checking hours: {e}")

            if not session_token:
                return Response({
                    'error': 'session_token is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if not items_data or len(items_data) == 0:
                logger.warning(f"Order failed: No items. Token: {session_token[:8]}...")
                return Response({
                    'error': 'At least one item is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate session
            try:
                session = TableSession.objects.select_related('table').get(token=session_token)
            except TableSession.DoesNotExist:
                return Response({'error': 'Invalid session token'}, status=status.HTTP_404_NOT_FOUND)
            
            # CRITICAL: Double check that this table doesn't have a NEWER active session
            # This handles any edge cases where a previous active session wasn't closed correctly
            current_active = TableSession.objects.filter(table=session.table, is_active=True).order_by('-created_at').first()
            if current_active and current_active.id != session.id:
                # This session has been superseded by a newer one
                session.is_active = False
                session.save()
                return Response({
                    'error': 'This session is no longer active. A new occupant has taken this table.'
                }, status=status.HTTP_401_UNAUTHORIZED)

            # Check if session is valid (active and not expired)
            if not session.is_valid():
                if session.is_expired():
                    # DO NOT FREE TABLE automatically.
                     return Response({
                        'error': 'Session has expired. Please rescan QR code.'
                    }, status=status.HTTP_401_UNAUTHORIZED)
                else:
                    return Response({
                        'error': 'Session is not active'
                    }, status=status.HTTP_401_UNAUTHORIZED)
            
            # Check for existing open order for THIS SESSION ONLY
            # CRITICAL: We must ONLY look at the current session's orders, not old ones from previous sessions
            # This prevents order items from previous customers bleeding into new orders
            existing_order = OfflineOrder.objects.filter(
                table=session.table,
                status__in=['Pending', 'Confirmed', 'Preparing', 'Ready']
            ).exclude(
                status='Served'  # Explicitly exclude served orders from previous sessions
            ).first()

            # Lookup loyalty info
            customer_name = None
            if loyalty_number:
                try:
                    client = ClientFidele.objects.get(loyalty_card_number=loyalty_number)
                    customer_name = client.name
                except ClientFidele.DoesNotExist:
                    pass

            # Prepend loyalty info to notes so it's visible to cashier
            if loyalty_number:
                loyalty_str = f"Loyalty: {loyalty_number}"
                if customer_name:
                    loyalty_str += f" ({customer_name})"
                
                # Check if already in notes to avoid duplication on updates (simple check)
                if not existing_order or (existing_order.notes and loyalty_number not in existing_order.notes):
                    notes = f"{loyalty_str}\n{notes}" if notes else loyalty_str

            # Allow multiple orders per session (continuous ordering)
            # We update session to keep it alive and extend expiration
            session.last_accessed = timezone.now()
            session.expires_at = timezone.now() + timedelta(hours=12) # Extend by 12 hours
            session.order_placed = True
            session.save()
            
            # Calculate total
            total = Decimal('0.00')
            order_items = []
            
            for item_data in items_data:
                item_id = item_data.get('item_id')
                size_id = item_data.get('size_id')
                quantity = item_data.get('quantity', 1)
                item_notes = item_data.get('notes', '')
                
                if not item_id:
                    continue
                
                try:
                    menu_item = MenuItem.objects.get(id=item_id)
                    
                    # Get price
                    if size_id:
                        size = MenuItemSize.objects.get(id=size_id, menu_item=menu_item)
                        price = size.price
                    else:
                        price = menu_item.price
                        size = None
                    
                    item_total = price * quantity
                    total += item_total
                    
                    order_items.append({
                        'item': menu_item,
                        'size': size,
                        'quantity': quantity,
                        'price': price,
                        'notes': item_notes
                    })
                    
                except (MenuItem.DoesNotExist, MenuItemSize.DoesNotExist) as e:
                    logger.warning(f"Item not found: {e}")
                    continue
            
            if not order_items:
                return Response({
                    'error': 'No valid items found'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            
            if existing_order:
                # Append to existing order
                offline_order = existing_order
                offline_order.total += total
                
                # Always reset status to Pending so it appears in Cashier's "Pending" list
                # and Kitchen can see the new items after confirmation.
                offline_order.status = 'Pending'
                
                offline_order.notes = (offline_order.notes or '') + f"\n[Update]: {notes}" if notes else offline_order.notes
                
                # IMPORTANT: Reset confirmation so cashier sees the update!
                offline_order.is_confirmed_cashier = False
                offline_order.save()
            else:
                # Create new offline order
                offline_order = OfflineOrder.objects.create(
                    table=session.table,
                    total=total,
                    revenue=Decimal('0.00'),  # Will be calculated later
                    status='Pending',
                    notes=notes
                )
            
            # Create order items linked to the (new or existing) order
            for item_data in order_items:
                OfflineOrderItem.objects.create(
                    offline_order=offline_order,
                    item=item_data['item'],
                    size=item_data['size'],
                    quantity=item_data['quantity'],
                    price=item_data['price'],
                    notes=item_data['notes']
                )

            # Create notification for cashier/kitchen (Critical)
            try:
                # We import here to avoid circular imports
                from .notification_utils import send_notification_to_role
                
                table_num = session.table.number
                
                # Build rich customer description
                customer_desc = f"Table {table_num}"
                if customer_name:
                    customer_desc += f" - {customer_name} (Loyalty: {loyalty_number})"
                elif loyalty_number:
                    customer_desc += f" (Loyalty: {loyalty_number})"

                if existing_order:
                    title = f"UPDATE: {customer_desc}"
                    message = f"{customer_desc} ADDED items. New Total: {offline_order.total} DA"
                else:
                    title = f"NEW: {customer_desc}"
                    message = f"New Order from {customer_desc}. Total: {offline_order.total} DA"
                
                send_notification_to_role(
                    role='cashier',
                    notification_type='order',
                    title=title,
                    message=message,
                    priority='critical',
                    related_offline_order=offline_order
                )

                # Also notify Admin (in case user is testing as Admin or Admin wants to know)
                send_notification_to_role(
                    role='admin',
                    notification_type='order',
                    title=title,
                    message=message,
                    priority='critical',
                    related_offline_order=offline_order
                )
                
                if existing_order:
                    chef_msg = f"{customer_desc} ADDED items - Check Order!"
                else:
                    chef_msg = f"New items for {customer_desc}"

                send_notification_to_role(
                    role='chef',
                    notification_type='order',
                    title=title,
                    message=chef_msg,
                    priority='medium',
                    related_offline_order=offline_order
                )
            except Exception as e:
                logger.error(f"Failed to send notification: {e}")


            
            # Mark session as order placed
            session.order_placed = True
            session.save()
            
            # Update last accessed
            session.last_accessed = timezone.now()
            session.save()
            
            serializer = OfflineOrderSerializer(offline_order)
            
            logger.info(f"Order created for Table {session.table.number}, Order ID: {offline_order.id}")
            
            return Response({
                'success': True,
                'order': serializer.data,
                'message': 'Order placed successfully'
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error creating order: {e}", exc_info=True)
            return Response({
                'error': 'Failed to create order',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TableSessionEndView(APIView):
    """
    End a table session (admin/cashier only)
    """
    permission_classes = [IsAuthenticated, IsCashierOrAdmin]
    
    def post(self, request):
        """
        End session and free table
        Expected data: { "session_id": 1 } or { "token": "session_token" }
        """
        try:
            table_id = request.data.get('table_id')
            session_id = request.data.get('session_id')
            token = request.data.get('token')
            
            # Find session
            session = None
            if table_id:
                # Find the active session for this table
                try:
                    table = Table.objects.get(id=table_id)
                    session = TableSession.objects.filter(
                        table=table,
                        is_active=True
                    ).order_by('-created_at').first()
                    
                    if not session:
                        # No active session, but still free the table if it's occupied
                        if not table.is_available:
                            table.is_available = True
                            table.save()
                            logger.info(f"Table {table.number} freed (no active session found)")
                        
                        return Response({
                            'success': True,
                            'message': f'Table {table.number} is now available'
                        }, status=status.HTTP_200_OK)
                        
                except Table.DoesNotExist:
                    return Response({
                        'error': 'Table not found'
                    }, status=status.HTTP_404_NOT_FOUND)
            elif session_id:
                try:
                    session = TableSession.objects.get(id=session_id)
                except TableSession.DoesNotExist:
                    return Response({
                        'error': 'Session not found'
                    }, status=status.HTTP_404_NOT_FOUND)
            elif token:
                try:
                    session = TableSession.objects.get(token=token)
                except TableSession.DoesNotExist:
                    return Response({
                        'error': 'Session not found'
                    }, status=status.HTTP_404_NOT_FOUND)
            else:
                return Response({
                    'error': 'table_id, session_id, or token is required'
                }, status=status.HTTP_400_BAD_REQUEST)

            
            # End session
            session.is_active = False
            session.save()
            
            # Finalize any open orders for this table
            # Mark them as 'Served' so they won't be picked up by new sessions
            open_orders = OfflineOrder.objects.filter(
                table=session.table,
                status__in=['Pending', 'Confirmed', 'Preparing', 'Ready']
            )
            
            orders_finalized = open_orders.count()
            if orders_finalized > 0:
                open_orders.update(status='Served')
                logger.info(f"Finalized {orders_finalized} orders for Table {session.table.number}")
            
            # Free table
            session.table.is_available = True
            session.table.save()
            
            logger.info(f"Session {session.id} ended for Table {session.table.number}")
            
            return Response({
                'success': True,
                'message': f'Session ended for Table {session.table.number}',
                'orders_finalized': orders_finalized
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error ending session: {e}", exc_info=True)
            return Response({
                'error': 'Failed to end session',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TableListView(APIView):
    """
    List all tables (public endpoint for client to see available tables)
    """
    permission_classes = [AllowAny]
    
    def get_authenticators(self):
        """Disable authentication for public table listing"""
        return []
    
    def get(self, request):
        """Get all tables with availability status"""
        try:
            tables = Table.objects.all().order_by('number')
            serializer = TableSerializer(tables, many=True)
            
            return Response({
                'tables': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error listing tables: {e}", exc_info=True)
            return Response({
                'error': 'Failed to list tables',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PublicMenuView(APIView):
    """
    Public menu endpoint for table sessions
    """
    permission_classes = [AllowAny]
    
    def get_authenticators(self):
        """Disable authentication for public menu access"""
        return []
    
    def get(self, request):
        """Get menu items for table ordering"""
        try:
            menu_items = MenuItem.objects.all()
            serializer = MenuItemSerializer(menu_items, many=True, context={'request': request})
            
            return Response({
                'menu_items': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error fetching menu: {e}", exc_info=True)
            return Response({
                'error': 'Failed to fetch menu',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
