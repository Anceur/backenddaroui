from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class Expense(models.Model):
    CATEGORY_CHOICES = [
        ('staff', 'Staff'),
        ('waste', 'Waste/Loss'),
        ('utilities', 'Utilities'),
        ('repairs', 'Repairs'),
        ('operational', 'Operational'),
        ('other', 'Other'),
    ]

    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    title = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    ingredient = models.ForeignKey('Ingredient', on_delete=models.SET_NULL, null=True, blank=True, related_name='waste_expenses')
    quantity = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Quantity of ingredient wasted")
    staff_member = models.ForeignKey('StaffMember', on_delete=models.SET_NULL, null=True, blank=True, related_name='expenses')
    notes = models.TextField(blank=True)
    date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    image = models.URLField(blank=True, null=True)  # ← Fixed: 4 spaces
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name = "Expense"
        verbose_name_plural = "Expenses"

    def __str__(self):
        return f"{self.title} - {self.amount} - {self.date}"
# Cloudinary import (commented out - using local storage)
# from cloudinary.models import CloudinaryField
# Create your models here.
class CustomUser(AbstractUser):
    roles = models.CharField(
        max_length=100, 
        choices=[('admin', 'Admin'), ('cashier', 'Cashier'), ('chef', 'Chef')]
    )
    USERNAME_FIELD = 'username'

    def save(self, *args, **kwargs):
        # Only hash password if it's a plain text password (not already hashed)
        # set_password() already hashes the password, so we check if it's already hashed
        if self.password and not self.password.startswith(('pbkdf2_', 'bcrypt', 'argon2')):
            self.set_password(self.password)
        super().save(*args, **kwargs)
class Profile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='profiles/', null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=200, blank=True)

class StaffMember(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='staff_member')
    name = models.CharField(max_length=200)
    role = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=200, blank=True)
    image = models.ImageField(upload_to='staff/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.role}"

class MenuItem(models.Model):
    CATEGORY_CHOICES = [
        ('burger', 'Burger'),
        ('pizza', 'Pizza'),
        ('sandwich', 'Sandwich & Specials'),
        ('plat', 'Plat'),
        ('tacos', 'Tacos'),
        ('desserts', 'Desserts'),
        ('drinks', 'Drinks'),
    ]

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=6, decimal_places=2, help_text="Selling price")
    cost_price = models.DecimalField(max_digits=6, decimal_places=2, default=0.00, help_text="Cost price for profit calculation")
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    image = models.ImageField(upload_to='menu_items/', blank=True, null=True)
    featured = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Sync 'Medium' size price if it exists to match this base item price
        # This ensures bidirectional consistency
        self.sizes.filter(size='M').update(
            price=self.price, 
            cost_price=self.cost_price
        )


class MenuItemSize(models.Model):
    SIZE_CHOICES = [
        ('XS', 'Extra Small'),
        ('S', 'Small'),
        ('M', 'Medium'),
        ('L', 'Large'),
        ('XL', 'Extra Large'),
        ('Mega', 'Mega'),
        ('Family', 'Family'),
    ]

    menu_item = models.ForeignKey(MenuItem, related_name='sizes', on_delete=models.CASCADE)
    size = models.CharField(max_length=10, choices=SIZE_CHOICES)
    price = models.DecimalField(max_digits=6, decimal_places=2, help_text="Selling price")
    cost_price = models.DecimalField(max_digits=6, decimal_places=2, default=0.00, help_text="Cost price for profit calculation")

    def __str__(self):
        return f"{self.menu_item.name} - {self.size}"

    def save(self, *args, **kwargs):
        # Sync parent MenuItem price/cost if this is the standard 'Medium' size
        if self.size == 'M':
            # We need to update the parent MenuItem
            # Use update_fields in future if we want to be more specific, 
            # but getting the item and saving it is safer to trigger its own save logic if any.
            self.menu_item.price = self.price
            self.menu_item.cost_price = self.cost_price
            self.menu_item.save()
        
        super().save(*args, **kwargs)



