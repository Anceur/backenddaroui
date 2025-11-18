"""
Django signals for the main app
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db import transaction
from decimal import Decimal
from .models import Order, OrderItem, IngredientStock, IngredientTrace, MenuItemSizeIngredient, MenuItemIngredient, OfflineOrder, OfflineOrderItem, Ingredient
from .notification_utils import notify_new_order, notify_order_status_change, notify_low_stock, notify_offline_order


@receiver(post_save, sender=Order)
def handle_order_created(sender, instance, created, **kwargs):
    """Send notification when a new order is created"""
    if created:
        notify_new_order(instance)


@receiver(pre_save, sender=Order)
def handle_order_status_change(sender, instance, **kwargs):
    """Track order status changes for notifications"""
    if instance.pk:
        try:
            old_instance = Order.objects.get(pk=instance.pk)
            if old_instance.status != instance.status:
                instance._status_changed = True
                instance._old_status = old_instance.status
        except Order.DoesNotExist:
            pass


@receiver(post_save, sender=Order)
def handle_order_status_ready(sender, instance, created, **kwargs):
    """
    Signal handler that processes ingredient usage when an order status changes to 'Ready'.
    
    This signal:
    1. Loops through all OrderItems in the order
    2. For each item with a size, fetches its ingredients (MenuItemSizeIngredient)
    3. Calculates used quantity: ingredient.quantity * order_item.quantity
    4. Subtracts from IngredientStock
    5. Creates IngredientTrace records for tracking
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Only process when status is 'Ready'
    if instance.status != 'Ready':
        return
    
    logger.info(f"🔔 Signal triggered for Order #{instance.id} with status '{instance.status}' (created={created})")
    
    # Check if we already have traces for this order (to avoid reprocessing)
    # This is the most reliable way to detect if we've already processed this order
    existing_traces = IngredientTrace.objects.filter(order=instance).exists()
    if existing_traces:
        existing_count = IngredientTrace.objects.filter(order=instance).count()
        logger.info(f"Order #{instance.id} already has {existing_count} traces, skipping to avoid duplicate processing")
        return
    
    # For existing orders (not new), check if status was actually updated
    # If the flag is set, it means the view explicitly marked this as a status change
    if not created:
        # Check if update_fields indicates status was updated
        update_fields = kwargs.get('update_fields', None)
        logger.info(f"Order #{instance.id} update_fields: {update_fields}")
        if update_fields and 'status' not in update_fields:
            # Status wasn't updated in this save, skip
            logger.info(f"Order #{instance.id} status not in update_fields, skipping")
            return
    
    # Clear the flag if it exists
    if hasattr(instance, '_status_changed_to_ready'):
        delattr(instance, '_status_changed_to_ready')
    
    # Use atomic transaction to ensure data consistency
    with transaction.atomic():
        # Get all order items for this order
        order_items = OrderItem.objects.filter(order=instance)
        
        logger.info(f"Order #{instance.id} has {order_items.count()} OrderItems")
        
        if not order_items.exists():
            # No order items, nothing to process
            logger.warning(
                f"Order #{instance.id} marked as Ready but has no OrderItems. "
                f"Cannot process ingredient usage."
            )
            return
        
        # Get the user who updated the order (from request if available)
        # This will be set in the view when updating the order
        used_by = getattr(instance, '_updated_by_user', None)
        
        # Process each order item
        processed_count = 0
        skipped_no_ingredients = 0
        
        for order_item in order_items:
            logger.info(
                f"Processing OrderItem: {order_item.item.name}, "
                f"Size: {order_item.size.size if order_item.size else 'None'}, "
                f"Qty: {order_item.quantity}"
            )
            
            # Get ingredients based on whether item has size or not
            if order_item.size:
                # Item has size, get ingredients from MenuItemSizeIngredient
                ingredient_links = MenuItemSizeIngredient.objects.filter(size=order_item.size)
                logger.info(f"Found {ingredient_links.count()} ingredients for size {order_item.size.size}")
            else:
                # Item has no size, get ingredients directly from MenuItemIngredient
                ingredient_links = MenuItemIngredient.objects.filter(menu_item=order_item.item)
                logger.info(f"Found {ingredient_links.count()} ingredients for menu item (no size)")
            
            if not ingredient_links.exists():
                skipped_no_ingredients += 1
                size_info = f"size {order_item.size.size}" if order_item.size else "no size"
                logger.warning(f"OrderItem {order_item.id} ({size_info}) has no ingredients, skipping")
                continue
            
            for ingredient_link in ingredient_links:
                ingredient = ingredient_link.ingredient
                
                # Calculate quantity used: ingredient quantity per unit * order item quantity
                quantity_used = Decimal(str(ingredient_link.quantity)) * Decimal(str(order_item.quantity))
                
                # Get or create IngredientStock record
                stock_record, created = IngredientStock.objects.get_or_create(
                    ingredient=ingredient,
                    defaults={'quantity': ingredient.stock}
                )
                
                # Get stock before update
                stock_before = stock_record.quantity
                
                # Ensure we don't go below zero
                stock_after = max(Decimal('0'), stock_before - quantity_used)
                
                # Update stock
                stock_record.quantity = stock_after
                stock_record.save()
                
                # Also update the Ingredient model's stock field for consistency
                ingredient.stock = stock_after
                ingredient.save(update_fields=['stock'])
                
                # Create trace record
                IngredientTrace.objects.create(
                    ingredient=ingredient,
                    order=instance,
                    quantity_used=quantity_used,
                    used_by=used_by,
                    stock_before=stock_before,
                    stock_after=stock_after
                )
                processed_count += 1
        
        # Log processing results
        logger.info(
            f"✅ Order #{instance.id} ingredient processing complete: "
            f"{processed_count} traces created, "
            f"{skipped_no_ingredients} items skipped (no ingredients)"
        )
        
        if processed_count == 0:
            logger.warning(
                f"⚠️ Order #{instance.id} processed but NO traces were created! "
                f"This means no OrderItems had ingredients configured. "
                f"Check that menu items have ingredients added (either via sizes or directly)."
            )
    
    # Send notification for status changes
    if hasattr(instance, '_status_changed') and instance._status_changed:
        notify_order_status_change(instance)


