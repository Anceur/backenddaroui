"""
Script to create ingredients for all menu items
Run with: python manage.py shell < create_ingredients_for_items.py
Or: python manage.py shell -c "$(cat create_ingredients_for_items.py)"
"""
from main.models import MenuItem, MenuItemSize, Ingredient, MenuItemSizeIngredient
from decimal import Decimal

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

def get_or_create_ingredient(name, unit='g'):
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
        print(f"  ✓ Created ingredient: {name} ({unit})")
    return ingredient

def create_ingredients_for_menu_item(menu_item):
    """Create ingredients for a menu item based on its category"""
    print(f"\nProcessing: {menu_item.name} ({menu_item.category})")
    
    # Get category-specific ingredients
    category_ingredients = COMMON_INGREDIENTS.get(menu_item.category, {})
    
    if not category_ingredients:
        print(f"  ⚠ No default ingredients defined for category: {menu_item.category}")
        return
    
    # Get all sizes for this menu item
    sizes = MenuItemSize.objects.filter(menu_item=menu_item)
    
    if not sizes.exists():
        print(f"  ⚠ No sizes found for {menu_item.name}")
        return
    
    # Create ingredients for each size
    for size in sizes:
        print(f"  → Size: {size.size}")
        
        # Check if ingredients already exist for this size
        existing = MenuItemSizeIngredient.objects.filter(size=size)
        if existing.exists():
            print(f"    ⚠ Already has {existing.count()} ingredients, skipping...")
            continue
        
        # Create ingredients based on size
        # Adjust quantities based on size (M = 1x, L = 1.2x, Mega = 1.5x)
        size_multiplier = {
            'M': Decimal('1.0'),
            'L': Decimal('1.2'),
            'Mega': Decimal('1.5'),
        }.get(size.size, Decimal('1.0'))
        
        for ing_name, ing_data in category_ingredients.items():
            ingredient = get_or_create_ingredient(ing_name, ing_data['unit'])
            
            # Calculate quantity based on size
            base_quantity = Decimal(str(ing_data['quantity']))
            adjusted_quantity = base_quantity * size_multiplier
            
            # Create MenuItemSizeIngredient
            MenuItemSizeIngredient.objects.create(
                size=size,
                ingredient=ingredient,
                quantity=adjusted_quantity
            )
            print(f"    ✓ Added {ing_name}: {adjusted_quantity}{ing_data['unit']}")

def main():
    print("=" * 60)
    print("Creating Ingredients for All Menu Items")
    print("=" * 60)
    
    # Get all menu items
    menu_items = MenuItem.objects.all()
    print(f"\nFound {menu_items.count()} menu items")
    
    # Process each menu item
    for menu_item in menu_items:
        create_ingredients_for_menu_item(menu_item)
    
    print("\n" + "=" * 60)
    print("Summary:")
    print(f"  Total Ingredients: {Ingredient.objects.count()}")
    print(f"  Total MenuItemSizeIngredient links: {MenuItemSizeIngredient.objects.count()}")
    print("=" * 60)

if __name__ == '__main__':
    main()

