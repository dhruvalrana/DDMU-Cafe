"""
URL patterns for authentication endpoints.
"""

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    SignUpView,
    LoginView,
    LogoutView,
    MeView,
    ChangePasswordView,
    SetPINView,
    PINLoginView,
    UserListView,
    UserDetailView,
)

app_name = 'authentication'

urlpatterns = [
    # Public auth endpoints
    path('signup/', SignUpView.as_view(), name='signup'),
    path('login/', LoginView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('pin-login/', PINLoginView.as_view(), name='pin-login'),
    
    # Authenticated user endpoints
    path('logout/', LogoutView.as_view(), name='logout'),
    path('me/', MeView.as_view(), name='me'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('set-pin/', SetPINView.as_view(), name='set-pin'),
    
    # User management (admin/manager)
    path('users/', UserListView.as_view(), name='user-list'),
    path('users/<int:pk>/', UserDetailView.as_view(), name='user-detail'),
]