class Order(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Confirmed', 'Confirmed'),
        ('Cancelled', 'Cancelled'),
      
    ]
    
    ORDER_TYPE_CHOICES = [
        ('delivery', 'Delivery'),
        ('dine_in', 'Dine In'),
        ('takeaway', 'Takeaway'),
    ]
    
    id = models.AutoField(primary_key=True)
    customer = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    address = models.CharField(max_length=255, blank=True, help_text="Delivery address or table number for dine-in")
    items = models.JSONField(default=list, help_text="List of item names")
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=100.00, help_text="Fixed tax amount (e.g., 100 DA)")
    total = models.DecimalField(max_digits=15, decimal_places=2)
    revenue = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, help_text="Revenue calculated as sell price - cost price (no tax)")
    is_confirmed_cashier = models.BooleanField(
        default=False,
        help_text="Whether the cashier has confirmed this order"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    order_type = models.CharField(max_length=20, choices=ORDER_TYPE_CHOICES, default='delivery', help_text="Type of order: delivery, dine_in, or takeaway")
    table_number = models.CharField(max_length=10, blank=True, null=True, help_text="Table number for dine-in orders")
    notes = models.TextField(blank=True, default='', help_text="Additional notes or special instructions for the order")
    loyalty_number = models.CharField(max_length=20, blank=True, null=True, help_text="Loyalty card number entered by the customer")
    loyal_customer = models.ForeignKey('ClientFidele', on_delete=models.SET_NULL, null=True, blank=True, related_name='orders', help_text="Loyal customer if applicable")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Order #{self.id} - {self.customer}"
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    item = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    size = models.ForeignKey(MenuItemSize, null=True, blank=True, on_delete=models.SET_NULL)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        size_info = f" - {self.size.size}" if self.size else ""
        return f"{self.item.name}{size_info} x {self.quantity}"
class Supplier(models.Model):
    """Supplier model for managing restaurant suppliers"""
    name = models.CharField(max_length=200, help_text="Supplier name")
    phone = models.CharField(max_length=20, help_text="Supplier phone number")
    supplier_type = models.CharField(
        max_length=50,
        help_text="Type of supplier",
        blank=True
    )
    debt = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="Current debt amount owed to supplier"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = "Supplier"
        verbose_name_plural = "Suppliers"
    
    def __str__(self):
        return f"{self.name} ({self.supplier_type})"


class SupplierHistory(models.Model):
    """Tracks supplier transaction history (purchases, payments, etc.)"""
    TRANSACTION_TYPES = [
        ('purchase', 'Purchase'),
        ('payment', 'Payment'),
    
    ]
    
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.CASCADE,
        related_name='history',
        help_text="Supplier associated with this transaction"
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPES,
        help_text="Type of transaction"
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Transaction amount (positive for purchases/debt, negative for payments)"
    )
    description = models.TextField(
        blank=True,
        help_text="Description or notes about the transaction"
    )
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='supplier_transactions',
        help_text="User who created this transaction"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Supplier History"
        verbose_name_plural = "Supplier Histories"
    
    def __str__(self):
        return f"{self.supplier.name} - {self.get_transaction_type_display()} - {self.amount}"


class SupplierTransactionItem(models.Model):
    """Items included in a supplier purchase transaction"""
    supplier_history = models.ForeignKey(
        SupplierHistory,
        on_delete=models.CASCADE,
        related_name='items',
        help_text="The parent transaction"
    )
    ingredient = models.ForeignKey(
        'Ingredient',  # String reference since Ingredient is defined below
        on_delete=models.CASCADE,
        related_name='transaction_items',
        help_text="The ingredient purchased"
    )
    quantity = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text="Quantity purchased"
    )
    price_per_unit = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text="Price per unit at the time of purchase"
    )
    total_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text="Total price for this item (quantity * price_per_unit)"
    )
    
    class Meta:
        verbose_name = "Supplier Transaction Item"
        verbose_name_plural = "Supplier Transaction Items"
        
    def __str__(self):
        return f"{self.ingredient.name} x {self.quantity} in {self.supplier_history}"

    def save(self, *args, **kwargs):
        if not self.total_price and self.quantity and self.price_per_unit:
            self.total_price = self.quantity * self.price_per_unit
        super().save(*args, **kwargs)



