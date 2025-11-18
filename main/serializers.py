from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import (
    CustomUser, Profile, Order, MenuItem, MenuItemSize, OrderItem, 
    Ingredient, MenuItemIngredient, MenuItemSizeIngredient, IngredientStock, IngredientTrace,
    Table, OfflineOrder, OfflineOrderItem, TableSession, Notification
)
from rest_framework import serializers

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # You can add extra data inside the token (optional)
        token['role'] = getattr(user, 'role', None)
        token['username'] = user.username
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        # Customize the response here
        data = {
            'username': self.user.username,
            'roles': getattr(self.user, 'roles', None),
            'access': data['access'],
            'refresh': data['refresh'],
        }
        return data
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ["id", "username","roles"]
class ProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    roles = serializers.CharField(source="user.roles", read_only=True)
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Profile
        fields = ["id", "username", "roles", "image", "phone", "address", "password"]

    def create(self, validated_data):
        user_data = validated_data.pop('user', None)
        password = validated_data.pop('password', None)
        profile = Profile.objects.create(**validated_data)

        if user_data and password:
            user = self.context['request'].user
            user.set_password(password)
            user.save()

        return profile
    
    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        
        # Update profile fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update password if provided
        if password:
            user = instance.user
            user.set_password(password)
            user.save()
        
        return instance

class UserWithProfileSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating a user with profile"""
    username = serializers.CharField(required=False)
    password = serializers.CharField(write_only=True, required=False)
    roles = serializers.ChoiceField(choices=['admin', 'cashier', 'chef'], required=False)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    address = serializers.CharField(max_length=200, required=False, allow_blank=True)
    image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = CustomUser
        fields = ["id", "username", "password", "roles", "phone", "address", "image"]

    def create(self, validated_data):
        # Extract profile data
        phone = validated_data.pop('phone', '')
        address = validated_data.pop('address', '')
        image = validated_data.pop('image', None)
        password = validated_data.pop('password', None)
        roles = validated_data.pop('roles', None)
        username = validated_data.pop('username', None)
        
        if not username or not password or not roles:
            raise serializers.ValidationError("username, password, and roles are required for creating a user")
        
        # Create user using create_user which handles password hashing
        user = CustomUser.objects.create_user(
            username=username,
            roles=roles,
            password=password
        )
        
        # Create profile for the user
        Profile.objects.create(
            user=user,
            phone=phone,
            address=address,
            image=image
        )
        
        return user
    
    def update(self, instance, validated_data):
        """Update user and profile"""
        # Extract profile data
        phone = validated_data.pop('phone', None)
        address = validated_data.pop('address', None)
        image = validated_data.pop('image', None)
        password = validated_data.pop('password', None)
        
        # Update user fields
        if 'username' in validated_data:
            instance.username = validated_data.pop('username')
        if 'roles' in validated_data:
            instance.roles = validated_data.pop('roles')
        if password:
            instance.set_password(password)
        instance.save()
        
        # Update or create profile
        profile, created = Profile.objects.get_or_create(user=instance)
        if phone is not None:
            profile.phone = phone
        if address is not None:
            profile.address = address
        if image is not None:
            profile.image = image
        profile.save()
        
        return instance
    
    def to_representation(self, instance):
        """Return representation with profile data"""
        representation = super().to_representation(instance)
        try:
            profile = instance.profile
            representation['phone'] = profile.phone
            representation['address'] = profile.address
            if profile.image:
                request = self.context.get('request')
                if request:
                    representation['image'] = request.build_absolute_uri(profile.image.url)
                else:
                    representation['image'] = profile.image.url
            else:
                representation['image'] = None
        except Profile.DoesNotExist:
            representation['phone'] = None
            representation['address'] = None
            representation['image'] = None
        return representation

class OrderSerializer(serializers.ModelSerializer):
    """Serializer for Order model"""
    date = serializers.SerializerMethodField()
    time = serializers.SerializerMethodField()
    orderType = serializers.CharField(source='order_type', required=False)
    tableNumber = serializers.CharField(source='table_number', required=False, allow_blank=True)
    formatted_id = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id', 'formatted_id', 'customer', 'phone', 'address', 'items', 
            'total', 'status', 'orderType', 'order_type',
            'tableNumber', 'table_number', 'date', 'time',
            'is_confirmed_cashier', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'formatted_id', 'created_at', 'updated_at']
        extra_kwargs = {
            'order_type': {'write_only': True},
            'table_number': {'write_only': True}
        }
    
    def get_formatted_id(self, obj):
        """Return formatted ID with # prefix"""
        return f"#{obj.id}"
    
    def get_date(self, obj):
        """Return date in YYYY-MM-DD format"""
        return obj.created_at.strftime('%Y-%m-%d')
    
    def get_time(self, obj):
        """Return time in HH:MM format"""
        return obj.created_at.strftime('%H:%M')
    
    def validate_total(self, value):
        """Validate that total is positive"""
        if value <= 0:
            raise serializers.ValidationError("Total must be greater than zero")
        return value
    
    def validate_items(self, value):
        """Validate that items list is not empty"""
        if not value or len(value) == 0:
            raise serializers.ValidationError("Order must have at least one item")
        return value
    
    def validate(self, data):
        """Validate order based on order type"""
        order_type = data.get('order_type', 'delivery')
        address = data.get('address', '')
        table_number = data.get('table_number', '')
        
        if order_type == 'delivery' and not address:
            raise serializers.ValidationError({"address": "Address is required for delivery orders"})
        
        if order_type == 'dine_in' and not table_number:
            raise serializers.ValidationError({"table_number": "Table number is required for dine-in orders"})
        
        return data
    
    def to_representation(self, instance):
        """Custom representation to format fields"""
        representation = super().to_representation(instance)
        
        # Replace numeric ID with formatted ID for backward compatibility
        if 'formatted_id' in representation:
            representation['id'] = representation.pop('formatted_id')
        
        # Add formatted fields
        representation['orderType'] = instance.order_type
        representation['tableNumber'] = instance.table_number or ''
        
        # Remove snake_case versions
        representation.pop('order_type', None)
        representation.pop('table_number', None)
        
        return representation
    
    def to_internal_value(self, data):
        """Convert camelCase to snake_case for database"""
        if 'orderType' in data:
            data['order_type'] = data.pop('orderType')
        if 'tableNumber' in data:
            data['table_number'] = data.pop('tableNumber')
        return super().to_internal_value(data)
