"""
Utility functions for sending real-time notifications via Django Channels
"""
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Notification
from django.contrib.auth import get_user_model
from datetime import datetime

User = get_user_model()

# Get channel layer - handle case where it might not be configured
try:
    channel_layer = get_channel_layer()
except Exception:
    channel_layer = None


def send_notification_to_user(user, notification_type, title, message, 
                             related_order=None, related_offline_order=None, 
                             related_ingredient=None):
    """
    Create and send a notification to a specific user
    
    Args:
        user: User instance or user ID
        notification_type: Type of notification ('order', 'alert', 'info', 'ingredient', 'table')
        title: Notification title
        message: Notification message
        related_order: Related Order instance (optional)
        related_offline_order: Related OfflineOrder instance (optional)
        related_ingredient: Related Ingredient instance (optional)
    """
    if isinstance(user, int):
        user = User.objects.get(id=user)
    
    # Create notification in database
    notification = Notification.objects.create(
        user=user,
        role=user.roles,
        notification_type=notification_type,
        title=title,
        message=message,
        related_order=related_order,
        related_offline_order=related_offline_order,
        related_ingredient=related_ingredient
    )
    
    # Send via WebSocket
    send_notification_websocket(notification)
    
    return notification


def send_notification_to_role(role, notification_type, title, message,
                              related_order=None, related_offline_order=None,
                              related_ingredient=None):
    """
    Create and send a notification to all users with a specific role
    
    Args:
        role: Role name ('admin', 'cashier', 'chef')
        notification_type: Type of notification
        title: Notification title
        message: Notification message
        related_order: Related Order instance (optional)
        related_offline_order: Related OfflineOrder instance (optional)
        related_ingredient: Related Ingredient instance (optional)
    """
    try:
        users = User.objects.filter(roles=role)
        notifications = []
        
        # If no users with this role, still create a role-based notification
        # that can be retrieved later when users with that role log in
        if not users.exists():
            # Create a notification without a specific user (role-based only)
            notification = Notification.objects.create(
                user=None,
                role=role,
                notification_type=notification_type,
                title=title,
                message=message,
                related_order=related_order,
                related_offline_order=related_offline_order,
                related_ingredient=related_ingredient
            )
            send_notification_websocket(notification)
            return [notification]
        
        for user in users:
            try:
                notification = Notification.objects.create(
                    user=user,
                    role=role,
                    notification_type=notification_type,
                    title=title,
                    message=message,
                    related_order=related_order,
                    related_offline_order=related_offline_order,
                    related_ingredient=related_ingredient
                )
                notifications.append(notification)
                send_notification_websocket(notification)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to create notification for user {user.id}: {e}", exc_info=True)
                # Continue with other users
        
        return notifications
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error sending notification to role {role}: {e}", exc_info=True)
        return []


def send_notification_to_all(notification_type, title, message,
                             related_order=None, related_offline_order=None,
                             related_ingredient=None):
    """
    Create and send a notification to all users
    
    Args:
        notification_type: Type of notification
        title: Notification title
        message: Notification message
        related_order: Related Order instance (optional)
        related_offline_order: Related OfflineOrder instance (optional)
        related_ingredient: Related Ingredient instance (optional)
    """
    users = User.objects.all()
    notifications = []
    
    for user in users:
        notification = Notification.objects.create(
            user=user,
            role=user.roles,
            notification_type=notification_type,
            title=title,
            message=message,
            related_order=related_order,
            related_offline_order=related_offline_order,
            related_ingredient=related_ingredient
        )
        notifications.append(notification)
        send_notification_websocket(notification)
    
    return notifications


