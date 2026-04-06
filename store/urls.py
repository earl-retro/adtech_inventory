from django.urls import path
from . import views

app_name = 'store'

urlpatterns = [
    # Auth
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Dashboard
    path('', views.dashboard, name='dashboard'),

    # Catalog / Products
    path('catalog/', views.catalog, name='catalog'),
    path('catalog/<int:pk>/', views.product_detail, name='product_detail'),

    # Cart
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:pk>/', views.cart_add, name='cart_add'),
    path('cart/remove/<int:pk>/', views.cart_remove, name='cart_remove'),

    # Checkout & Orders
    path('checkout/', views.checkout, name='checkout'),
    path('orders/', views.order_list, name='order_list'),
    path('orders/<int:pk>/', views.order_confirm, name='order_confirm'),

    # PayPal AJAX
    path('paypal/create/', views.paypal_create_order, name='paypal_create'),
    path('paypal/capture/', views.paypal_capture_order, name='paypal_capture'),

    # Inventory
    path('inventory/', views.inventory, name='inventory'),
    path('inventory/stock-in/', views.stock_in, name='stock_in'),
    path('inventory/product/new/', views.product_create, name='product_create'),
    path('inventory/product/<int:pk>/edit/', views.product_edit, name='product_edit'),
    path('inventory/product/<int:pk>/delete/', views.product_delete, name='product_delete'),

    # Customers
    path('customers/', views.customers, name='customers'),
    path('customers/new/', views.customer_create, name='customer_create'),



    # Reports (admin only)
    path('reports/', views.reports, name='reports'),
]