class Ingredient(models.Model):
    name = models.CharField(max_length=100)
    unit = models.CharField(max_length=20, default="g")  # optional: g, ml, piece
    stock = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Current stock quantity")
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Cost per unit")
    reorder_level = models.DecimalField(max_digits=10, decimal_places=2, default=10, help_text="Reorder level threshold")
    suppliers = models.ManyToManyField(
        Supplier,
        related_name='ingredients',
        blank=True,
        help_text="Suppliers who provide this ingredient"
    )

    def __str__(self):
        return self.name
    
    @property
    def is_low_stock(self):
        """Check if stock is below reorder level"""
        return self.stock <= self.reorder_level


class MenuItemIngredient(models.Model):
    """Ingredients for menu items without sizes"""
    menu_item = models.ForeignKey(
        MenuItem,
        related_name='item_ingredients',
        on_delete=models.CASCADE
    )
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=6, decimal_places=2)

    class Meta:
        unique_together = ['menu_item', 'ingredient']

    def __str__(self):
        return f"{self.menu_item.name} - {self.quantity}{self.ingredient.unit} {self.ingredient.name}"


class MenuItemSizeIngredient(models.Model):
    """Ingredients for menu items with sizes"""
    size = models.ForeignKey(
        MenuItemSize,
        related_name='ingredients',
        on_delete=models.CASCADE
    )
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=6, decimal_places=2)

    def __str__(self):
        return f"{self.size.menu_item.name} [{self.size.size}] - {self.quantity}{self.ingredient.unit} {self.ingredient.name}"


class IngredientStock(models.Model):
    """Tracks current stock levels for ingredients"""
    ingredient = models.OneToOneField(
        Ingredient,
        on_delete=models.CASCADE,
        related_name='stock_record'
    )
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Current stock quantity"
    )
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Ingredient Stock"
        verbose_name_plural = "Ingredient Stocks"
        ordering = ['ingredient__name']
    
    def __str__(self):
        return f"{self.ingredient.name}: {self.quantity} {self.ingredient.unit}"


class IngredientTrace(models.Model):
    """Tracks ingredient usage history"""
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name='traces'
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='ingredient_traces',
        null=True,
        blank=True
    )
    offline_order = models.ForeignKey(
        'OfflineOrder',
        on_delete=models.CASCADE,
        related_name='ingredient_traces',
        null=True,
        blank=True,
        help_text="Offline order that used this ingredient"
    )
    quantity_used = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Quantity of ingredient used"
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    used_by = models.ForeignKey(
        CustomUser,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='ingredient_usage_traces'
    )
    stock_before = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Stock quantity before this usage"
    )
    stock_after = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Stock quantity after this usage"
    )
    notes = models.TextField(blank=True, null=True, help_text="Notes about the usage")
    
    class Meta:
        verbose_name = "Ingredient Trace"
        verbose_name_plural = "Ingredient Traces"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['ingredient', '-timestamp']),
        ]
    
    def __str__(self):
        if self.order:
            order_info = f"Order #{self.order.id}"
        elif self.offline_order:
            order_info = f"Offline Order #{self.offline_order.id} (Table {self.offline_order.table.number})"
        else:
            order_info = "Manual"
        user_info = f" by {self.used_by.username}" if self.used_by else ""
        return f"{self.ingredient.name}: {self.quantity_used}{self.ingredient.unit} ({order_info}{user_info})"