@receiver(post_save, sender=OfflineOrder)
def handle_offline_order_created(sender, instance, created, **kwargs):
    """Send notification when a new offline order is created"""
    if created:
        notify_offline_order(instance)


@receiver(pre_save, sender=OfflineOrder)
def handle_offline_order_status_change(sender, instance, **kwargs):
    """Track offline order status changes for notifications"""
    if instance.pk:
        try:
            old_instance = OfflineOrder.objects.get(pk=instance.pk)
            if old_instance.status != instance.status:
                instance._status_changed = True
                instance._old_status = old_instance.status
        except OfflineOrder.DoesNotExist:
            pass


@receiver(post_save, sender=OfflineOrder)
def handle_offline_order_status_ready(sender, instance, created, **kwargs):
    """
    Signal handler that processes ingredient usage when an offline order status changes to 'Ready'.
    
    This signal:
    1. Loops through all OfflineOrderItems in the order
    2. For each item with a size, fetches its ingredients (MenuItemSizeIngredient)
    3. For each item without a size, fetches its ingredients (MenuItemIngredient)
    4. Calculates used quantity: ingredient.quantity * order_item.quantity
    5. Subtracts from IngredientStock
    6. Creates IngredientTrace records for tracking
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Only process when status is 'Ready'
    if instance.status != 'Ready':
        return
    
    logger.info(f"🔔 Signal triggered for OfflineOrder #{instance.id} with status '{instance.status}' (created={created})")
    
    # Check if we already have traces for this order (to avoid reprocessing)
    existing_traces = IngredientTrace.objects.filter(offline_order=instance).exists()
    if existing_traces:
        existing_count = IngredientTrace.objects.filter(offline_order=instance).count()
        logger.info(f"OfflineOrder #{instance.id} already has {existing_count} traces, skipping to avoid duplicate processing")
        return
    
    # For existing orders (not new), check if status was actually updated
    if not created:
        update_fields = kwargs.get('update_fields', None)
        logger.info(f"OfflineOrder #{instance.id} update_fields: {update_fields}")
        if update_fields and 'status' not in update_fields:
            logger.info(f"OfflineOrder #{instance.id} status not in update_fields, skipping")
            return
    
    # Clear the flag if it exists
    if hasattr(instance, '_status_changed_to_ready'):
        delattr(instance, '_status_changed_to_ready')
    
    # Use atomic transaction to ensure data consistency
    with transaction.atomic():
        # Get all offline order items for this order
        order_items = OfflineOrderItem.objects.filter(offline_order=instance)
        
        logger.info(f"OfflineOrder #{instance.id} has {order_items.count()} OfflineOrderItems")
        
        if not order_items.exists():
            logger.warning(
                f"OfflineOrder #{instance.id} marked as Ready but has no OfflineOrderItems. "
                f"Cannot process ingredient usage."
            )
            return
        
        # Get the user who updated the order (from request if available)
        used_by = getattr(instance, '_updated_by_user', None)
        
        # Process each order item
        processed_count = 0
        skipped_no_ingredients = 0
        
        for order_item in order_items:
            logger.info(
                f"Processing OfflineOrderItem: {order_item.item.name}, "
                f"Size: {order_item.size.size if order_item.size else 'None'}, "
                f"Qty: {order_item.quantity}"
            )
            
            # Get ingredients based on whether item has size or not
            if order_item.size:
                # Item has size, get ingredients from MenuItemSizeIngredient
                ingredient_links = MenuItemSizeIngredient.objects.filter(size=order_item.size)
                logger.info(f"Found {ingredient_links.count()} ingredients for size {order_item.size.size}")
            else:
                # Item has no size, get ingredients directly from MenuItemIngredient
                ingredient_links = MenuItemIngredient.objects.filter(menu_item=order_item.item)
                logger.info(f"Found {ingredient_links.count()} ingredients for menu item (no size)")
            
            if not ingredient_links.exists():
                skipped_no_ingredients += 1
                size_info = f"size {order_item.size.size}" if order_item.size else "no size"
                logger.warning(f"OfflineOrderItem {order_item.id} ({size_info}) has no ingredients, skipping")
                continue
            
            for ingredient_link in ingredient_links:
                ingredient = ingredient_link.ingredient
                
                # Calculate quantity used: ingredient quantity per unit * order item quantity
                quantity_used = Decimal(str(ingredient_link.quantity)) * Decimal(str(order_item.quantity))
                
                # Get or create IngredientStock record
                stock_record, created = IngredientStock.objects.get_or_create(
                    ingredient=ingredient,
                    defaults={'quantity': ingredient.stock}
                )
                
                # Get stock before update
                stock_before = stock_record.quantity
                
                # Ensure we don't go below zero
                stock_after = max(Decimal('0'), stock_before - quantity_used)
                
                # Update stock
                stock_record.quantity = stock_after
                stock_record.save()
                
                # Also update the Ingredient model's stock field for consistency
                ingredient.stock = stock_after
                ingredient.save(update_fields=['stock'])
                
                # Create trace record
                IngredientTrace.objects.create(
                    ingredient=ingredient,
                    offline_order=instance,
                    quantity_used=quantity_used,
                    used_by=used_by,
                    stock_before=stock_before,
                    stock_after=stock_after
                )
                processed_count += 1
        
        # Log processing results
        logger.info(
            f"✅ OfflineOrder #{instance.id} ingredient processing complete: "
            f"{processed_count} traces created, "
            f"{skipped_no_ingredients} items skipped (no ingredients)"
        )
        
        if processed_count == 0:
            logger.warning(
                f"⚠️ OfflineOrder #{instance.id} processed but NO traces were created! "
                f"This means no OfflineOrderItems had ingredients configured. "
                f"Check that menu items have ingredients added (either via sizes or directly)."
            )
    
    # Send notification for status changes
    if hasattr(instance, '_status_changed') and instance._status_changed:
        notify_order_status_change(instance)


@receiver(post_save, sender=Ingredient)
def handle_ingredient_stock_check(sender, instance, created, **kwargs):
    """Check for low stock and send notifications"""
    if instance.is_low_stock:
        notify_low_stock(instance)

