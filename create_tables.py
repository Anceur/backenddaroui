"""
Script to create initial tables for the restaurant
Run this script to populate the database with tables
"""

import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from main.models import Table

def create_tables():
    """Create initial restaurant tables"""
    
    tables_data = [
        # Main Hall Tables
        {'number': '1', 'capacity': 4, 'location': 'Main Hall - Window'},
        {'number': '2', 'capacity': 4, 'location': 'Main Hall - Window'},
        {'number': '3', 'capacity': 6, 'location': 'Main Hall - Center'},
        {'number': '4', 'capacity': 4, 'location': 'Main Hall - Center'},
        {'number': '5', 'capacity': 4, 'location': 'Main Hall - Center'},
        {'number': '6', 'capacity': 2, 'location': 'Main Hall - Corner'},
        {'number': '7', 'capacity': 2, 'location': 'Main Hall - Corner'},
        
        # Patio Tables
        {'number': '8', 'capacity': 4, 'location': 'Patio - Outdoor'},
        {'number': '9', 'capacity': 4, 'location': 'Patio - Outdoor'},
        {'number': '10', 'capacity': 6, 'location': 'Patio - Outdoor'},
        
        # VIP Section
        {'number': 'VIP-1', 'capacity': 8, 'location': 'VIP Section'},
        {'number': 'VIP-2', 'capacity': 6, 'location': 'VIP Section'},
        
        # Bar Area
        {'number': 'BAR-1', 'capacity': 2, 'location': 'Bar Area'},
        {'number': 'BAR-2', 'capacity': 2, 'location': 'Bar Area'},
        {'number': 'BAR-3', 'capacity': 2, 'location': 'Bar Area'},
    ]
    
    created_count = 0
    skipped_count = 0
    
    for table_data in tables_data:
        # Check if table already exists
        if Table.objects.filter(number=table_data['number']).exists():
            print(f"⏭️  Table {table_data['number']} already exists, skipping...")
            skipped_count += 1
            continue
        
        # Create table
        table = Table.objects.create(
            number=table_data['number'],
            capacity=table_data['capacity'],
            location=table_data['location'],
            is_available=True,
            notes=''
        )
        print(f"✅ Created Table {table.number} - {table.location} (Capacity: {table.capacity})")
        created_count += 1
    
    print(f"\n📊 Summary:")
    print(f"   Created: {created_count} tables")
    print(f"   Skipped: {skipped_count} tables")
    print(f"   Total: {Table.objects.count()} tables in database")

if __name__ == '__main__':
    print("🍽️  Creating Restaurant Tables...\n")
    create_tables()
    print("\n✨ Done!")
