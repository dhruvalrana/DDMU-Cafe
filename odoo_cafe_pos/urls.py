"""
Main URL configuration for Odoo Cafe POS.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from rest_framework import permissions
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from apps.core.views import HealthCheckView, APIRootView

urlpatterns = [
    # Root redirect to Dashboard (template views)
    path('', RedirectView.as_view(url='/app/', permanent=False), name='home'),
    
    # Template-based Frontend Views
    path('app/', include('apps.core.template_urls')),
    
    # Admin
    path('admin/', admin.site.urls),
    
    # Health check
    path('health/', HealthCheckView.as_view(), name='health-check'),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # API Root
    path('api/', APIRootView.as_view(), name='api-root'),
    
    # API v1 endpoints
    path('api/v1/', include([
        # Authentication
        path('auth/', include('apps.authentication.urls')),
        
        # Core modules
        path('products/', include('apps.products.urls')),
        path('payments/', include('apps.payments.urls')),
        path('floors/', include('apps.floors.urls')),
        path('terminals/', include('apps.terminals.urls')),
        path('orders/', include('apps.orders.urls')),
        path('kitchen/', include('apps.kitchen.urls')),
        path('customers/', include('apps.customers.urls')),
        path('reports/', include('apps.reports.urls')),
        path('self-order/', include('apps.self_order.urls')),
        
        # Virtual Assistant Chatbot
        path('chatbot/', include('apps.chatbot.urls')),
    ])),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
