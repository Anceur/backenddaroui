"""
Django management command to seed the database with sample data.
Usage: python manage.py seed_db
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from main.models import MenuItem, MenuItemSize, Order, CustomUser, Profile


class Command(BaseCommand):
    help = 'Seeds the database with sample menu items, orders, and users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before seeding',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write(self.style.WARNING('Clearing existing data...'))
            Order.objects.all().delete()
            MenuItemSize.objects.all().delete()
            MenuItem.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Existing data cleared.'))

        self.stdout.write(self.style.SUCCESS('Starting database seeding...'))

        # Create menu items
        menu_items = self.create_menu_items()
        
        # Create menu item sizes
        self.create_menu_item_sizes(menu_items)
        
        # Create sample orders
        self.create_sample_orders(menu_items)
        
        # Create admin user if doesn't exist
        self.create_admin_user()

        self.stdout.write(self.style.SUCCESS('Database seeding completed successfully!'))

    def create_menu_items(self):
        """Create sample menu items"""
        self.stdout.write('Creating menu items...')
        
        menu_data = [
            # Burgers
            {
                'name': 'Classic Burger',
                'description': 'Juicy beef patty with fresh lettuce, tomato, and special sauce',
                'price': Decimal('12.50'),
                'category': 'burger',
                'featured': True,
            },
            {
                'name': 'Cheese Burger',
                'description': 'Classic burger with melted cheese',
                'price': Decimal('13.50'),
                'category': 'burger',
                'featured': True,
            },
            {
                'name': 'Double Burger',
                'description': 'Two beef patties with double cheese',
                'price': Decimal('18.00'),
                'category': 'burger',
                'featured': False,
            },
            {
                'name': 'Chicken Burger',
                'description': 'Crispy chicken fillet with mayo and lettuce',
                'price': Decimal('14.00'),
                'category': 'burger',
                'featured': False,
            },
            
            # Pizza
            {
                'name': 'Margherita Pizza',
                'description': 'Classic pizza with tomato sauce, mozzarella, and basil',
                'price': Decimal('15.00'),
                'category': 'pizza',
                'featured': True,
            },
            {
                'name': 'Pepperoni Pizza',
                'description': 'Pizza with pepperoni and mozzarella cheese',
                'price': Decimal('18.50'),
                'category': 'pizza',
                'featured': True,
            },
            {
                'name': 'Hawaiian Pizza',
                'description': 'Pizza with ham, pineapple, and cheese',
                'price': Decimal('19.00'),
                'category': 'pizza',
                'featured': False,
            },
            {
                'name': 'Vegetarian Pizza',
                'description': 'Pizza with mixed vegetables and cheese',
                'price': Decimal('17.00'),
                'category': 'pizza',
                'featured': False,
            },
            
            # Sandwiches
            {
                'name': 'Club Sandwich',
                'description': 'Triple-decker sandwich with chicken, bacon, and vegetables',
                'price': Decimal('11.00'),
                'category': 'sandwich',
                'featured': True,
            },
            {
                'name': 'Grilled Chicken Sandwich',
                'description': 'Grilled chicken breast with lettuce and mayo',
                'price': Decimal('10.50'),
                'category': 'sandwich',
                'featured': False,
            },
            {
                'name': 'Tuna Sandwich',
                'description': 'Fresh tuna with vegetables and special sauce',
                'price': Decimal('9.50'),
                'category': 'sandwich',
                'featured': False,
            },
            
            # Plats
            {
                'name': 'Grilled Chicken Plate',
                'description': 'Grilled chicken with rice and vegetables',
                'price': Decimal('16.00'),
                'category': 'plat',
                'featured': True,
            },
            {
                'name': 'Beef Steak Plate',
                'description': 'Tender beef steak with fries and salad',
                'price': Decimal('22.00'),
                'category': 'plat',
                'featured': True,
            },
            {
                'name': 'Fish Plate',
                'description': 'Grilled fish with rice and vegetables',
                'price': Decimal('18.50'),
                'category': 'plat',
                'featured': False,
            },
            
            # Tacos
            {
                'name': 'Beef Tacos',
                'description': 'Three soft tacos with seasoned beef and vegetables',
                'price': Decimal('13.00'),
                'category': 'tacos',
                'featured': True,
            },
            {
                'name': 'Chicken Tacos',
                'description': 'Three soft tacos with grilled chicken',
                'price': Decimal('12.50'),
                'category': 'tacos',
                'featured': False,
            },
            {
                'name': 'Vegetarian Tacos',
                'description': 'Three tacos with mixed vegetables',
                'price': Decimal('11.00'),
                'category': 'tacos',
                'featured': False,
            },
            
            # Desserts
            {
                'name': 'Chocolate Cake',
                'description': 'Rich chocolate cake with cream',
                'price': Decimal('8.00'),
                'category': 'desserts',
                'featured': True,
            },
            {
                'name': 'Ice Cream Sundae',
                'description': 'Vanilla ice cream with chocolate sauce and nuts',
                'price': Decimal('7.50'),
                'category': 'desserts',
                'featured': False,
            },
            {
                'name': 'Cheesecake',
                'description': 'Creamy cheesecake with berry topping',
                'price': Decimal('9.00'),
                'category': 'desserts',
                'featured': False,
            },
            {
                'name': 'Apple Pie',
                'description': 'Homemade apple pie with cinnamon',
                'price': Decimal('7.00'),
                'category': 'desserts',
                'featured': False,
            },
            
            # Drinks
            {
                'name': 'Coca Cola',
                'description': 'Refreshing cola drink',
                'price': Decimal('3.00'),
                'category': 'drinks',
                'featured': False,
            },
            {
                'name': 'Orange Juice',
                'description': 'Fresh orange juice',
                'price': Decimal('4.00'),
                'category': 'drinks',
                'featured': False,
            },
            {
                'name': 'Coffee',
                'description': 'Hot coffee',
                'price': Decimal('3.50'),
                'category': 'drinks',
                'featured': False,
            },
            {
                'name': 'Milkshake',
                'description': 'Creamy milkshake (chocolate, vanilla, or strawberry)',
                'price': Decimal('5.00'),
                'category': 'drinks',
                'featured': True,
            },
        ]

        created_items = []
        for item_data in menu_data:
            item, created = MenuItem.objects.get_or_create(
                name=item_data['name'],
                defaults=item_data
            )
            created_items.append(item)
            if created:
                self.stdout.write(f'  Created: {item.name}')

        self.stdout.write(self.style.SUCCESS(f'Created/updated {len(created_items)} menu items'))
        return created_items

    def create_menu_item_sizes(self, menu_items):
        """Create sizes for pizza and drinks"""
        self.stdout.write('Creating menu item sizes...')
        
        size_count = 0
        for item in menu_items:
            # Add sizes for pizzas
            if item.category == 'pizza':
                sizes = [
                    {'size': 'M', 'price': item.price},
                    {'size': 'L', 'price': item.price * Decimal('1.3')},
                    {'size': 'Mega', 'price': item.price * Decimal('1.6')},
                ]
                for size_data in sizes:
                    size_obj, created = MenuItemSize.objects.get_or_create(
                        menu_item=item,
                        size=size_data['size'],
                        defaults={'price': size_data['price']}
                    )
                    if created:
                        size_count += 1
                        self.stdout.write(f'  Created size: {item.name} - {size_data["size"]}')
            
            # Add sizes for drinks (milkshake)
            elif item.category == 'drinks' and 'milkshake' in item.name.lower():
                sizes = [
                    {'size': 'M', 'price': item.price},
                    {'size': 'L', 'price': item.price * Decimal('1.2')},
                ]
                for size_data in sizes:
                    size_obj, created = MenuItemSize.objects.get_or_create(
                        menu_item=item,
                        size=size_data['size'],
                        defaults={'price': size_data['price']}
                    )
                    if created:
                        size_count += 1
                        self.stdout.write(f'  Created size: {item.name} - {size_data["size"]}')

        self.stdout.write(self.style.SUCCESS(f'Created {size_count} menu item sizes'))

    def create_sample_orders(self, menu_items):
        """Create sample orders"""
        self.stdout.write('Creating sample orders...')
        
        # Get some menu items for orders
        burger = MenuItem.objects.filter(category='burger').first()
        pizza = MenuItem.objects.filter(category='pizza').first()
        sandwich = MenuItem.objects.filter(category='sandwich').first()
        drink = MenuItem.objects.filter(category='drinks').first()
        dessert = MenuItem.objects.filter(category='desserts').first()

        orders_data = [
            {
                'customer': 'Ahmed Benali',
                'phone': '+213 555 123 456',
                'address': '12 Rue Didouche Mourad, Alger',
                'items': ['Classic Burger x1', 'Coca Cola x1', 'Chocolate Cake x1'],
                'total': Decimal('23.50'),
                'status': 'Pending',
                'order_type': 'delivery',
                'table_number': None,
                'created_at': timezone.now() - timedelta(hours=2),
            },
            {
                'customer': 'Sarah Johnson',
                'phone': '+213 555 234 567',
                'address': '45 Avenue des Frères Fares, Oran',
                'items': ['Margherita Pizza (L) x1', 'Orange Juice x2'],
                'total': Decimal('28.00'),
                'status': 'Preparing',
                'order_type': 'delivery',
                'table_number': None,
                'created_at': timezone.now() - timedelta(hours=1, minutes=30),
            },
            {
                'customer': 'Mohamed Amine',
                'phone': '+213 555 345 678',
                'address': 'Table 5',
                'items': ['Club Sandwich x2', 'Coffee x2'],
                'total': Decimal('29.00'),
                'status': 'Ready',
                'order_type': 'dine_in',
                'table_number': '5',
                'created_at': timezone.now() - timedelta(hours=1),
            },
            {
                'customer': 'Fatima Zohra',
                'phone': '+213 555 456 789',
                'address': '78 Boulevard Che Guevara, Constantine',
                'items': ['Grilled Chicken Plate x1', 'Milkshake x1'],
                'total': Decimal('21.00'),
                'status': 'Delivered',
                'order_type': 'delivery',
                'table_number': None,
                'created_at': timezone.now() - timedelta(days=1),
            },
            {
                'customer': 'Youssef Khelil',
                'phone': '+213 555 567 890',
                'address': 'Table 12',
                'items': ['Pepperoni Pizza (Mega) x1', 'Coca Cola x2'],
                'total': Decimal('29.50'),
                'status': 'Preparing',
                'order_type': 'dine_in',
                'table_number': '12',
                'created_at': timezone.now() - timedelta(minutes=45),
            },
            {
                'customer': 'Amina Bensalem',
                'phone': '+213 555 678 901',
                'address': '23 Rue Larbi Ben M\'hidi, Tlemcen',
                'items': ['Beef Tacos x1', 'Ice Cream Sundae x1'],
                'total': Decimal('20.50'),
                'status': 'Pending',
                'order_type': 'delivery',
                'table_number': None,
                'created_at': timezone.now() - timedelta(minutes=30),
            },
            {
                'customer': 'Karim Bouzid',
                'phone': '+213 555 789 012',
                'address': 'Table 8',
                'items': ['Double Burger x1', 'Milkshake x1', 'Cheesecake x1'],
                'total': Decimal('32.00'),
                'status': 'Ready',
                'order_type': 'dine_in',
                'table_number': '8',
                'created_at': timezone.now() - timedelta(minutes=20),
            },
            {
                'customer': 'Lina Merabet',
                'phone': '+213 555 890 123',
                'address': '56 Rue de la République, Annaba',
                'items': ['Vegetarian Pizza (L) x1', 'Orange Juice x1'],
                'total': Decimal('25.00'),
                'status': 'Canceled',
                'order_type': 'delivery',
                'table_number': None,
                'created_at': timezone.now() - timedelta(days=2),
            },
        ]

        created_count = 0
        for order_data in orders_data:
            # Use update_or_create to avoid duplicates
            order, created = Order.objects.get_or_create(
                customer=order_data['customer'],
                phone=order_data['phone'],
                created_at__date=order_data['created_at'].date(),
                defaults=order_data
            )
            if created:
                created_count += 1
                self.stdout.write(f'  Created order: #{order.id} - {order.customer}')

        self.stdout.write(self.style.SUCCESS(f'Created {created_count} sample orders'))

    def create_admin_user(self):
        """Create admin user if doesn't exist"""
        self.stdout.write('Checking admin user...')
        
        admin, created = CustomUser.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@restaurant.com',
                'roles': 'admin',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        
        if created:
            admin.set_password('admin123')
            admin.save()
            # Create profile
            Profile.objects.get_or_create(
                user=admin,
                defaults={
                    'phone': '+213 555 000 000',
                    'address': 'Restaurant Address',
                }
            )
            self.stdout.write(self.style.SUCCESS('Created admin user (username: admin, password: admin123)'))
        else:
            self.stdout.write(self.style.WARNING('Admin user already exists'))