class MenuItemSizeSerializer(serializers.ModelSerializer):
    menu_item_name = serializers.CharField(source='menu_item.name', read_only=True)
    menu_item_id = serializers.PrimaryKeyRelatedField(
        queryset=MenuItem.objects.all(), source='menu_item', write_only=True
    )
    
    class Meta:
        model = MenuItemSize
        fields = ['id', 'menu_item', 'menu_item_id', 'menu_item_name', 'size', 'price']
        read_only_fields = ['menu_item']
class MenuItemSerializer(serializers.ModelSerializer):
    sizes = MenuItemSizeSerializer(many=True, read_only=True)
    
    class Meta:
        model = MenuItem
        fields = ['id', 'name', 'description', 'price', 'category', 'image', 'featured', 'sizes']
    
    def to_representation(self, instance):
        """Convert image to absolute URL"""
        representation = super().to_representation(instance)
        
        # Convert image field to absolute URL if it exists
        if instance.image:
            request = self.context.get('request')
            if request:
                representation['image'] = request.build_absolute_uri(instance.image.url)
            else:
                # Fallback if no request context (shouldn't happen in API views)
                representation['image'] = instance.image.url
        else:
            representation['image'] = None
        
        return representation
class OrderItemSerializer(serializers.ModelSerializer):
    item = MenuItemSerializer(read_only=True)
    size = MenuItemSizeSerializer(read_only=True)

    item_id = serializers.PrimaryKeyRelatedField(
        queryset=MenuItem.objects.all(), source='item', write_only=True
    )
    size_id = serializers.PrimaryKeyRelatedField(
        queryset=MenuItemSize.objects.all(), source='size', write_only=True, allow_null=True
    )
    order_id = serializers.PrimaryKeyRelatedField(
        queryset=Order.objects.all(), source='order', write_only=True
    )

    class Meta:
        model = OrderItem
        fields = ['id', 'item', 'size', 'quantity', 'item_id', 'size_id', 'order_id', 'order']
        read_only_fields = ['id', 'order']
        extra_kwargs = {
            'order': {'read_only': True}
        }
    
    def to_representation(self, instance):
        """Custom representation to format order ID"""
        representation = super().to_representation(instance)
        if instance.order:
            representation['order'] = f"#{instance.order.id}"
        return representation

class IngredientSerializer(serializers.ModelSerializer):
    is_low_stock = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Ingredient
        fields = ['id', 'name', 'unit', 'stock', 'reorder_level', 'is_low_stock']

class MenuItemIngredientSerializer(serializers.ModelSerializer):
    """Serializer for ingredients linked directly to menu items (no sizes)"""
    ingredient = IngredientSerializer(read_only=True)
    menu_item = MenuItemSerializer(read_only=True)
    
    ingredient_id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(), source='ingredient', write_only=True
    )
    menu_item_id = serializers.PrimaryKeyRelatedField(
        queryset=MenuItem.objects.all(), source='menu_item', write_only=True
    )

    class Meta:
        model = MenuItemIngredient
        fields = ['id', 'menu_item', 'ingredient', 'quantity', 'ingredient_id', 'menu_item_id']


class MenuItemSizeIngredientSerializer(serializers.ModelSerializer):
    ingredient = IngredientSerializer(read_only=True)
    size = MenuItemSizeSerializer(read_only=True)
    
    ingredient_id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(), source='ingredient', write_only=True
    )
    size_id = serializers.PrimaryKeyRelatedField(
        queryset=MenuItemSize.objects.all(), source='size', write_only=True
    )

    class Meta:
        model = MenuItemSizeIngredient
        fields = ['id', 'size', 'ingredient', 'quantity', 'ingredient_id', 'size_id']