class Table(models.Model):
    """Restaurant table model"""
    number = models.CharField(max_length=10, unique=True, help_text="Table number (e.g., '1', '2', 'VIP-1')")
    capacity = models.PositiveIntegerField(default=4, help_text="Maximum number of guests")
    is_available = models.BooleanField(default=True, help_text="Whether the table is currently available")
    location = models.CharField(max_length=100, blank=True, help_text="Table location (e.g., 'Window', 'Patio', 'Main Hall')")
    notes = models.TextField(blank=True, help_text="Additional notes about the table")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['number']
        verbose_name = "Table"
        verbose_name_plural = "Tables"
    
    def __str__(self):
        return f"Table {self.number}"
        
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        if not is_new:
            old_table = Table.objects.get(pk=self.pk)
            if old_table.is_available != self.is_available:
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"TABLE STATE CHANGE: Table {self.number} changed is_available from {old_table.is_available} to {self.is_available}")
        else:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"TABLE CREATED: Table {self.number} with is_available={self.is_available}")
            
        super().save(*args, **kwargs)


class TableSession(models.Model):
    """Secure session for table access via QR code tokens"""
    table = models.ForeignKey(
        Table,
        on_delete=models.CASCADE,
        related_name='sessions',
        help_text="Table this session is for"
    )
    token = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="Secure token for accessing this table"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this session is currently active"
    )
    expires_at = models.DateTimeField(
        help_text="When this session expires"
    )
    last_accessed = models.DateTimeField(
        auto_now=True,
        help_text="Last time this session was accessed"
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of the client accessing this session"
    )
    user_agent = models.CharField(
        max_length=255,
        blank=True,
        help_text="User agent of the client"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this session was created"
    )
    order_placed = models.BooleanField(
        default=False,
        help_text="Whether an order has been placed in this session"
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Table Session"
        verbose_name_plural = "Table Sessions"
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['table', 'is_active']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"Session for Table {self.table.number} - {self.token[:8]}..."
    
    def is_expired(self):
        """Check if session has expired"""
        from django.utils import timezone
        return timezone.now() > self.expires_at
    
    def is_valid(self):
        """Check if session is valid (active and not expired)"""
        return self.is_active and not self.is_expired()


class OfflineOrder(models.Model):
    """Offline orders for dine-in customers"""
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Confirmed', 'Confirmed'),
        ('Cancelled', 'Cancelled'),
       
    ]
    
    table = models.ForeignKey(
        Table,
        on_delete=models.CASCADE,
        related_name='offline_orders',
        help_text="Table number for this order",
        null=True,
        blank=True
    )
    is_imported = models.BooleanField(default=False, help_text="Whether this order was imported from an external source")
    total = models.DecimalField(max_digits=15, decimal_places=2)
    revenue = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, help_text="Revenue calculated as sell price - cost price (no tax)")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    is_confirmed_cashier = models.BooleanField(
        default=False,
        help_text="Whether the cashier has confirmed this order"
    )
    notes = models.TextField(blank=True, help_text="Special instructions or notes for the order")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Offline Order"
        verbose_name_plural = "Offline Orders"
    
    def __str__(self):
        table_info = f"Table {self.table.number}" if self.table else ("Imported Order" if self.is_imported else "No Table")
        return f"Offline Order #{self.id} - {table_info}"


class OfflineOrderItem(models.Model):
    """Items in an offline order"""
    offline_order = models.ForeignKey(
        OfflineOrder,
        on_delete=models.CASCADE,
        related_name='items'
    )
    item = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    size = models.ForeignKey(MenuItemSize, null=True, blank=True, on_delete=models.SET_NULL)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price at time of order")
    notes = models.CharField(max_length=255, blank=True, help_text="Special instructions for this item")
    
    class Meta:
        verbose_name = "Offline Order Item"
        verbose_name_plural = "Offline Order Items"
    
    def __str__(self):
        size_info = f" - {self.size.size}" if self.size else ""
        table_info = f" (Table {self.offline_order.table.number})" if self.offline_order.table else ""
        return f"{self.item.name}{size_info} x {self.quantity}{table_info}"


