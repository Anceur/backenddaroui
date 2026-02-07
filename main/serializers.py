from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from decimal import Decimal
from .models import (
    CustomUser, Profile, Order, MenuItem, MenuItemSize, OrderItem, 
    Ingredient, MenuItemIngredient, MenuItemSizeIngredient, IngredientStock, IngredientTrace,
    Table, OfflineOrder, OfflineOrderItem, TableSession, Notification,
    Supplier, SupplierHistory, SupplierTransactionItem, ClientFidele, Expense, StaffMember, Promotion, PromotionItem,
    RestaurantInfo
)
from rest_framework import serializers

class StaffMemberSerializer(serializers.ModelSerializer):
    username = serializers.CharField(required=False, allow_null=True, write_only=True)
    password = serializers.CharField(required=False, allow_null=True, write_only=True)
    has_account = serializers.BooleanField(required=False, default=False, write_only=True)

    class Meta:
        model = StaffMember
        fields = ["id", "user", "name", "role", "phone", "address", "image", "username", "password", "has_account", "is_active"]
        read_only_fields = ["user"]

    def create(self, validated_data):
        has_account = validated_data.pop('has_account', False)
        username = validated_data.pop('username', None)
        password = validated_data.pop('password', None)
        
        user = None
        if has_account and username and password:
            if CustomUser.objects.filter(username=username).exists():
                raise serializers.ValidationError({"username": "Username already exists"})
            
            # Roles for users are restricted in frontend, but here we just take the role
            user = CustomUser.objects.create(
                username=username,
                roles=validated_data.get('role', 'cashier')
            )
            user.set_password(password)
            user.save()
            
        staff = StaffMember.objects.create(user=user, **validated_data)
        return staff

    def update(self, instance, validated_data):
        has_account = validated_data.pop('has_account', None)
        username = validated_data.pop('username', None)
        password = validated_data.pop('password', None)

        # If password is provided, update user password
        if instance.user and password:
            instance.user.set_password(password)
            instance.user.save()

        # If user roles changed, sync it
        if 'role' in validated_data and instance.user:
            instance.user.roles = validated_data['role']
            instance.user.save()

        return super().update(instance, validated_data)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if instance.image:
            image_url = instance.image
            if image_url.startswith('http://') or image_url.startswith('https://'):
                representation['image'] = image_url
            else:
                request = self.context.get('request')
                if request:
                    representation['image'] = request.build_absolute_uri(image_url)
                else:
                    representation['image'] = image_url
        else:
            representation['image'] = None
        return representation

class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = '__all__'

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

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if instance.image:
            image_url = instance.image
            if image_url.startswith('http://') or image_url.startswith('https://'):
                representation['image'] = image_url
            else:
                request = self.context.get('request')
                if request:
                    representation['image'] = request.build_absolute_uri(image_url)
                else:
                    representation['image'] = image_url
        else:
            representation['image'] = None
        return representation

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
                image_url = profile.image
                if image_url.startswith('http://') or image_url.startswith('https://'):
                    representation['image'] = image_url
                else:
                    request = self.context.get('request')
                    if request:
                        representation['image'] = request.build_absolute_uri(image_url)
                    else:
                        representation['image'] = image_url
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
            'subtotal', 'tax_amount', 'total', 'revenue', 'status', 'orderType', 'order_type',
            'tableNumber', 'table_number', 'date', 'time',
            'is_confirmed_cashier', 'loyalty_number', 'loyal_customer', 'notes',
            'created_at', 'updated_at'
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
        
        # Add formatted fields
        representation['orderType'] = instance.order_type
        representation['tableNumber'] = instance.table_number or ''
        
        # Add loyal_customer as nested object if it exists
        if instance.loyal_customer:
            representation['loyalCustomer'] = {
                'id': instance.loyal_customer.id,
                'name': instance.loyal_customer.name,
                'phone': instance.loyal_customer.phone,
                'loyaltyCardNumber': instance.loyal_customer.loyalty_card_number,
                'totalSpent': str(instance.loyal_customer.total_spent),
            }
        else:
            representation['loyalCustomer'] = None
        
        # Remove snake_case versions
        representation.pop('order_type', None)
        representation.pop('table_number', None)
        representation.pop('loyal_customer', None)  # Remove the ID, we have the nested object
        
        return representation
    
    def to_internal_value(self, data):
        """Convert camelCase to snake_case for database"""
        if 'orderType' in data:
            data['order_type'] = data.pop('orderType')
        if 'tableNumber' in data:
            data['table_number'] = data.pop('tableNumber')
        return super().to_internal_value(data)
    
    def create(self, validated_data):
        """Create order and link to ClientFidele if loyalty_number matches"""
        loyalty_number = validated_data.get('loyalty_number')
        
        # If loyalty_number is provided and not empty, try to find matching ClientFidele
        if loyalty_number and str(loyalty_number).strip():
            from .models import ClientFidele
            try:
                # Try to find ClientFidele by loyalty_card_number
                loyal_customer = ClientFidele.objects.filter(
                    loyalty_card_number=loyalty_number.strip()
                ).first()
                
                if loyal_customer:
                    validated_data['loyal_customer'] = loyal_customer
            except Exception:
                # If lookup fails, continue without linking
                pass
        
        return super().create(validated_data)
