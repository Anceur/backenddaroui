"""
Django management command to create ingredients for all menu items
Usage: python manage.py create_ingredients
"""
from django.core.management.base import BaseCommand
from main.models import MenuItem, MenuItemSize, Ingredient, MenuItemSizeIngredient
from decimal import Decimal


class Command(BaseCommand):
    help = 'Create ingredients for all menu items'

    # Common ingredients that might be used across different menu items
    COMMON_INGREDIENTS = {
        'burger': {
            'Beef Patty': {'unit': 'g', 'quantity': 150},
            'Bun': {'unit': 'piece', 'quantity': 1},
            'Lettuce': {'unit': 'g', 'quantity': 20},
            'Tomato': {'unit': 'g', 'quantity': 30},
            'Onion': {'unit': 'g', 'quantity': 15},
            'Cheese': {'unit': 'g', 'quantity': 25},
            'Pickles': {'unit': 'g', 'quantity': 10},
            'Mayonnaise': {'unit': 'ml', 'quantity': 15},
            'Ketchup': {'unit': 'ml', 'quantity': 10},
        },
        'pizza': {
            'Pizza Dough': {'unit': 'g', 'quantity': 200},
            'Tomato Sauce': {'unit': 'ml', 'quantity': 50},
            'Mozzarella Cheese': {'unit': 'g', 'quantity': 100},
            'Pepperoni': {'unit': 'g', 'quantity': 30},
            'Mushrooms': {'unit': 'g', 'quantity': 40},
            'Bell Peppers': {'unit': 'g', 'quantity': 30},
            'Olives': {'unit': 'g', 'quantity': 20},
            'Onion': {'unit': 'g', 'quantity': 25},
        },
        'sandwich': {
            'Bread': {'unit': 'piece', 'quantity': 2},
            'Chicken Breast': {'unit': 'g', 'quantity': 150},
            'Lettuce': {'unit': 'g', 'quantity': 25},
            'Tomato': {'unit': 'g', 'quantity': 30},
            'Mayonnaise': {'unit': 'ml', 'quantity': 15},
            'Cheese': {'unit': 'g', 'quantity': 30},
        },
        'plat': {
            'Rice': {'unit': 'g', 'quantity': 200},
            'Chicken': {'unit': 'g', 'quantity': 200},
            'Vegetables': {'unit': 'g', 'quantity': 150},
            'Sauce': {'unit': 'ml', 'quantity': 50},
        },
        'tacos': {
            'Tortilla': {'unit': 'piece', 'quantity': 2},
            'Ground Beef': {'unit': 'g', 'quantity': 100},
            'Lettuce': {'unit': 'g', 'quantity': 30},
            'Tomato': {'unit': 'g', 'quantity': 40},
            'Cheese': {'unit': 'g', 'quantity': 30},
            'Sour Cream': {'unit': 'ml', 'quantity': 20},
            'Salsa': {'unit': 'ml', 'quantity': 15},
        },
        'desserts': {
            'Flour': {'unit': 'g', 'quantity': 100},
            'Sugar': {'unit': 'g', 'quantity': 50},
            'Butter': {'unit': 'g', 'quantity': 30},
            'Eggs': {'unit': 'piece', 'quantity': 1},
            'Chocolate': {'unit': 'g', 'quantity': 50},
        },
        'drinks': {
            'Water': {'unit': 'ml', 'quantity': 250},
            'Sugar': {'unit': 'g', 'quantity': 20},
            'Lemon': {'unit': 'piece', 'quantity': 0.5},
            'Ice': {'unit': 'g', 'quantity': 100},
        },
    }

    def get_or_create_ingredient(self, name, unit='g'):
        """Get or create an ingredient"""
        ingredient, created = Ingredient.objects.get_or_create(
            name=name,
            defaults={
                'unit': unit,
                'stock': 1000,  # Default stock
                'reorder_level': 100,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"  ✓ Created ingredient: {name} ({unit})"))
        return ingredient

    def create_ingredients_for_menu_item(self, menu_item):
        """Create ingredients for a menu item based on its category"""
        self.stdout.write(f"\nProcessing: {menu_item.name} ({menu_item.category})")
        
        # Get category-specific ingredients
        category_ingredients = self.COMMON_INGREDIENTS.get(menu_item.category, {})
        
        if not category_ingredients:
            self.stdout.write(self.style.WARNING(f"  ⚠ No default ingredients defined for category: {menu_item.category}"))
            return
        
        # Get all sizes for this menu item
        sizes = MenuItemSize.objects.filter(menu_item=menu_item)
        
        if not sizes.exists():
            self.stdout.write(self.style.WARNING(f"  ⚠ No sizes found for {menu_item.name}"))
            return
        
        # Create ingredients for each size
        for size in sizes:
            self.stdout.write(f"  → Size: {size.size}")
            
            # Check if ingredients already exist for this size
            existing = MenuItemSizeIngredient.objects.filter(size=size)
            if existing.exists():
                self.stdout.write(self.style.WARNING(f"    ⚠ Already has {existing.count()} ingredients, skipping..."))
                continue
            
            # Create ingredients based on size
            # Adjust quantities based on size (M = 1x, L = 1.2x, Mega = 1.5x)
            size_multiplier = {
                'M': Decimal('1.0'),
                'L': Decimal('1.2'),
                'Mega': Decimal('1.5'),
            }.get(size.size, Decimal('1.0'))
            
            for ing_name, ing_data in category_ingredients.items():
                ingredient = self.get_or_create_ingredient(ing_name, ing_data['unit'])
                
                # Calculate quantity based on size
                base_quantity = Decimal(str(ing_data['quantity']))
                adjusted_quantity = base_quantity * size_multiplier
                
                # Create MenuItemSizeIngredient
                MenuItemSizeIngredient.objects.create(
                    size=size,
                    ingredient=ingredient,
                    quantity=adjusted_quantity
                )
                self.stdout.write(f"    ✓ Added {ing_name}: {adjusted_quantity}{ing_data['unit']}")

    def handle(self, *args, **options):
        self.stdout.write("=" * 60)
        self.stdout.write("Creating Ingredients for All Menu Items")
        self.stdout.write("=" * 60)
        
        # Get all menu items
        menu_items = MenuItem.objects.all()
        self.stdout.write(f"\nFound {menu_items.count()} menu items")
        
        # Process each menu item
        for menu_item in menu_items:
            self.create_ingredients_for_menu_item(menu_item)
        
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("Summary:")
        self.stdout.write(f"  Total Ingredients: {Ingredient.objects.count()}")
        self.stdout.write(f"  Total MenuItemSizeIngredient links: {MenuItemSizeIngredient.objects.count()}")
        self.stdout.write("=" * 60)
        self.stdout.write(self.style.SUCCESS("\n✓ Done!"))

