"""
URL Configuration for Template Views
"""
from django.urls import path
from . import template_views as views

urlpatterns = [
    # Authentication
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # POS Terminal
    path('pos/', views.pos_terminal, name='pos_terminal'),
    path('pos/create-order/', views.pos_create_order, name='pos_create_order'),
    
    # Virtual Assistant
    path('assistant/', views.chatbot_assistant, name='chatbot_assistant'),
    
    # Orders
    path('orders/', views.order_list, name='order_list'),
    path('orders/<uuid:order_id>/', views.order_detail, name='order_detail'),
    path('orders/<uuid:order_id>/update-status/', views.order_update_status, name='order_update_status'),
    path('orders/<uuid:order_id>/payment/', views.order_payment, name='order_payment'),
    
    # Kitchen Display
    path('kitchen/', views.kitchen_display, name='kitchen_display'),
    path('kitchen/<uuid:order_id>/update-status/', views.kitchen_update_status, name='kitchen_update_status'),
    
    # Tables
    path('tables/', views.table_list, name='table_list'),
    path('tables/<uuid:table_id>/update-status/', views.table_update_status, name='table_update_status'),
    
    # Products
    path('products/', views.product_list, name='product_list'),
    path('products/add/', views.product_add, name='product_add'),
    path('products/<uuid:product_id>/edit/', views.product_edit, name='product_edit'),
    path('products/<uuid:product_id>/toggle/', views.product_toggle, name='product_toggle'),
    path('products/<uuid:product_id>/delete/', views.product_delete, name='product_delete'),
    
    # Customers
    path('customers/', views.customer_list, name='customer_list'),
    path('customers/<uuid:customer_id>/', views.customer_detail, name='customer_detail'),
    path('customers/<uuid:customer_id>/edit/', views.customer_edit, name='customer_edit'),
    
    # Reports
    path('reports/', views.reports, name='reports'),
    
    # Settings
    path('settings/', views.settings_view, name='settings'),
]