class MenuItemSizeSerializer(serializers.ModelSerializer):
    menu_item_name = serializers.CharField(source='menu_item.name', read_only=True)
    menu_item_id = serializers.PrimaryKeyRelatedField(
        queryset=MenuItem.objects.all(), source='menu_item', write_only=True
    )
    cost_price = serializers.DecimalField(max_digits=6, decimal_places=2, required=False, allow_null=True)
    
    class Meta:
        model = MenuItemSize
        fields = ['id', 'menu_item', 'menu_item_id', 'menu_item_name', 'size', 'price', 'cost_price']
        read_only_fields = ['menu_item']
    
    def validate_cost_price(self, value):
        """Ensure cost_price is not negative and defaults to 0.00"""
        if value is None:
            return 0.00
        if value < 0:
            raise serializers.ValidationError("Cost price cannot be negative.")
        return value
    
    def create(self, validated_data):
        """Create menu item size ensuring cost_price has a value"""
        if 'cost_price' not in validated_data or validated_data.get('cost_price') is None:
            validated_data['cost_price'] = 0.00
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        """Update menu item size ensuring cost_price has a value"""
        if 'cost_price' in validated_data and validated_data.get('cost_price') is None:
            validated_data['cost_price'] = 0.00
        return super().update(instance, validated_data)
# MenuItemSerializer
    class MenuItemSerializer(serializers.ModelSerializer):
    image = serializers.CharField(required=False, allow_blank=True, allow_null=True)  # ✅ سطر واحد فقط
    sizes = MenuItemSizeSerializer(many=True, read_only=True)
    cost_price = serializers.DecimalField(max_digits=6, decimal_places=2, required=False, allow_null=True)
    
    class Meta:
        model = MenuItem
        fields = '__all__'
    
    def validate_image(self, value):
        if isinstance(value, str):
            if value and not value.startswith('http'):
                raise serializers.ValidationError("رابط صورة غير صالح")
            return value
        return value


# StaffSerializer - خارج MenuItemSerializer تماماً! ⚠️
    class StaffSerializer(serializers.ModelSerializer):
        image = serializers.CharField(required=False, allow_blank=True, allow_null=True)
        username = serializers.CharField(source='user.username', read_only=True, required=False)
    
    class Meta:
        model = Staff
        fields = '__all__'
    
    def validate_image(self, value):
        if isinstance(value, str):
            if value and not value.startswith('http'):
                raise serializers.ValidationError("رابط صورة غير صالح")
            return value
        return value    
    class Meta:
        model = MenuItem
        fields = ['id', 'name', 'description', 'price', 'cost_price', 'category', 'image', 'featured', 'sizes']
    
    def validate_cost_price(self, value):
        """Ensure cost_price is not negative and defaults to 0.00"""
        if value is None:
            return 0.00
        if value < 0:
            raise serializers.ValidationError("Cost price cannot be negative.")
        return value
    
    def create(self, validated_data):
        """Create menu item ensuring cost_price has a value"""
        if 'cost_price' not in validated_data or validated_data.get('cost_price') is None:
            validated_data['cost_price'] = 0.00
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        """Update menu item ensuring cost_price has a value"""
        if 'cost_price' in validated_data and validated_data.get('cost_price') is None:
            validated_data['cost_price'] = 0.00
        return super().update(instance, validated_data)
    
    def to_representation(self, instance):
        """Convert image to absolute URL"""
        representation = super().to_representation(instance)
        
        # Convert image field to absolute URL if it exists
        if instance.image:
            image_url = instance.image
            
            # If it's already an absolute URL (like Firebase), just return it
            if image_url.startswith('http://') or image_url.startswith('https://'):
                representation['image'] = image_url
            else:
                # Handle relative paths (legacy or local development)
                request = self.context.get('request')
                if request:
                    # Get the scheme and host from request
                    scheme = request.scheme  # http or https
                    host = request.get_host()  # localhost:8000 or domain.com
                    representation['image'] = f"{scheme}://{host}{image_url}"
                else:
                    # Fallback: use localhost:8000 for development
                    representation['image'] = f"http://localhost:8000{image_url}"
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

