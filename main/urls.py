from django.urls import path
from .views import CustomTokenObtainPairView
from .views import CheckAuthenticatedView, ReturnRole,LogoutView,ReturnUser,ChangePasswordView
from .views import ProfileView, CreateUserWithProfileView
from .views import (
    OrderListCreateView, OrderDetailView, OrderStatusCountView, PublicOrderCreateView,
    OfflineOrderCreateView, OfflineOrderListView, OfflineOrderDetailView, OfflineOrderAdminListView,
    TableListCreateView, TableDetailView, PublicTableValidateView, DashboardStatsView, AnalyticsView, CustomersListView,
    TableSessionGenerateView, TableSessionValidateView, TableSessionListView, TableSessionDetailView,
    CashierTablesStatusView, CashierPendingOrdersView, CashierConfirmOrderView, CashierOrderDetailView,
    CashierTableOccupancyView
)
from .views import (
    MenuItemListCreateView, MenuItemDetailView, PublicMenuItemListView,
    MenuItemSizeListCreateView, MenuItemSizeDetailView,
    OrderItemListCreateView, OrderItemDetailView,
    IngredientListCreateView, IngredientDetailView,
    MenuItemIngredientListCreateView, MenuItemIngredientDetailView,
    MenuItemSizeIngredientListCreateView, MenuItemSizeIngredientDetailView
)
from .views_ingredient_tracking import (
    IngredientStockListCreateView, IngredientStockDetailView,
    IngredientTraceListView, IngredientTraceDetailView
)
from .views_notifications import (
    NotificationListView, NotificationUnreadCountView,
    NotificationMarkReadView, NotificationMarkAllReadView,
    NotificationDetailView
)

