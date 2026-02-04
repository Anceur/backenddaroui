"""
Django management command to add default 'M' size to menu items that don't have any sizes
"""
from django.core.management.base import BaseCommand
from main.models import MenuItem, MenuItemSize


class Command(BaseCommand):
    help = 'Add default "M" size to menu items that don\'t have any sizes'

    def handle(self, *args, **options):
        self.stdout.write('Adding default "M" sizes to menu items...')
        
        menu_items = MenuItem.objects.all()
        created_count = 0
        skipped_count = 0
        
        for menu_item in menu_items:
            existing_sizes = MenuItemSize.objects.filter(menu_item=menu_item)
            
            if not existing_sizes.exists():
                MenuItemSize.objects.create(
                    menu_item=menu_item,
                    size='M',
                    price=menu_item.price
                )
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'  ✓ Created default "M" size for: {menu_item.name} (price: {menu_item.price})')
                )
            else:
                skipped_count += 1
                self.stdout.write(
                    f'  - Skipped {menu_item.name} (already has {existing_sizes.count()} size(s))'
                )
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'✅ Completed! Created {created_count} default sizes, skipped {skipped_count} items.'
        ))




