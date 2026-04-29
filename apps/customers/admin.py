from django.contrib import admin
from .models import CustomerDisplayConfig, CustomerPromotion


@admin.register(CustomerDisplayConfig)
class CustomerDisplayConfigAdmin(admin.ModelAdmin):
    list_display = ['terminal', 'is_enabled', 'show_order_items', 'show_promotions']
    list_filter = ['is_enabled']


@admin.register(CustomerPromotion)
class CustomerPromotionAdmin(admin.ModelAdmin):
    list_display = ['title', 'display_type', 'display_order', 'is_active', 'start_date', 'end_date']
    list_filter = ['display_type', 'is_active']
    search_fields = ['title']
