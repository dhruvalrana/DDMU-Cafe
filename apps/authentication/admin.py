from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserSession


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'first_name', 'last_name', 'role', 'is_active', 'created_at']
    list_filter = ['role', 'is_active', 'is_staff']
    search_fields = ['email', 'first_name', 'last_name', 'phone']
    ordering = ['-created_at']
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'phone', 'avatar')}),
        ('Role & Permissions', {
            'fields': (
                'role', 'pin_code',
                'can_access_pos', 'can_access_kitchen', 'can_access_reports',
                'can_manage_products', 'can_manage_users',
                'can_void_orders', 'can_apply_discounts', 'max_discount_percent',
            )
        }),
        ('Status', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'first_name', 'last_name', 'role'),
        }),
    )


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ['user', 'ip_address', 'is_active', 'created_at', 'expires_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['user__email', 'ip_address']
    readonly_fields = ['token_jti', 'user_agent']