def send_notification_websocket(notification):
    """
    Send notification via WebSocket to connected clients
    
    Args:
        notification: Notification instance
    """
    try:
        if not channel_layer:
            return
        
        from .serializers import NotificationSerializer
        serializer = NotificationSerializer(notification)
        notification_data = serializer.data
        
        # Send to user-specific group
        if notification.user:
            user_group_name = f"notifications_{notification.user.id}_{notification.user.roles}"
            try:
                async_to_sync(channel_layer.group_send)(
                    user_group_name,
                    {
                        'type': 'notification_message',
                        'message': {
                            'type': 'notification',
                            'data': notification_data
                        }
                    }
                )
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to send WebSocket notification to user {notification.user.id}: {e}")
        
        # Send to role-based group
        if notification.role:
            role_group_name = f"notifications_role_{notification.role}"
            try:
                async_to_sync(channel_layer.group_send)(
                    role_group_name,
                    {
                        'type': 'notification_message',
                        'message': {
                            'type': 'notification',
                            'data': notification_data
                        }
                    }
                )
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to send WebSocket notification to role {notification.role}: {e}")
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error sending notification via WebSocket: {e}", exc_info=True)


# Convenience functions for common notification types

def notify_new_order(order):
    """Notify chefs and cashiers about a new order"""
    try:
        # Notify chefs about new order
        send_notification_to_role(
            role='chef',
            notification_type='order',
            title=f'New Order #{order.id}',
            message=f'New {order.order_type} order from {order.customer}',
            related_order=order
        )
        
        # Always notify cashiers about new orders so they can process/confirm them
        cashier_title = f'New Order #{order.id}'
        cashier_message = f'New {order.order_type} order from {order.customer}'
        
        # Add confirmation note if order needs confirmation
        if not order.is_confirmed_cashier:
            cashier_title = f'Order #{order.id} - Needs Confirmation'
            cashier_message = f'Order #{order.id} from {order.customer} needs cashier confirmation'
        
        send_notification_to_role(
            role='cashier',
            notification_type='order',
            title=cashier_title,
            message=cashier_message,
            related_order=order
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error sending new order notification for order {order.id}: {e}", exc_info=True)
        # Don't raise - notifications are non-critical


def notify_order_status_change(order):
    """Notify relevant users about order status change"""
    try:
        if order.status == 'Ready':
            # Notify cashier when order is ready
            send_notification_to_role(
                role='cashier',
                notification_type='order',
                title=f'Order #{order.id} Ready',
                message=f'Order #{order.id} is ready for pickup/delivery',
                related_order=order
            )
        elif order.status == 'Delivered':
            # Notify admin about completed order
            send_notification_to_role(
                role='admin',
                notification_type='order',
                title=f'Order #{order.id} Delivered',
                message=f'Order #{order.id} has been delivered',
                related_order=order
            )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error sending order status change notification for order {order.id}: {e}", exc_info=True)
        # Don't raise - notifications are non-critical


def notify_low_stock(ingredient):
    """Notify admin and chef about low stock"""
    try:
        send_notification_to_role(
            role='admin',
            notification_type='alert',
            title=f'Low Stock Alert: {ingredient.name}',
            message=f'{ingredient.name} stock is below reorder level ({ingredient.stock} {ingredient.unit})',
            related_ingredient=ingredient
        )
        
        send_notification_to_role(
            role='chef',
            notification_type='alert',
            title=f'Low Stock: {ingredient.name}',
            message=f'{ingredient.name} stock is low ({ingredient.stock} {ingredient.unit})',
            related_ingredient=ingredient
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error sending low stock notification for ingredient {ingredient.id}: {e}", exc_info=True)
        # Don't raise - notifications are non-critical


def notify_offline_order(offline_order):
    """Notify chefs about a new offline order"""
    try:
        send_notification_to_role(
            role='chef',
            notification_type='order',
            title=f'New Table Order #{offline_order.id}',
            message=f'New order from Table {offline_order.table.number}',
            related_offline_order=offline_order
        )
        
        # Notify cashier if needs confirmation
        if not offline_order.is_confirmed_cashier:
            send_notification_to_role(
                role='cashier',
                notification_type='order',
                title=f'Table Order #{offline_order.id} Pending',
                message=f'Order from Table {offline_order.table.number} needs confirmation',
                related_offline_order=offline_order
            )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error sending offline order notification for order {offline_order.id}: {e}", exc_info=True)
        # Don't raise - notifications are non-critical

