from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .permissions import IsCashier
from .models import Order, OfflineOrder
from .notification_utils import send_notification_to_role
import logging

logger = logging.getLogger(__name__)

class CashierDeclineOrderView(APIView):
    """Decline (cancel) an order"""
    permission_classes = [IsAuthenticated, IsCashier]
    
    def post(self, request):
        """Decline an order by setting status='Cancelled'"""
        try:
            order_type = request.data.get('order_type')
            order_id = request.data.get('order_id')
            reason = request.data.get('reason', 'Declined by cashier')
            
            if not order_type or not order_id:
                return Response({
                    'error': 'Validation failed',
                    'details': {'order_type': ['order_type and order_id are required']}
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Clean order_id
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
                    if order.status == 'Cancelled':
                        return Response({'success': True, 'message': 'Order already cancelled'}, status=status.HTTP_200_OK)
                        
                    order.status = 'Cancelled'
                    order.is_confirmed_cashier = False # Ensure it's not confirmed
                    order.notes = (order.notes or '') + f" [Cancelled: {reason}]"
                    order._updated_by_user = request.user
                    order.save(update_fields=['status', 'is_confirmed_cashier', 'notes'])
                    
                    try:
                        send_notification_to_role(
                            role='admin',
                            notification_type='order',
                            title=f"Order #{order.id} Cancelled",
                            message=f"Order declined by cashier. Reason: {reason}",
                            priority='high',
                            related_order=order
                        )
                    except Exception as e:
                        logger.error(f"Failed to send cancellation notification: {e}")
                    
                    logger.info(f"Order {order.id} declined/cancelled by cashier.")
                    return Response({'success': True, 'message': 'Order declined successfully'}, status=status.HTTP_200_OK)
                except Order.DoesNotExist:
                    return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)
                    
            elif order_type == 'offline':
                try:
                    offline_order = OfflineOrder.objects.select_related('table').get(id=order_id)
                    if offline_order.status == 'Cancelled':
                        return Response({'success': True, 'message': 'Order already cancelled'}, status=status.HTTP_200_OK)
                        
                    offline_order.status = 'Cancelled'
                    offline_order.is_confirmed_cashier = False
                    offline_order.notes = (offline_order.notes or '') + f" [Cancelled: {reason}]"
                    offline_order._updated_by_user = request.user
                    offline_order.save(update_fields=['status', 'is_confirmed_cashier', 'notes'])
                    
                    # Release table if no other active orders exist on it
                    if offline_order.table:
                        active_orders = OfflineOrder.objects.filter(
                            table=offline_order.table,
                            status__in=['Pending', 'Confirmed', 'Preparing', 'Ready', 'Served']
                        ).exclude(id=offline_order.id).exists()
                        
                        if not active_orders:
                            offline_order.table.is_available = True
                            offline_order.table.save(update_fields=['is_available'])
                            logger.info(f"Table {offline_order.table.number} marked as available after order cancellation.")

                    try:
                        send_notification_to_role(
                            role='admin',
                            notification_type='order',
                            title=f"Offline Order #{offline_order.id} Cancelled",
                            message=f"Order declined by cashier. Reason: {reason}",
                            priority='high',
                            related_offline_order=offline_order
                        )
                    except Exception as e:
                        logger.error(f"Failed to send cancellation notification: {e}")

                    logger.info(f"Offline Order {offline_order.id} declined/cancelled by cashier.")
                    return Response({'success': True, 'message': 'Order declined successfully'}, status=status.HTTP_200_OK)
                except OfflineOrder.DoesNotExist:
                    return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)
            
            else:
                return Response({'error': 'Invalid order type'}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            logger.error(f"Error checking declination: {e}\n{error_trace}")
            return Response({'error': 'Failed to decline order', 'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
