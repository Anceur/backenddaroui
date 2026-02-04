"""
Django management command to seed ingredients, ingredient stocks, and link them to menu items
Usage: python manage.py seed_ingredients
"""
from django.core.management.base import BaseCommand
from decimal import Decimal
from main.models import (
    Ingredient, IngredientStock, MenuItem, MenuItemSize,
    MenuItemIngredient, MenuItemSizeIngredient
)


class Command(BaseCommand):
    help = 'Seeds ingredients, ingredient stocks, and links them to menu items'

    # Common ingredients by category
    COMMON_INGREDIENTS = {
        'burger': {
            'Beef Patty': {'unit': 'kg', 'quantity': 0.15, 'stock': 50, 'reorder_level': 10},
            'Bun': {'unit': 'piece', 'quantity': 1, 'stock': 500, 'reorder_level': 100},
            'Lettuce': {'unit': 'kg', 'quantity': 0.02, 'stock': 30, 'reorder_level': 5},
            'Tomato': {'unit': 'kg', 'quantity': 0.03, 'stock': 40, 'reorder_level': 8},
            'Onion': {'unit': 'kg', 'quantity': 0.015, 'stock': 25, 'reorder_level': 5},
            'Cheese': {'unit': 'kg', 'quantity': 0.025, 'stock': 35, 'reorder_level': 7},
            'Pickles': {'unit': 'kg', 'quantity': 0.01, 'stock': 20, 'reorder_level': 5},
            'Mayonnaise': {'unit': 'l', 'quantity': 0.015, 'stock': 50, 'reorder_level': 10},
            'Ketchup': {'unit': 'l', 'quantity': 0.01, 'stock': 40, 'reorder_level': 8},
        },
        'pizza': {
            'Pizza Dough': {'unit': 'kg', 'quantity': 0.2, 'stock': 100, 'reorder_level': 20},
            'Tomato Sauce': {'unit': 'l', 'quantity': 0.05, 'stock': 60, 'reorder_level': 12},
            'Mozzarella Cheese': {'unit': 'kg', 'quantity': 0.1, 'stock': 80, 'reorder_level': 15},
            'Pepperoni': {'unit': 'kg', 'quantity': 0.03, 'stock': 40, 'reorder_level': 8},
            'Mushrooms': {'unit': 'kg', 'quantity': 0.04, 'stock': 30, 'reorder_level': 6},
            'Bell Peppers': {'unit': 'kg', 'quantity': 0.03, 'stock': 25, 'reorder_level': 5},
            'Olives': {'unit': 'kg', 'quantity': 0.02, 'stock': 20, 'reorder_level': 4},
            'Onion': {'unit': 'kg', 'quantity': 0.025, 'stock': 25, 'reorder_level': 5},
            'Basil': {'unit': 'kg', 'quantity': 0.005, 'stock': 5, 'reorder_level': 1},
        },
        'sandwich': {
            'Bread': {'unit': 'piece', 'quantity': 2, 'stock': 600, 'reorder_level': 120},
            'Chicken Breast': {'unit': 'kg', 'quantity': 0.15, 'stock': 60, 'reorder_level': 12},
            'Lettuce': {'unit': 'kg', 'quantity': 0.025, 'stock': 30, 'reorder_level': 5},
            'Tomato': {'unit': 'kg', 'quantity': 0.03, 'stock': 40, 'reorder_level': 8},
            'Mayonnaise': {'unit': 'l', 'quantity': 0.015, 'stock': 50, 'reorder_level': 10},
            'Cheese': {'unit': 'kg', 'quantity': 0.03, 'stock': 35, 'reorder_level': 7},
            'Bacon': {'unit': 'kg', 'quantity': 0.05, 'stock': 30, 'reorder_level': 6},
        },
        'plat': {
            'Rice': {'unit': 'kg', 'quantity': 0.2, 'stock': 150, 'reorder_level': 30},
            'Chicken': {'unit': 'kg', 'quantity': 0.2, 'stock': 80, 'reorder_level': 15},
            'Vegetables': {'unit': 'kg', 'quantity': 0.15, 'stock': 50, 'reorder_level': 10},
            'Sauce': {'unit': 'l', 'quantity': 0.05, 'stock': 40, 'reorder_level': 8},
            'Potatoes': {'unit': 'kg', 'quantity': 0.15, 'stock': 60, 'reorder_level': 12},
            'Salad Mix': {'unit': 'kg', 'quantity': 0.1, 'stock': 30, 'reorder_level': 6},
        },
        'tacos': {
            'Tortilla': {'unit': 'piece', 'quantity': 2, 'stock': 400, 'reorder_level': 80},
            'Ground Beef': {'unit': 'kg', 'quantity': 0.1, 'stock': 50, 'reorder_level': 10},
            'Lettuce': {'unit': 'kg', 'quantity': 0.03, 'stock': 30, 'reorder_level': 5},
            'Tomato': {'unit': 'kg', 'quantity': 0.04, 'stock': 40, 'reorder_level': 8},
            'Cheese': {'unit': 'kg', 'quantity': 0.03, 'stock': 35, 'reorder_level': 7},
            'Sour Cream': {'unit': 'l', 'quantity': 0.02, 'stock': 25, 'reorder_level': 5},
            'Salsa': {'unit': 'l', 'quantity': 0.015, 'stock': 20, 'reorder_level': 4},
        },
        'desserts': {
            'Flour': {'unit': 'kg', 'quantity': 0.1, 'stock': 100, 'reorder_level': 20},
            'Sugar': {'unit': 'kg', 'quantity': 0.05, 'stock': 80, 'reorder_level': 15},
            'Butter': {'unit': 'kg', 'quantity': 0.03, 'stock': 50, 'reorder_level': 10},
            'Eggs': {'unit': 'piece', 'quantity': 1, 'stock': 500, 'reorder_level': 100},
            'Chocolate': {'unit': 'kg', 'quantity': 0.05, 'stock': 40, 'reorder_level': 8},
            'Vanilla Extract': {'unit': 'l', 'quantity': 0.005, 'stock': 5, 'reorder_level': 1},
            'Cream': {'unit': 'l', 'quantity': 0.1, 'stock': 30, 'reorder_level': 6},
        },
        'drinks': {
            'Water': {'unit': 'l', 'quantity': 0.25, 'stock': 200, 'reorder_level': 40},
            'Sugar': {'unit': 'kg', 'quantity': 0.02, 'stock': 80, 'reorder_level': 15},
            'Lemon': {'unit': 'piece', 'quantity': 0.5, 'stock': 200, 'reorder_level': 40},
            'Ice': {'unit': 'kg', 'quantity': 0.1, 'stock': 100, 'reorder_level': 20},
            'Coffee Beans': {'unit': 'kg', 'quantity': 0.02, 'stock': 30, 'reorder_level': 6},
            'Milk': {'unit': 'l', 'quantity': 0.2, 'stock': 100, 'reorder_level': 20},
            'Tea Leaves': {'unit': 'kg', 'quantity': 0.01, 'stock': 15, 'reorder_level': 3},
        },
    }

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing ingredient data before seeding',
        )

    def get_or_create_ingredient(self, name, unit, stock, reorder_level):
        """Get or create an ingredient with stock"""
        ingredient, created = Ingredient.objects.get_or_create(
            name=name,
            defaults={
                'unit': unit,
                'stock': Decimal(str(stock)),
                'reorder_level': Decimal(str(reorder_level)),
            }
        )
        
        # Update stock if ingredient already exists
        if not created:
            ingredient.stock = Decimal(str(stock))
            ingredient.reorder_level = Decimal(str(reorder_level))
            ingredient.unit = unit
            ingredient.save()
        
        # Create or update IngredientStock
        stock_record, stock_created = IngredientStock.objects.get_or_create(
            ingredient=ingredient,
            defaults={'quantity': Decimal(str(stock))}
        )
        if not stock_created:
            stock_record.quantity = Decimal(str(stock))
            stock_record.save()
        
        return ingredient

    def create_ingredients_for_menu_item(self, menu_item):
        """Create ingredients for a menu item based on its category"""
        self.stdout.write(f"\nProcessing: {menu_item.name} ({menu_item.category})")
        
        # Get category-specific ingredients
        category_ingredients = self.COMMON_INGREDIENTS.get(menu_item.category, {})
        
        if not category_ingredients:
            self.stdout.write(
                self.style.WARNING(f"  ⚠ No default ingredients defined for category: {menu_item.category}")
            )
            return
        
        # Get all sizes for this menu item
        sizes = MenuItemSize.objects.filter(menu_item=menu_item)
        
        if sizes.exists():
            # Menu item has sizes - use MenuItemSizeIngredient
            self.stdout.write(f"  → Item has {sizes.count()} size(s), creating size-specific ingredients...")
            
            for size in sizes:
                self.stdout.write(f"    → Size: {size.size}")
                
                # Check if ingredients already exist for this size
                existing = MenuItemSizeIngredient.objects.filter(size=size)
                if existing.exists():
                    self.stdout.write(
                        self.style.WARNING(f"      ⚠ Already has {existing.count()} ingredients, skipping...")
                    )
                    continue
                
                # Adjust quantities based on size (M = 1x, L = 1.2x, Mega = 1.5x)
                size_multiplier = {
                    'M': Decimal('1.0'),
                    'L': Decimal('1.2'),
                    'Mega': Decimal('1.5'),
                }.get(size.size, Decimal('1.0'))
                
                for ing_name, ing_data in category_ingredients.items():
                    ingredient = self.get_or_create_ingredient(
                        ing_name,
                        ing_data['unit'],
                        ing_data['stock'],
                        ing_data['reorder_level']
                    )
                    
                    # Calculate quantity based on size
                    base_quantity = Decimal(str(ing_data['quantity']))
                    adjusted_quantity = base_quantity * size_multiplier
                    
                    # Create MenuItemSizeIngredient
                    MenuItemSizeIngredient.objects.get_or_create(
                        size=size,
                        ingredient=ingredient,
                        defaults={'quantity': adjusted_quantity}
                    )
                    self.stdout.write(
                        f"      ✓ Added {ing_name}: {adjusted_quantity}{ing_data['unit']}"
                    )
        else:
            # Menu item has no sizes - use MenuItemIngredient
            self.stdout.write("  → Item has no sizes, creating direct ingredients...")
            
            # Check if ingredients already exist
            existing = MenuItemIngredient.objects.filter(menu_item=menu_item)
            if existing.exists():
                self.stdout.write(
                    self.style.WARNING(f"    ⚠ Already has {existing.count()} ingredients, skipping...")
                )
                return
            
            for ing_name, ing_data in category_ingredients.items():
                ingredient = self.get_or_create_ingredient(
                    ing_name,
                    ing_data['unit'],
                    ing_data['stock'],
                    ing_data['reorder_level']
                )
                
                quantity = Decimal(str(ing_data['quantity']))
                
                # Create MenuItemIngredient
                MenuItemIngredient.objects.get_or_create(
                    menu_item=menu_item,
                    ingredient=ingredient,
                    defaults={'quantity': quantity}
                )
                self.stdout.write(f"    ✓ Added {ing_name}: {quantity}{ing_data['unit']}")

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write(self.style.WARNING('Clearing existing ingredient data...'))
            MenuItemSizeIngredient.objects.all().delete()
            MenuItemIngredient.objects.all().delete()
            IngredientStock.objects.all().delete()
            Ingredient.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Existing ingredient data cleared.'))
        
        self.stdout.write("=" * 60)
        self.stdout.write("Seeding Ingredients, Ingredient Stocks, and Menu Item Links")
        self.stdout.write("=" * 60)
        
        # Get all menu items
        menu_items = MenuItem.objects.all()
        self.stdout.write(f"\nFound {menu_items.count()} menu items")
        
        if menu_items.count() == 0:
            self.stdout.write(
                self.style.WARNING('No menu items found. Please run seed_db first.')
            )
            return
        
        # Process each menu item
        for menu_item in menu_items:
            self.create_ingredients_for_menu_item(menu_item)
        
        # Summary
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("Summary:")
        self.stdout.write(f"  Total Ingredients: {Ingredient.objects.count()}")
        self.stdout.write(f"  Total Ingredient Stocks: {IngredientStock.objects.count()}")
        self.stdout.write(f"  Total MenuItemIngredient links: {MenuItemIngredient.objects.count()}")
        self.stdout.write(f"  Total MenuItemSizeIngredient links: {MenuItemSizeIngredient.objects.count()}")
        self.stdout.write("=" * 60)
        self.stdout.write(self.style.SUCCESS("\n✓ Done!"))