class SupplierSerializer(serializers.ModelSerializer):
    """Serializer for Supplier model"""
    
    class Meta:
        model = Supplier
        fields = ['id', 'name', 'phone', 'supplier_type', 'debt', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class SupplierTransactionItemSerializer(serializers.ModelSerializer):
    ingredient_name = serializers.CharField(source='ingredient.name', read_only=True)
    ingredient_unit = serializers.CharField(source='ingredient.unit', read_only=True)
    
    class Meta:
        model = SupplierTransactionItem
        fields = ['id', 'ingredient', 'ingredient_name', 'ingredient_unit', 'quantity', 'price_per_unit', 'total_price']

class SupplierHistorySerializer(serializers.ModelSerializer):
    """Serializer for SupplierHistory model"""
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    items = SupplierTransactionItemSerializer(many=True, read_only=True)
    items_data = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = SupplierHistory
        fields = [
            'id', 'supplier', 'supplier_name', 'transaction_type', 'transaction_type_display',
            'amount', 'description', 'created_by', 'created_by_username', 'created_at', 'items', 'items_data'
        ]
        read_only_fields = ['created_at']

    def create(self, validated_data):
        items_data = validated_data.pop('items_data', None)
        history = super().create(validated_data)
        
        if items_data and history.transaction_type == 'purchase':
            total_amount = Decimal('0')
            for item_data in items_data:
                ingredient_id = item_data.get('ingredient_id')
                name = item_data.get('name')
                quantity = item_data.get('quantity')
                price_per_unit = item_data.get('price_per_unit')
                
                if quantity is None or price_per_unit is None:
                    continue
                    
                # Convert to Decimal for proper calculation
                quantity_decimal = Decimal(str(quantity))
                price_per_unit_decimal = Decimal(str(price_per_unit))
                
                # Fetch or Create Ingredient
                ingredient = None
                if ingredient_id:
                    try:
                        ingredient = Ingredient.objects.get(id=ingredient_id)
                    except Ingredient.DoesNotExist:
                        pass
                
                if not ingredient and name:
                    # Create new ingredient
                    # Use unit from data or default? Assuming 'kg' or passed in data
                    unit = item_data.get('unit', 'kg')
                    ingredient = Ingredient.objects.create(
                        name=name,
                        unit=unit,
                        price=price_per_unit_decimal,
                        stock=Decimal('0'), # Will add quantity
                    )
                
                if ingredient:
                    # Add supplier to ingredient's suppliers (many-to-many) if not already added
                    if history.supplier and history.supplier not in ingredient.suppliers.all():
                        ingredient.suppliers.add(history.supplier)
                    # Create Item
                    SupplierTransactionItem.objects.create(
                        supplier_history=history,
                        ingredient=ingredient,
                        quantity=quantity_decimal,
                        price_per_unit=price_per_unit_decimal,
                        total_price=quantity_decimal * price_per_unit_decimal
                    )
                    
                    # Update Ingredient Stock and Price
                    # Assuming purchase adds to stock
                    ingredient.stock = ingredient.stock + quantity_decimal
                    ingredient.price = price_per_unit_decimal # Update latest price
                    ingredient.save()
                    
                    # Sync IngredientStock record
                    IngredientStock.objects.update_or_create(
                        ingredient=ingredient,
                        defaults={'quantity': ingredient.stock}
                    )
                    
                    total_amount += (quantity_decimal * price_per_unit_decimal)
            
            # Update history amount if items were processed (optional, depends on requirement)
            # Validating that calculated total roughly matches input or overriding it?
            # User requirement: "amount price will be calulated automaticlly"
            # It's safer to trust the items calculation
            history.amount = total_amount
            history.save()
        
        return history


class IngredientSerializer(serializers.ModelSerializer):
    is_low_stock = serializers.SerializerMethodField()
    suppliers = serializers.SerializerMethodField()
    supplier_names = serializers.SerializerMethodField()
    suppliers_list = serializers.SerializerMethodField()  # Alias for frontend compatibility
    supplier_ids = serializers.SerializerMethodField()  # Alias for frontend compatibility
    
    class Meta:
        model = Ingredient
        fields = ['id', 'name', 'unit', 'stock', 'price', 'reorder_level', 'is_low_stock', 'suppliers', 'supplier_names', 'suppliers_list', 'supplier_ids']
    
    def get_is_low_stock(self, obj):
        """Check if stock is below reorder level"""
        return obj.is_low_stock
    
    def get_suppliers(self, obj):
        """Return list of supplier IDs"""
        return [supplier.id for supplier in obj.suppliers.all()]
    
    def get_supplier_ids(self, obj):
        """Return list of supplier IDs (alias for frontend)"""
        return [supplier.id for supplier in obj.suppliers.all()]
    
    def get_supplier_names(self, obj):
        """Return list of supplier names"""
        return [supplier.name for supplier in obj.suppliers.all()]
    
    def get_suppliers_list(self, obj):
        """Return list of supplier names (alias for frontend compatibility)"""
        return [supplier.name for supplier in obj.suppliers.all()]
    
    def create(self, validated_data):
        """Create ingredient and handle suppliers"""
        suppliers_data = self.initial_data.get('suppliers', [])
        ingredient = Ingredient.objects.create(**validated_data)
        
        if suppliers_data:
            supplier_ids = [s for s in suppliers_data if isinstance(s, int)]
            ingredient.suppliers.set(supplier_ids)
        
        return ingredient
    
    def update(self, instance, validated_data):
        """Update ingredient and handle suppliers"""
        suppliers_data = self.initial_data.get('suppliers', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        if suppliers_data is not None:
            supplier_ids = [s for s in suppliers_data if isinstance(s, int)]
            instance.suppliers.set(supplier_ids)
        
        return instance

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
        queryset=Ingredient.objects.all(), source='ingredient', write_only=True, required=False
    )
    ingredient_name = serializers.CharField(source='ingredient.name', read_only=True)
    ingredient_unit = serializers.CharField(source='ingredient.unit', read_only=True)
    reorder_level = serializers.DecimalField(source='ingredient.reorder_level', max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = IngredientStock
        fields = [
            'id', 'ingredient', 'ingredient_id', 'ingredient_name', 'ingredient_unit',
            'quantity', 'last_updated', 'reorder_level'
        ]
        read_only_fields = ['last_updated', 'quantity']


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
            table_info = f" (Table {obj.offline_order.table.number})" if obj.offline_order.table else ""
            return f"Offline Order #{obj.offline_order.id}{table_info}"
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
        queryset=Table.objects.all(), source='table', write_only=True, required=False, allow_null=True
    )
    items = OfflineOrderItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = OfflineOrder
        fields = ['id', 'table', 'table_id', 'total', 'revenue', 'status', 'is_confirmed_cashier', 'notes', 'items', 'is_imported', 'created_at', 'updated_at']
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


class ClientFideleSerializer(serializers.ModelSerializer):
    """Serializer for loyal customers"""
    class Meta:
        model = ClientFidele
        fields = [
            'id', 'name', 'phone', 'loyalty_card_number', 
            'total_spent', 'created_at', 'updated_at'
        ]
        read_only_fields = ['loyalty_card_number', 'total_spent', 'created_at', 'updated_at']


class NotificationSerializer(serializers.ModelSerializer):
    time_ago = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = [
            'id', 'notification_type', 'priority', 'title', 'message', 'is_read',
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

class PromotionItemSerializer(serializers.ModelSerializer):
    menu_item_name = serializers.CharField(source='menu_item.name', read_only=True)
    size_label = serializers.CharField(source='menu_item_size.size', read_only=True)
    
    class Meta:
        model = PromotionItem
        fields = ['id', 'promotion', 'menu_item', 'menu_item_name', 'menu_item_size', 'size_label', 'quantity']

class RestaurantInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = RestaurantInfo
        fields = ['id', 'opening_time', 'closing_time']
    


class PromotionSerializer(serializers.ModelSerializer):
    combo_items = PromotionItemSerializer(many=True, required=False)
    display_status = serializers.CharField(read_only=True)
    
    class Meta:
        model = Promotion
        fields = ['id', 'name', 'description', 'promotion_type', 'value', 'start_date', 'end_date', 'is_active', 'status', 'display_status', 'applicable_items', 'applicable_sizes', 'combo_items', 'created_at']

    def create(self, validated_data):
        combo_items_data = validated_data.pop('combo_items', [])
        applicable_items = validated_data.pop('applicable_items', [])
        applicable_sizes = validated_data.pop('applicable_sizes', [])
        
        promotion = Promotion.objects.create(**validated_data)
        promotion.applicable_items.set(applicable_items)
        promotion.applicable_sizes.set(applicable_sizes)
        
        for item_data in combo_items_data:
            PromotionItem.objects.create(promotion=promotion, **item_data)
            
        return promotion

    def update(self, instance, validated_data):
        combo_items_data = validated_data.pop('combo_items', None)
        applicable_items = validated_data.pop('applicable_items', None)
        applicable_sizes = validated_data.pop('applicable_sizes', None)
        
        # Update basics
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update ManyToMany
        if applicable_items is not None:
            instance.applicable_items.set(applicable_items)
        if applicable_sizes is not None:
            instance.applicable_sizes.set(applicable_sizes)
            
        # Update Nested Combo Items
        if combo_items_data is not None:
            instance.combo_items.all().delete()
            for item_data in combo_items_data:
                PromotionItem.objects.create(promotion=instance, **item_data)
                
        return instance

