from django.urls import path
from .views import PromotionListCreateView, PromotionDetailView, PublicPromotionListView, StaffUploadImageView
from .views import CustomTokenObtainPairView
from .views import CheckAuthenticatedView, ReturnRole,LogoutView,ReturnUser,ChangePasswordView
from .views import ProfileView, CreateUserWithProfileView
from .views import (
    OrderListCreateView, OrderDetailView, OrderStatusCountView, PublicOrderCreateView, SecurityTokenView,
    OfflineOrderCreateView, OfflineOrderListView, OfflineOrderDetailView, OfflineOrderAdminListView,
    TableListCreateView, TableDetailView, PublicTableValidateView, DashboardStatsView, AnalyticsView, CustomersListView,
    TableSessionGenerateView, TableSessionValidateView, TableSessionListView, TableSessionDetailView,
    CashierTablesStatusView, CashierPendingOrdersView, CashierConfirmOrderView, CashierOrderDetailView,
    CashierTableOccupancyView, CashierCreateOfflineOrderView, OrderTicketPrintView,
    MenuItemMovementView, ExpenseListCreateView, ExpenseDetailView, ExpenseAnalyticsView,
    EarningsAnalyticsView, StaffMemberView, RestaurantInfoView
)
from .views import (
    MenuItemListCreateView, MenuItemDetailView, PublicMenuItemListView,
    MenuItemSizeListCreateView, MenuItemSizeDetailView,
    OrderItemListCreateView, OrderItemDetailView,
    IngredientListCreateView, IngredientDetailView,
    MenuItemIngredientListCreateView, MenuItemIngredientDetailView,
    MenuItemSizeIngredientListCreateView, MenuItemSizeIngredientDetailView,
    SupplierListCreateView, SupplierDetailView,
    SupplierHistoryListView, SupplierHistoryCreateView, SupplierHistoryDetailView,
    ClientFideleListCreateView, ClientFideleDetailView
)
from .views_ingredient_tracking import (
    IngredientStockListCreateView, IngredientStockDetailView,
    IngredientTraceListView, IngredientTraceDetailView
)
from .views_cashier_manual_order import CashierManualOrderCreateView
from .views_notifications import (
    NotificationListView, NotificationUnreadCountView,
    NotificationMarkReadView, NotificationMarkAllReadView,
    NotificationDetailView
)
from .views_websocket import WebSocketTokenView
from .views_table_session import (
    TableSessionCreateView, TableSessionValidateView as TableSessionValidatePublicView,
    TableSessionOrderCreateView, TableSessionEndView, TableListView as PublicTableListView,
    PublicMenuView
)
from .views_cashier_history import CashierOrderHistoryView
from .views_cashier_decline import CashierDeclineOrderView
from .views_public_status import PublicRestaurantStatusView
from .views import MenuItemUploadImageView
urlpatterns = [
    # ... existing patterns ...
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
    path('orders/security-token/', SecurityTokenView.as_view(), name='security_token'),
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
    
    # Public Table Session endpoints (for clients)
    path('public/table-sessions/create/', TableSessionCreateView.as_view(), name='public_table_session_create'),
    path('public/table-sessions/validate/', TableSessionValidatePublicView.as_view(), name='public_table_session_validate'),
    path('public/table-sessions/order/', TableSessionOrderCreateView.as_view(), name='public_table_session_order'),
    path('public/table-sessions/end/', TableSessionEndView.as_view(), name='public_table_session_end'),
    path('public/tables/', PublicTableListView.as_view(), name='public_table_list'),
    path('public/menu/', PublicMenuView.as_view(), name='public_menu'),
    
    # Cashier Panel endpoints
    path('cashier/tables-status/', CashierTablesStatusView.as_view(), name='cashier_tables_status'),
    path('cashier/pending-orders/', CashierPendingOrdersView.as_view(), name='cashier_pending_orders'),
    path('cashier/confirm-order/', CashierConfirmOrderView.as_view(), name='cashier_confirm_order'),
    path('cashier/decline-order/', CashierDeclineOrderView.as_view(), name='cashier_decline_order'),
    path('cashier/orders/<int:order_id>/ticket/', OrderTicketPrintView.as_view(), name='order_ticket_print'),
    path('cashier/order-detail/', CashierOrderDetailView.as_view(), name='cashier_order_detail'),
    path('cashier/create-order/', CashierCreateOfflineOrderView.as_view(), name='cashier_create_order'),
    path('cashier/manual-online-order/', CashierManualOrderCreateView.as_view(), name='cashier_manual_online_order_create'),
    path('cashier/order-history/', CashierOrderHistoryView.as_view(), name='cashier_order_history'),
    path('cashier/tables/<int:table_id>/occupancy/', CashierTableOccupancyView.as_view(), name='cashier_table_occupancy'),
    
    # Dashboard and Analytics endpoints
    path('dashboard/stats/', DashboardStatsView.as_view(), name='dashboard_stats'),
    path('analytics/', AnalyticsView.as_view(), name='analytics'),
    path('analytics/menu-item-movement/', MenuItemMovementView.as_view(), name='menu_item_movement'),
    path('customers/', CustomersListView.as_view(), name='customers_list'),
    
    # Expense endpoints
    path('expenses/', ExpenseListCreateView.as_view(), name='expense_list_create'),
    path('expenses/<int:pk>/', ExpenseDetailView.as_view(), name='expense_detail'),
    path('expenses/analytics/', ExpenseAnalyticsView.as_view(), name='expense_analytics'),
    path('earnings/analytics/', EarningsAnalyticsView.as_view(), name='earnings_analytics'),
    
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
    
    # Supplier endpoints
    path('suppliers/', SupplierListCreateView.as_view(), name='supplier_list_create'),
    path('suppliers/<int:supplier_id>/', SupplierDetailView.as_view(), name='supplier_detail'),
    
    # Supplier History endpoints
    path('supplier-history/', SupplierHistoryListView.as_view(), name='supplier_history_list'),
    path('supplier-history/create/', SupplierHistoryCreateView.as_view(), name='supplier_history_create'),
    path('supplier-history/<int:history_id>/', SupplierHistoryDetailView.as_view(), name='supplier_history_detail'),
    
    # Notification endpoints
    path('notifications/', NotificationListView.as_view(), name='notification_list'),
    path('notifications/unread-count/', NotificationUnreadCountView.as_view(), name='notification_unread_count'),
    path('notifications/mark-read/', NotificationMarkReadView.as_view(), name='notification_mark_read'),
    path('notifications/mark-all-read/', NotificationMarkAllReadView.as_view(), name='notification_mark_all_read'),
    path('notifications/<int:notification_id>/', NotificationDetailView.as_view(), name='notification_detail'),
    
    # WebSocket token endpoint
    path('websocket-token/', WebSocketTokenView.as_view(), name='websocket_token'),
    
    # Client Fidele endpoints
    path('clients-fidele/', ClientFideleListCreateView.as_view(), name='client_fidele_list_create'),
    path('clients-fidele/<int:pk>/', ClientFideleDetailView.as_view(), name='client_fidele_detail'),
    # Staff Management (New)
    path('staff/', StaffMemberView.as_view(), name='staff-list'),
    path('staff/<int:pk>/', StaffMemberView.as_view(), name='staff-detail'),
    path('promotions/', PromotionListCreateView.as_view(), name='promotion-list'),
    path('promotions/public/', PublicPromotionListView.as_view(), name='public-promotion-list'),
    path('promotions/<int:pk>/', PromotionDetailView.as_view(), name='promotion-detail'),
    path('restaurant-settings/', RestaurantInfoView.as_view(), name='restaurant-settings'),
    path('public/restaurant-status/', PublicRestaurantStatusView.as_view(), name='public_restaurant_status'),


    path('staff/upload-image/', StaffUploadImageView.as_view(), name='staff_upload_image'),
    path('menu-items/upload-image/', MenuItemUploadImageView.as_view(), name='menu_item_upload_image'),
]





