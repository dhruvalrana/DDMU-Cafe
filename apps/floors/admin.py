from django.contrib import admin
from .models import Floor, Table, TableReservation


class TableInline(admin.TabularInline):
    model = Table
    extra = 0


@admin.register(Floor)
class FloorAdmin(admin.ModelAdmin):
    list_display = ['name', 'display_order', 'is_active', 'table_count']
    list_filter = ['is_active']
    search_fields = ['name']
    ordering = ['display_order']
    inlines = [TableInline]


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ['table_number', 'floor', 'seats', 'is_active', 'is_occupied']
    list_filter = ['floor', 'is_active', 'is_occupied']
    search_fields = ['table_number', 'name']
    ordering = ['floor', 'table_number']


@admin.register(TableReservation)
class TableReservationAdmin(admin.ModelAdmin):
    list_display = [
        'customer_name', 'table', 'reservation_date', 'reservation_time',
        'party_size', 'status'
    ]
    list_filter = ['status', 'reservation_date', 'table__floor']
    search_fields = ['customer_name', 'customer_phone']
    ordering = ['-reservation_date', '-reservation_time']
