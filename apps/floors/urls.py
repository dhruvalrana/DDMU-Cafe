"""
URL patterns for floor and table management.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FloorViewSet, TableViewSet, TableReservationViewSet

app_name = 'floors'

router = DefaultRouter()
router.register(r'tables', TableViewSet, basename='table')
router.register(r'reservations', TableReservationViewSet, basename='reservation')
router.register(r'', FloorViewSet, basename='floor')

urlpatterns = [
    path('', include(router.urls)),
]
