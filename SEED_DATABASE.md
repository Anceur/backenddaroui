# Database Seeding Guide

This guide explains how to populate your database with sample data for testing and development.

## Overview

The seed script creates:
- **25 Menu Items** across all categories (Burgers, Pizza, Sandwiches, Plats, Tacos, Desserts, Drinks)
- **14 Menu Item Sizes** for pizzas and milkshakes
- **8 Sample Orders** with different statuses and order types
- **Admin User** (if doesn't exist)

## Usage

### Basic Seeding

To seed the database with sample data:

```bash
cd backend
python manage.py seed_db
```

### Clear and Reseed

To clear existing data and reseed:

```bash
python manage.py seed_db --clear
```

**Warning:** The `--clear` flag will delete all existing:
- Orders
- Menu Item Sizes
- Menu Items

## What Gets Created

### Menu Items by Category

#### Burgers (4 items)
- Classic Burger - 12.50 DA
- Cheese Burger - 13.50 DA
- Double Burger - 18.00 DA
- Chicken Burger - 14.00 DA

#### Pizza (4 items)
- Margherita Pizza - 15.00 DA (with sizes: M, L, Mega)
- Pepperoni Pizza - 18.50 DA (with sizes: M, L, Mega)
- Hawaiian Pizza - 19.00 DA (with sizes: M, L, Mega)
- Vegetarian Pizza - 17.00 DA (with sizes: M, L, Mega)

#### Sandwiches (3 items)
- Club Sandwich - 11.00 DA
- Grilled Chicken Sandwich - 10.50 DA
- Tuna Sandwich - 9.50 DA

#### Plats (3 items)
- Grilled Chicken Plate - 16.00 DA
- Beef Steak Plate - 22.00 DA
- Fish Plate - 18.50 DA

#### Tacos (3 items)
- Beef Tacos - 13.00 DA
- Chicken Tacos - 12.50 DA
- Vegetarian Tacos - 11.00 DA

#### Desserts (4 items)
- Chocolate Cake - 8.00 DA
- Ice Cream Sundae - 7.50 DA
- Cheesecake - 9.00 DA
- Apple Pie - 7.00 DA

#### Drinks (4 items)
- Coca Cola - 3.00 DA
- Orange Juice - 4.00 DA
- Coffee - 3.50 DA
- Milkshake - 5.00 DA (with sizes: M, L)

### Sample Orders

The script creates 8 sample orders with:
- Different statuses: Pending, Preparing, Ready, Delivered, Canceled
- Different order types: Delivery, Dine In
- Different payment methods: Cash, Credit Card, Debit Card, PayPal
- Various customers and addresses

### Admin User

If an admin user doesn't exist, it creates:
- **Username:** `admin`
- **Password:** `admin123`
- **Role:** Admin
- **Email:** admin@restaurant.com

## Running the Seed Script

### First Time Setup

```bash
# Navigate to backend directory
cd backend

# Run migrations first (if not already done)
python manage.py migrate

# Seed the database
python manage.py seed_db
```

### Resetting Data

If you want to start fresh:

```bash
python manage.py seed_db --clear
```

## Customization

To customize the seed data, edit:
```
backend/main/management/commands/seed_db.py
```

You can modify:
- Menu items and their details
- Prices and categories
- Sample orders
- Admin user credentials

## Notes

- The script uses `get_or_create()` to avoid duplicates
- Menu items won't be recreated if they already exist (unless using `--clear`)
- Orders are created with unique customer/phone/date combinations
- The script is idempotent - safe to run multiple times

## Troubleshooting

### Error: "No such table"
Make sure migrations are run first:
```bash
python manage.py migrate
```

### Error: "Module not found"
Ensure you're in the backend directory and Django is properly installed.

### Duplicate entries
Use `--clear` flag to remove existing data before reseeding.


