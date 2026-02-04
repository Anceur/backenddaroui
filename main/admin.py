from django.contrib import admin
from .models import (
    CustomUser, Profile, MenuItem, MenuItemSize, Order, OrderItem, 
    Ingredient, MenuItemIngredient, MenuItemSizeIngredient, IngredientStock, 
    IngredientTrace, Table, OfflineOrder, OfflineOrderItem, TableSession, Notification,
    Supplier, SupplierHistory,Expense, StaffMember, Promotion, PromotionItem
)

# Register your models here.
admin.site.register(CustomUser)
admin.site.register(Profile)
admin.site.register(Order)
admin.site.register(MenuItem)
admin.site.register(MenuItemSize)
admin.site.register(OrderItem)
admin.site.register(Ingredient)
admin.site.register(MenuItemSizeIngredient)
admin.site.register(MenuItemIngredient)
admin.site.register(IngredientStock)
admin.site.register(IngredientTrace)
admin.site.register(Table)
admin.site.register(OfflineOrder)
admin.site.register(OfflineOrderItem)
admin.site.register(TableSession)
admin.site.register(Notification)
admin.site.register(Supplier)
admin.site.register(SupplierHistory)
admin.site.register(Expense)
admin.site.register(StaffMember)

admin.site.register(Promotion)
admin.site.register(PromotionItem)