urlpatterns = [
    # Authentication endpoints
    path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('is-authenticated/', CheckAuthenticatedView.as_view(), name="isauthenticated"),
    path('role/', ReturnRole.as_view(), name="role"),
    path('logout/',LogoutView.as_view(),name="logout"),
    path('user/',ReturnUser.as_view(),name="user"),
    path('change-password/',ChangePasswordView.as_view(),name="changepassword"),
    
    # Profile endpoints
    path('profile/',ProfileView.as_view(),name="profile"),
    
    # User management endpoints
    path('create-user/',CreateUserWithProfileView.as_view(),name="create_user"),
    path('create-user/<int:user_id>/',CreateUserWithProfileView.as_view(),name="user_detail"),
    
    # Order endpoints
    path('orders/', OrderListCreateView.as_view(), name='order_list_create'),
    path('orders/public/', PublicOrderCreateView.as_view(), name='public_order_create'),
    path('orders/status-counts/', OrderStatusCountView.as_view(), name='order_status_counts'),
    path('orders/<int:order_id>/', OrderDetailView.as_view(), name='order_detail'),
    
    # Offline Order endpoints
    path('offline-orders/', OfflineOrderCreateView.as_view(), name='offline_order_create'),
    path('offline-orders/list/', OfflineOrderListView.as_view(), name='offline_order_list'),
    path('offline-orders/admin/', OfflineOrderAdminListView.as_view(), name='offline_order_admin_list'),
    path('offline-orders/<int:offline_order_id>/', OfflineOrderDetailView.as_view(), name='offline_order_detail'),
    
    # Table endpoints
    path('tables/', TableListCreateView.as_view(), name='table_list_create'),
    path('tables/<int:table_id>/', TableDetailView.as_view(), name='table_detail'),
    path('tables/validate/', PublicTableValidateView.as_view(), name='public_table_validate'),
    
    # Table Session endpoints (Security)
    path('table-sessions/generate/', TableSessionGenerateView.as_view(), name='table_session_generate'),
    path('table-sessions/validate/', TableSessionValidateView.as_view(), name='table_session_validate'),
    path('table-sessions/', TableSessionListView.as_view(), name='table_session_list'),
    path('table-sessions/<int:session_id>/', TableSessionDetailView.as_view(), name='table_session_detail'),
    
    # Cashier Panel endpoints
    path('cashier/tables-status/', CashierTablesStatusView.as_view(), name='cashier_tables_status'),
    path('cashier/pending-orders/', CashierPendingOrdersView.as_view(), name='cashier_pending_orders'),
    path('cashier/confirm-order/', CashierConfirmOrderView.as_view(), name='cashier_confirm_order'),
    path('cashier/order-detail/', CashierOrderDetailView.as_view(), name='cashier_order_detail'),
    path('cashier/tables/<int:table_id>/occupancy/', CashierTableOccupancyView.as_view(), name='cashier_table_occupancy'),
    
    # Dashboard and Analytics endpoints
    path('dashboard/stats/', DashboardStatsView.as_view(), name='dashboard_stats'),
    path('analytics/', AnalyticsView.as_view(), name='analytics'),
    path('customers/', CustomersListView.as_view(), name='customers_list'),
    
    # OrderItem endpoints
    path('order-items/', OrderItemListCreateView.as_view(), name='order_item_list_create'),
    path('order-items/<int:item_id>/', OrderItemDetailView.as_view(), name='order_item_detail'),
    
    # Menu item endpoints
    path('menu-items/', MenuItemListCreateView.as_view(), name='menu_item_list_create'),
    path('menu-items/<int:item_id>/', MenuItemDetailView.as_view(), name='menu_item_detail'),
    path('menu-items/public/', PublicMenuItemListView.as_view(), name='public_menu_item_list'),
    
    # MenuItemSize endpoints
    path('menu-item-sizes/', MenuItemSizeListCreateView.as_view(), name='menu_item_size_list_create'),
    path('menu-item-sizes/<int:size_id>/', MenuItemSizeDetailView.as_view(), name='menu_item_size_detail'),
    
    # Ingredient endpoints
    path('ingredients/', IngredientListCreateView.as_view(), name='ingredient_list_create'),
    path('ingredients/<int:ingredient_id>/', IngredientDetailView.as_view(), name='ingredient_detail'),
    
    # MenuItemIngredient endpoints (for items without sizes)
    path('menu-item-ingredients/', MenuItemIngredientListCreateView.as_view(), name='menu_item_ingredient_list_create'),
    path('menu-item-ingredients/<int:item_ingredient_id>/', MenuItemIngredientDetailView.as_view(), name='menu_item_ingredient_detail'),
    
    # MenuItemSizeIngredient endpoints (for items with sizes)
    path('menu-item-size-ingredients/', MenuItemSizeIngredientListCreateView.as_view(), name='menu_item_size_ingredient_list_create'),
    path('menu-item-size-ingredients/<int:size_ingredient_id>/', MenuItemSizeIngredientDetailView.as_view(), name='menu_item_size_ingredient_detail'),
    
    # IngredientStock endpoints
    path('ingredient-stocks/', IngredientStockListCreateView.as_view(), name='ingredient_stock_list_create'),
    path('ingredient-stocks/<int:stock_id>/', IngredientStockDetailView.as_view(), name='ingredient_stock_detail'),
    
    # IngredientTrace endpoints (admin only)
    path('ingredient-traces/', IngredientTraceListView.as_view(), name='ingredient_trace_list'),
    path('ingredient-traces/<int:trace_id>/', IngredientTraceDetailView.as_view(), name='ingredient_trace_detail'),
    
    # Notification endpoints
    path('notifications/', NotificationListView.as_view(), name='notification_list'),
    path('notifications/unread-count/', NotificationUnreadCountView.as_view(), name='notification_unread_count'),
    path('notifications/mark-read/', NotificationMarkReadView.as_view(), name='notification_mark_read'),
    path('notifications/mark-all-read/', NotificationMarkAllReadView.as_view(), name='notification_mark_all_read'),
    path('notifications/<int:notification_id>/', NotificationDetailView.as_view(), name='notification_detail'),
]