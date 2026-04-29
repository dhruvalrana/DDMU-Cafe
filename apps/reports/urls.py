"""
URL patterns for Reports.
"""

from django.urls import path
from .views import (
    DashboardView,
    DailySalesView,
    HourlySalesView,
    PaymentMethodsView,
    ProductSalesView,
    CategorySalesView,
    StaffPerformanceView,
    SessionSummaryView,
    ExportReportView,
)

app_name = 'reports'

urlpatterns = [
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('daily-sales/', DailySalesView.as_view(), name='daily-sales'),
    path('hourly-sales/', HourlySalesView.as_view(), name='hourly-sales'),
    path('payment-methods/', PaymentMethodsView.as_view(), name='payment-methods'),
    path('product-sales/', ProductSalesView.as_view(), name='product-sales'),
    path('category-sales/', CategorySalesView.as_view(), name='category-sales'),
    path('staff-performance/', StaffPerformanceView.as_view(), name='staff-performance'),
    path('sessions/', SessionSummaryView.as_view(), name='sessions'),
    path('export/', ExportReportView.as_view(), name='export'),
]