class IngredientStockSerializer(serializers.ModelSerializer):
    ingredient = IngredientSerializer(read_only=True)
    ingredient_id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(), source='ingredient', write_only=True
    )
    ingredient_name = serializers.CharField(source='ingredient.name', read_only=True)
    ingredient_unit = serializers.CharField(source='ingredient.unit', read_only=True)
    
    class Meta:
        model = IngredientStock
        fields = [
            'id', 'ingredient', 'ingredient_id', 'ingredient_name', 'ingredient_unit',
            'quantity', 'last_updated'
        ]
        read_only_fields = ['last_updated']


class IngredientTraceSerializer(serializers.ModelSerializer):
    ingredient = IngredientSerializer(read_only=True)
    ingredient_id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(), source='ingredient', write_only=True
    )
    ingredient_name = serializers.CharField(source='ingredient.name', read_only=True)
    ingredient_unit = serializers.CharField(source='ingredient.unit', read_only=True)
    order_id = serializers.IntegerField(source='order.id', read_only=True, allow_null=True)
    offline_order_id = serializers.IntegerField(source='offline_order.id', read_only=True, allow_null=True)
    order_display = serializers.SerializerMethodField()
    used_by_username = serializers.CharField(source='used_by.username', read_only=True, allow_null=True)
    
    class Meta:
        model = IngredientTrace
        fields = [
            'id', 'ingredient', 'ingredient_id', 'ingredient_name', 'ingredient_unit',
            'order', 'order_id', 'offline_order', 'offline_order_id', 'order_display', 'quantity_used', 'timestamp',
            'used_by', 'used_by_username', 'stock_before', 'stock_after'
        ]
        read_only_fields = ['id', 'timestamp', 'stock_before', 'stock_after']
    
    def get_order_display(self, obj):
        """Return formatted order display"""
        if obj.order:
            return f"Order #{obj.order.id}"
        elif obj.offline_order:
            return f"Offline Order #{obj.offline_order.id} (Table {obj.offline_order.table.number})"
        return None


class TableSerializer(serializers.ModelSerializer):
    class Meta:
        model = Table
        fields = ['id', 'number', 'capacity', 'is_available', 'location', 'notes', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class OfflineOrderItemSerializer(serializers.ModelSerializer):
    item = MenuItemSerializer(read_only=True)
    size = MenuItemSizeSerializer(read_only=True)
    
    item_id = serializers.PrimaryKeyRelatedField(
        queryset=MenuItem.objects.all(), source='item', write_only=True
    )
    size_id = serializers.PrimaryKeyRelatedField(
        queryset=MenuItemSize.objects.all(), source='size', write_only=True, allow_null=True
    )
    
    class Meta:
        model = OfflineOrderItem
        fields = ['id', 'item', 'size', 'quantity', 'price', 'notes', 'item_id', 'size_id']
        read_only_fields = ['id']


class OfflineOrderSerializer(serializers.ModelSerializer):
    table = TableSerializer(read_only=True)
    table_id = serializers.PrimaryKeyRelatedField(
        queryset=Table.objects.all(), source='table', write_only=True
    )
    items = OfflineOrderItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = OfflineOrder
        fields = ['id', 'table', 'table_id', 'total', 'status', 'is_confirmed_cashier', 'notes', 'items', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class TableSessionSerializer(serializers.ModelSerializer):
    table = TableSerializer(read_only=True)
    table_id = serializers.PrimaryKeyRelatedField(
        queryset=Table.objects.all(), source='table', write_only=True
    )
    is_valid = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()
    
    class Meta:
        model = TableSession
        fields = [
            'id', 'table', 'table_id', 'token', 'is_active', 'expires_at',
            'last_accessed', 'ip_address', 'user_agent', 'created_at',
            'order_placed', 'is_valid', 'is_expired'
        ]
        read_only_fields = ['id', 'token', 'created_at', 'last_accessed', 'is_valid', 'is_expired']
    
    def get_is_valid(self, obj):
        return obj.is_valid()
    
    def get_is_expired(self, obj):
        return obj.is_expired()


class NotificationSerializer(serializers.ModelSerializer):
    time_ago = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = [
            'id', 'notification_type', 'title', 'message', 'is_read',
            'related_order', 'related_offline_order', 'related_ingredient',
            'created_at', 'time_ago'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_time_ago(self, obj):
        """Calculate time ago string"""
        from django.utils import timezone
        delta = timezone.now() - obj.created_at
        
        if delta.days > 0:
            return f"{delta.days} day{'s' if delta.days > 1 else ''} ago"
        elif delta.seconds >= 3600:
            hours = delta.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif delta.seconds >= 60:
            minutes = delta.seconds // 60
            return f"{minutes} min ago"
        else:
            return "Just now"