class Notification(models.Model):
    """Real-time notifications for users"""
    TYPE_CHOICES = [
        ('order', 'Order'),
        ('alert', 'Alert'),
        ('info', 'Info'),
        ('ingredient', 'Ingredient'),
        ('table', 'Table'),
    ]
    
    PRIORITY_CHOICES = [
        ('critical', 'Critical'),  # Real-time + sound
        ('medium', 'Medium'),      # Real-time only (no sound)
        ('low', 'Low'),            # Daily digest (no real-time)
    ]
    
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='notifications',
        null=True,
        blank=True,
        help_text="Specific user to notify (null for all users or role-based)"
    )
    role = models.CharField(
        max_length=20,
        choices=[('admin', 'Admin'), ('cashier', 'Cashier'), ('chef', 'Chef')],
        null=True,
        blank=True,
        help_text="Role to notify (null for all roles)"
    )
    notification_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='info'
    )
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='medium',
        help_text="Notification priority: critical (sound+real-time), medium (real-time only), low (daily digest)"
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    related_order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications'
    )
    related_offline_order = models.ForeignKey(
        OfflineOrder,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications'
    )
    related_ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['role', '-created_at']),
            models.Index(fields=['is_read', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.notification_type}: {self.title}"


class ClientFidele(models.Model):
    """Loyal customer model"""
    name = models.CharField(max_length=100, help_text="Customer name")
    phone = models.CharField(max_length=20, unique=True, help_text="Customer phone number")
    loyalty_card_number = models.CharField(
        max_length=20, 
        unique=True, 
        blank=True, 
        help_text="Unique loyalty card number (auto-generated if empty)"
    )
    total_spent = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=0.00, 
        help_text="Total amount spent by this customer"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Loyal Customer"
        verbose_name_plural = "Loyal Customers"

    def save(self, *args, **kwargs):
        if not self.loyalty_card_number:
            # Generate a unique 8-digit loyalty number
            import random
            import string
            while True:
                new_number = ''.join(random.choices(string.digits, k=8))
                if not ClientFidele.objects.filter(loyalty_card_number=new_number).exists():
                    self.loyalty_card_number = new_number
                    break
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.loyalty_card_number})"

class Promotion(models.Model):
    PROMOTION_TYPE_CHOICES = [
        ('percentage', 'Percentage Discount'),
        ('fixed_amount', 'Fixed Amount Discount'),
        ('combo_fixed_price', 'Combo Fixed Price'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('archived', 'Archived'),
    ]

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, help_text="Short teaser for the promotion banner")
    promotion_type = models.CharField(max_length=20, choices=PROMOTION_TYPE_CHOICES)
    value = models.DecimalField(max_digits=10, decimal_places=2, help_text='Discount percentage, fixed amount, or combo price')
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # For simple discounts (percentage/fixed) applied to specific products or sizes
    applicable_items = models.ManyToManyField('MenuItem', blank=True, related_name='promotions')
    applicable_sizes = models.ManyToManyField('MenuItemSize', blank=True, related_name='promotions')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    @property
    def display_status(self):
        now = timezone.now()
        if self.status == 'draft':
            return 'Draft'
        if self.status == 'archived':
            return 'Ended'
        if not self.is_active:
            return 'Paused'
        if now < self.start_date:
            return 'Scheduled'
        if now > self.end_date:
            return 'Ended'
        return 'Live'

    def __str__(self):
        return self.name

class PromotionItem(models.Model):
    '''Items included in a Combo Promotion'''
    promotion = models.ForeignKey(Promotion, on_delete=models.CASCADE, related_name='combo_items')
    menu_item = models.ForeignKey('MenuItem', on_delete=models.CASCADE)
    menu_item_size = models.ForeignKey('MenuItemSize', null=True, blank=True, on_delete=models.SET_NULL)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        size_info = f" ({self.menu_item_size.size})" if self.menu_item_size else ""
        return f'{self.quantity} x {self.menu_item.name}{size_info} in {self.promotion.name}'


class RestaurantInfo(models.Model):
    """Model to store restaurant configuration like opening hours"""
    opening_time = models.TimeField(help_text="Restaurant opening time")
    closing_time = models.TimeField(help_text="Restaurant closing time")
    
    class Meta:
        verbose_name = "Restaurant Info"
        verbose_name_plural = "Restaurant Info"

    def __str__(self):
        return f"Open: {self.opening_time} - Close: {self.closing_time}"

