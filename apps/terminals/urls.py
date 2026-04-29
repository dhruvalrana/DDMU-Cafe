"""
URL patterns for terminal and session management.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers
from .views import POSTerminalViewSet, POSSessionViewSet, CashMovementViewSet

app_name = 'terminals'

router = DefaultRouter()
router.register(r'sessions', POSSessionViewSet, basename='session')
router.register(r'', POSTerminalViewSet, basename='terminal')

# Nested router for cash movements
sessions_router = routers.NestedDefaultRouter(router, r'sessions', lookup='session')
sessions_router.register(r'cash-movements', CashMovementViewSet, basename='session-cash-movement')

urlpatterns = [
    path('', include(router.urls)),
    path('', include(sessions_router.urls)),
]
