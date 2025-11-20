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
                             related_ingredient=None, priority='medium'):
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
        priority: Notification priority ('critical', 'medium', 'low')
    """
    if isinstance(user, int):
        user = User.objects.get(id=user)
    
    # Create notification in database
    notification = Notification.objects.create(
        user=user,
        role=user.roles,
        notification_type=notification_type,
        priority=priority,
        title=title,
        message=message,
        related_order=related_order,
        related_offline_order=related_offline_order,
        related_ingredient=related_ingredient
    )
    
    # Only send via WebSocket if not low priority (low priority goes to daily digest)
    if priority != 'low':
        send_notification_websocket(notification)
    
    return notification


def send_notification_to_role(role, notification_type, title, message,
                              related_order=None, related_offline_order=None,
                              related_ingredient=None, priority='medium'):
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
        priority: Notification priority ('critical', 'medium', 'low')
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"send_notification_to_role called: role={role}, title={title}, priority={priority}")
        users = User.objects.filter(roles=role)
        logger.info(f"Found {users.count()} users with role '{role}'")
        notifications = []
        
        # If no users with this role, still create a role-based notification
        # that can be retrieved later when users with that role log in
        if not users.exists():
            logger.info(f"No users found with role '{role}', creating role-based notification")
            # Create a notification without a specific user (role-based only)
            notification = Notification.objects.create(
                user=None,
                role=role,
                notification_type=notification_type,
                priority=priority,
                title=title,
                message=message,
                related_order=related_order,
                related_offline_order=related_offline_order,
                related_ingredient=related_ingredient
            )
            # Refresh from database to ensure priority was saved correctly
            notification.refresh_from_db()
            logger.info(f"Created role-based notification {notification.id} for role '{role}' with priority={notification.priority} (expected: {priority})")
            if notification.priority != priority:
                logger.error(f"PRIORITY MISMATCH! Notification {notification.id} has priority '{notification.priority}' but expected '{priority}'")
            # Only send via WebSocket if not low priority
            if priority != 'low':
                send_notification_websocket(notification)
            return [notification]
        
        for user in users:
            try:
                logger.info(f"Creating notification for user {user.id} ({user.username}) with role '{role}'")
                notification = Notification.objects.create(
                    user=user,
                    role=role,
                    notification_type=notification_type,
                    priority=priority,
                    title=title,
                    message=message,
                    related_order=related_order,
                    related_offline_order=related_offline_order,
                    related_ingredient=related_ingredient
                )
                # Refresh from database to ensure priority was saved correctly
                notification.refresh_from_db()
                logger.info(f"Successfully created notification {notification.id} for user {user.id} with priority={notification.priority} (expected: {priority})")
                if notification.priority != priority:
                    logger.error(f"PRIORITY MISMATCH! Notification {notification.id} has priority '{notification.priority}' but expected '{priority}'")
                notifications.append(notification)
                # Only send via WebSocket if not low priority
                if priority != 'low':
                    send_notification_websocket(notification)
            except Exception as e:
                logger.error(f"Failed to create notification for user {user.id}: {e}", exc_info=True)
                # Continue with other users
        
        logger.info(f"send_notification_to_role completed: created {len(notifications)} notifications")
        return notifications
    except Exception as e:
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
        
        # Debug: Log the priority being sent
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"WebSocket notification data - ID: {notification.id}, Priority: {notification_data.get('priority')}, Title: {notification_data.get('title')}")
        
        # If notification has a specific user, send only to that user's group
        # This prevents duplicates when user is also subscribed to role group
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
        # If no specific user, send to role-based group (for role-based notifications)
        elif notification.role:
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
    """Notify cashiers and admin about a new order (NOT chefs - chefs only get confirmed orders)"""
    try:
        # NOTE: Chefs do NOT get new order notifications - they only get confirmed order notifications
        
        # Notify cashiers about ALL new orders (CRITICAL - with sound)
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
            related_order=order,
            priority='critical'  # Critical: real-time + sound for cashiers
        )
        
        # Notify admin about NEW ONLINE ORDERS ONLY (critical - real-time + sound)
        # Do NOT notify admin about offline/local cashier orders
        if order.order_type in ['delivery', 'takeaway']:  # Only online orders
            send_notification_to_role(
                role='admin',
                notification_type='order',
                title=f'New Online Order #{order.id}',
                message=f'New {order.order_type} order from {order.customer}',
                related_order=order,
                priority='critical'  # Critical: real-time + sound
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
            # Notify cashier when order is ready (medium priority)
            send_notification_to_role(
                role='cashier',
                notification_type='order',
                title=f'Order #{order.id} Ready',
                message=f'Order #{order.id} is ready for pickup/delivery',
                related_order=order,
                priority='medium'
            )
            # Notify admin when order is ready (medium priority - real-time, no sound)
            send_notification_to_role(
                role='admin',
                notification_type='order',
                title=f'Order #{order.id} Ready',
                message=f'Order #{order.id} is ready for pickup/delivery',
                related_order=order,
                priority='medium'
            )
        elif order.status == 'Preparing':
            # Notify admin when chef starts preparing (medium priority - real-time, no sound)
            send_notification_to_role(
                role='admin',
                notification_type='order',
                title=f'Order #{order.id} Being Prepared',
                message=f'Chef is preparing order #{order.id} from {order.customer}',
                related_order=order,
                priority='medium'
            )
        elif order.status == 'Delivered':
            # Notify admin about completed order (low priority - daily digest)
            send_notification_to_role(
                role='admin',
                notification_type='order',
                title=f'Order #{order.id} Delivered',
                message=f'Order #{order.id} has been delivered',
                related_order=order,
                priority='low'  # Low priority - goes to daily digest
            )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error sending order status change notification for order {order.id}: {e}", exc_info=True)
        # Don't raise - notifications are non-critical


def notify_low_stock(ingredient):
    """Notify admin and chef about low stock or out of stock
    
    Both low stock (below reorder level) and out of stock (stock <= 0) 
    are CRITICAL priority for admin (with sound).
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"notify_low_stock called for ingredient {ingredient.id} ({ingredient.name}): stock={ingredient.stock}, reorder_level={ingredient.reorder_level}")
        
        # Determine if it's out of stock (stock <= 0) or just low stock (below reorder level)
        is_out_of_stock = ingredient.stock <= 0
        
        # Admin gets CRITICAL priority for BOTH low stock AND out of stock (critical - real-time + sound)
        priority = 'critical'  # Both low stock and out of stock are CRITICAL for admin
        title = f'Out of Stock: {ingredient.name}' if is_out_of_stock else f'Low Stock Alert: {ingredient.name}'
        message = f'{ingredient.name} is {"out of stock" if is_out_of_stock else f"running low. Current stock: {ingredient.stock} {ingredient.unit} (reorder level: {ingredient.reorder_level} {ingredient.unit})"}'
        
        logger.info(f"Sending CRITICAL notification to admin for ingredient {ingredient.name} (out_of_stock={is_out_of_stock}) with priority='critical'")
        admin_notifications = send_notification_to_role(
            role='admin',
            notification_type='alert',
            title=title,
            message=message,
            related_ingredient=ingredient,
            priority='critical'  # CRITICAL: Both low stock and out of stock are critical for admin (real-time + sound)
        )
        logger.info(f"Created {len(admin_notifications)} admin notifications for low stock alert")
        
        # Chef gets medium priority (real-time, no sound)
        logger.info(f"Sending medium notification to chef for ingredient {ingredient.name}")
        chef_notifications = send_notification_to_role(
            role='chef',
            notification_type='alert',
            title=f'Low Stock: {ingredient.name}',
            message=f'{ingredient.name} stock is low ({ingredient.stock} {ingredient.unit})',
            related_ingredient=ingredient,
            priority='medium'
        )
        logger.info(f"Created {len(chef_notifications)} chef notifications for low stock alert")
        
        return admin_notifications + chef_notifications
    except Exception as e:
        logger.error(f"Error sending low stock notification for ingredient {ingredient.id}: {e}", exc_info=True)
        # Don't raise - notifications are non-critical
        return []


