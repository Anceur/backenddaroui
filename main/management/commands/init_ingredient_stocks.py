"""
Django management command to initialize IngredientStock records for all ingredients
Usage: python manage.py init_ingredient_stocks
"""
from django.core.management.base import BaseCommand
from main.models import Ingredient, IngredientStock


class Command(BaseCommand):
    help = 'Initialize IngredientStock records for all ingredients'

    def handle(self, *args, **options):
        self.stdout.write("=" * 60)
        self.stdout.write("Initializing IngredientStock Records")
        self.stdout.write("=" * 60)
        
        # Get all ingredients
        ingredients = Ingredient.objects.all()
        self.stdout.write(f"\nFound {ingredients.count()} ingredients")
        
        created_count = 0
        updated_count = 0
        
        for ingredient in ingredients:
            # Check if stock record already exists
            stock_record, created = IngredientStock.objects.get_or_create(
                ingredient=ingredient,
                defaults={
                    'quantity': ingredient.stock,  # Use the ingredient's stock value
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  ✓ Created stock record for {ingredient.name}: "
                        f"{stock_record.quantity} {ingredient.unit}"
                    )
                )
            else:
                # Update existing record to match ingredient stock if different
                if stock_record.quantity != ingredient.stock:
                    old_quantity = stock_record.quantity
                    stock_record.quantity = ingredient.stock
                    stock_record.save()
                    updated_count += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"  ↻ Updated stock record for {ingredient.name}: "
                            f"{old_quantity} → {ingredient.stock} {ingredient.unit}"
                        )
                    )
                else:
                    self.stdout.write(
                        f"  - {ingredient.name} already has stock record: "
                        f"{stock_record.quantity} {ingredient.unit}"
                    )
        
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("Summary:")
        self.stdout.write(f"  Total Ingredients: {ingredients.count()}")
        self.stdout.write(f"  IngredientStock records created: {created_count}")
        self.stdout.write(f"  IngredientStock records updated: {updated_count}")
        self.stdout.write(f"  Total IngredientStock records: {IngredientStock.objects.count()}")
        self.stdout.write("=" * 60)
        self.stdout.write(self.style.SUCCESS("\n✓ Done!"))

