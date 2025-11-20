from django.db import models
from django.contrib.auth.models import AbstractUser
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
    price = models.DecimalField(max_digits=6, decimal_places=2)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    image = models.ImageField(upload_to='menu_items/', blank=True, null=True)
    featured = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class MenuItemSize(models.Model):
    SIZE_CHOICES = [
        ('M', 'Medium'),
        ('L', 'Large'),
        ('Mega', 'Mega'),
    ]

    menu_item = models.ForeignKey(MenuItem, related_name='sizes', on_delete=models.CASCADE)
    size = models.CharField(max_length=10, choices=SIZE_CHOICES)
    price = models.DecimalField(max_digits=6, decimal_places=2)

    def __str__(self):
        return f"{self.menu_item.name} - {self.size}"



class Order(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Preparing', 'Preparing'),
        ('Ready', 'Ready'),
        ('Delivered', 'Delivered'),
        ('Canceled', 'Canceled'),
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
    total = models.DecimalField(max_digits=15, decimal_places=2)
    is_confirmed_cashier = models.BooleanField(
        default=False,
        help_text="Whether the cashier has confirmed this order"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    order_type = models.CharField(max_length=20, choices=ORDER_TYPE_CHOICES, default='delivery', help_text="Type of order: delivery, dine_in, or takeaway")
    table_number = models.CharField(max_length=10, blank=True, null=True, help_text="Table number for dine-in orders")
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
class Ingredient(models.Model):
    name = models.CharField(max_length=100)
    unit = models.CharField(max_length=20, default="g")  # optional: g, ml, piece
    stock = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Current stock quantity")
    reorder_level = models.DecimalField(max_digits=10, decimal_places=2, default=10, help_text="Reorder level threshold")

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
        ('Preparing', 'Preparing'),
        ('Ready', 'Ready'),
        ('Served', 'Served'),
        ('Paid', 'Paid'),
        ('Canceled', 'Canceled'),
    ]
    
    table = models.ForeignKey(
        Table,
        on_delete=models.CASCADE,
        related_name='offline_orders',
        help_text="Table number for this order"
    )
    total = models.DecimalField(max_digits=15, decimal_places=2)
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
        return f"Offline Order #{self.id} - Table {self.table.number}"


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
        return f"{self.item.name}{size_info} x {self.quantity} (Table {self.offline_order.table.number})"


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