def notify_offline_order(offline_order):
    """Notify cashiers about a new offline order (NOT chefs or admin - chefs only get confirmed orders)"""
    try:
        # NOTE: Chefs do NOT get new offline order notifications - they only get confirmed order notifications
        
        # Notify cashiers about new offline orders (CRITICAL - with sound)
        if not offline_order.is_confirmed_cashier:
            send_notification_to_role(
                role='cashier',
                notification_type='order',
                title=f'Table Order #{offline_order.id} - Needs Confirmation',
                message=f'Order from Table {offline_order.table.number} needs confirmation',
                related_offline_order=offline_order,
                priority='critical'  # Critical: real-time + sound for cashiers
            )
        
        # NOTE: Admin does NOT get notified about offline orders - only online orders
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error sending offline order notification for order {offline_order.id}: {e}", exc_info=True)
        # Don't raise - notifications are non-critical


def notify_order_confirmed_by_cashier(order, order_type='online'):
    """
    Notify chefs when cashier confirms an order (chefs ONLY get confirmed orders, not new orders)
    
    Args:
        order: Order or OfflineOrder instance
        order_type: 'online' or 'offline'
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"notify_order_confirmed_by_cashier called: order_id={order.id}, order_type={order_type}")
        
        if order_type == 'online':
            # NOTE: Cashiers do NOT get confirmed order notifications - they only get new order notifications
            
            # Notify chefs about confirmed online order (CRITICAL - with sound)
            logger.info(f"Sending notification to chefs for confirmed online order {order.id} with priority='critical'")
            chef_notifications = send_notification_to_role(
                role='chef',
                notification_type='order',
                title=f'Order #{order.id} Confirmed - Ready to Prepare',
                message=f'Order #{order.id} from {order.customer} has been confirmed by cashier. Ready to start preparing.',
                related_order=order,
                priority='critical'  # Critical: real-time + sound for chefs
            )
            # Verify priority was set correctly
            if chef_notifications:
                for notif in chef_notifications:
                    logger.info(f"Created notification {notif.id} with priority: {notif.priority}")
                    if notif.priority != 'critical':
                        logger.error(f"ERROR: Notification {notif.id} has wrong priority! Expected 'critical', got '{notif.priority}'")
            
            # Notify admin (medium priority - real-time, no sound)
            admin_notifications = send_notification_to_role(
                role='admin',
                notification_type='order',
                title=f'Order #{order.id} Confirmed by Cashier',
                message=f'Order #{order.id} from {order.customer} has been confirmed by cashier',
                related_order=order,
                priority='medium'
            )
            
            logger.info(f"Created {len(chef_notifications)} chef and {len(admin_notifications)} admin notifications for order {order.id}")
            return chef_notifications + admin_notifications
        elif order_type == 'offline':
            table_info = f'Table {order.table.number}' if order.table else 'Table'
            
            # NOTE: Cashiers do NOT get confirmed order notifications - they only get new order notifications
            
            # Notify chefs about confirmed offline order (CRITICAL - with sound)
            logger.info(f"Sending notification to chefs for confirmed offline order {order.id} with priority='critical'")
            chef_notifications = send_notification_to_role(
                role='chef',
                notification_type='order',
                title=f'Table Order #{order.id} Confirmed - Ready to Prepare',
                message=f'Order #{order.id} from {table_info} has been confirmed by cashier. Ready to start preparing.',
                related_offline_order=order,
                priority='critical'  # Critical: real-time + sound for chefs
            )
            # Verify priority was set correctly
            if chef_notifications:
                for notif in chef_notifications:
                    logger.info(f"Created notification {notif.id} with priority: {notif.priority}")
                    if notif.priority != 'critical':
                        logger.error(f"ERROR: Notification {notif.id} has wrong priority! Expected 'critical', got '{notif.priority}'")
            
            # Notify admin (medium priority - real-time, no sound)
            admin_notifications = send_notification_to_role(
                role='admin',
                notification_type='order',
                title=f'Table Order #{order.id} Confirmed by Cashier',
                message=f'Table order #{order.id} from {table_info} has been confirmed by cashier',
                related_offline_order=order,
                priority='medium'
            )
            
            logger.info(f"Created {len(chef_notifications)} chef and {len(admin_notifications)} admin notifications for offline order {order.id}")
            return chef_notifications + admin_notifications
        else:
            logger.warning(f"Unknown order_type: {order_type}")
            return []
    except Exception as e:
        logger.error(f"Error sending order confirmation notification for {order_type} order {order.id}: {e}", exc_info=True)
        # Don't raise - notifications are non-critical
        return []


# Admin-specific notification functions

def notify_chef_prepared_order(order, order_type='online'):
    """
    Notify admin when chef prepares an order (medium priority - real-time, no sound)
    
    Args:
        order: Order or OfflineOrder instance
        order_type: 'online' or 'offline'
    """
    try:
        if order_type == 'online':
            send_notification_to_role(
                role='admin',
                notification_type='order',
                title=f'Order #{order.id} Being Prepared',
                message=f'Chef is preparing order #{order.id} from {order.customer}',
                related_order=order,
                priority='medium'  # Real-time, no sound
            )
        elif order_type == 'offline':
            table_info = f'Table {order.table.number}' if order.table else 'Table'
            send_notification_to_role(
                role='admin',
                notification_type='order',
                title=f'Table Order #{order.id} Being Prepared',
                message=f'Chef is preparing table order #{order.id} from {table_info}',
                related_offline_order=order,
                priority='medium'  # Real-time, no sound
            )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error sending chef prepared order notification: {e}", exc_info=True)


def notify_table_change(table, change_type='occupied'):
    """
    Notify admin about table status changes (medium priority - real-time, no sound)
    
    Args:
        table: Table instance
        change_type: 'occupied', 'free', or 'reserved'
    """
    try:
        change_messages = {
            'occupied': f'Table {table.number} is now occupied',
            'free': f'Table {table.number} is now available',
            'reserved': f'Table {table.number} has been reserved'
        }
        
        send_notification_to_role(
            role='admin',
            notification_type='table',
            title=f'Table {table.number} Status Changed',
            message=change_messages.get(change_type, f'Table {table.number} status changed'),
            priority='medium'  # Real-time, no sound
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error sending table change notification: {e}", exc_info=True)


def notify_ingredient_trace_created(ingredient_trace):
    """
    Notify admin when ingredient trace is created (low priority - daily digest, no real-time)
    
    Args:
        ingredient_trace: IngredientTrace instance
    """
    try:
        send_notification_to_role(
            role='admin',
            notification_type='ingredient',
            title=f'Ingredient Trace Created: {ingredient_trace.ingredient.name}',
            message=f'New trace entry for {ingredient_trace.ingredient.name}: {ingredient_trace.quantity_used} {ingredient_trace.ingredient.unit}',
            related_ingredient=ingredient_trace.ingredient,
            priority='low'  # Low priority: daily digest (no real-time, no sound)
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error sending ingredient trace notification: {e}", exc_info=True)


def notify_inventory_received(ingredient, quantity):
    """
    Notify admin when inventory is received (medium priority - real-time, no sound)
    
    Args:
        ingredient: Ingredient instance
        quantity: Quantity received
    """
    try:
        send_notification_to_role(
            role='admin',
            notification_type='ingredient',
            title=f'Inventory Received: {ingredient.name}',
            message=f'Received {quantity} {ingredient.unit} of {ingredient.name}. New stock: {ingredient.stock} {ingredient.unit}',
            related_ingredient=ingredient,
            priority='medium'  # Real-time, no sound
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error sending inventory received notification: {e}", exc_info=True)


def notify_unauthorized_attempt(user, action):
    """
    Notify admin about unauthorized access attempts (medium priority - real-time, no sound)
    
    Args:
        user: User instance who attempted unauthorized action
        action: Description of the attempted action
    """
    try:
        send_notification_to_role(
            role='admin',
            notification_type='alert',
            title=f'Unauthorized Access Attempt',
            message=f'User {user.username} attempted unauthorized action: {action}',
            priority='medium'  # Real-time, no sound
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error sending unauthorized attempt notification: {e}", exc_info=True)
