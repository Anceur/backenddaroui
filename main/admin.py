from django.contrib import admin
from .models import (
    CustomUser,
    Profile,
    MenuItem,
    MenuItemSize,
    MenuItemExtra,
    Order,
    OrderItem,
    Ingredient,
    MenuItemIngredient,
    MenuItemSizeIngredient,
    IngredientStock,
    IngredientTrace,
    Table,
    OfflineOrder,
    OfflineOrderItem,
    TableSession,
    Notification,
    Supplier,
    SupplierHistory,
    Expense,
    StaffMember,
    Promotion,
    PromotionItem,
)


class MenuItemSizeInline(admin.TabularInline):
    model = MenuItemSize
    extra = 1


class MenuItemExtraInline(admin.TabularInline):
    model = MenuItemExtra
    extra = 1


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "featured")
    search_fields = ("name", "category")
    list_filter = ("category", "featured")
    inlines = [MenuItemSizeInline, MenuItemExtraInline]


@admin.register(MenuItemSize)
class MenuItemSizeAdmin(admin.ModelAdmin):
    list_display = ("menu_item", "size", "price")
    list_filter = ("size", "menu_item__category")
    search_fields = ("menu_item__name",)


@admin.register(MenuItemExtra)
class MenuItemExtraAdmin(admin.ModelAdmin):
    list_display = ("menu_item", "name", "price")
    search_fields = ("menu_item__name", "name")
    list_filter = ("menu_item__category",)


# Register your models here.
admin.site.register(CustomUser)
admin.site.register(Profile)
admin.site.register(Order)
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
