"""
Authentication views and API endpoints.
"""

from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model

from apps.core.permissions import IsAdminUser, IsManagerOrAdmin
from .serializers import (
    UserSerializer,
    UserCreateSerializer,
    UserUpdateSerializer,
    AdminUserUpdateSerializer,
    ChangePasswordSerializer,
    SetPINSerializer,
    PINLoginSerializer,
    CustomTokenObtainPairSerializer,
)

User = get_user_model()


class SignUpView(generics.CreateAPIView):
    """
    User registration endpoint.
    
    POST /api/v1/auth/signup/
    """
    queryset = User.objects.all()
    serializer_class = UserCreateSerializer
    permission_classes = [AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Generate tokens for the new user
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'success': True,
            'message': 'Account created successfully.',
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)


class LoginView(TokenObtainPairView):
    """
    User login endpoint with JWT tokens.
    
    POST /api/v1/auth/login/
    """
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [AllowAny]


class LogoutView(APIView):
    """
    Logout endpoint - blacklists the refresh token.
    
    POST /api/v1/auth/logout/
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            return Response({
                'success': True,
                'message': 'Logged out successfully.'
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class MeView(generics.RetrieveUpdateAPIView):
    """
    Get/update current user profile.
    
    GET /api/v1/auth/me/
    PATCH /api/v1/auth/me/
    """
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user
    
    def get_serializer_class(self):
        if self.request.method == 'GET':
            return UserSerializer
        return UserUpdateSerializer


class ChangePasswordView(APIView):
    """
    Change password endpoint.
    
    POST /api/v1/auth/change-password/
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()
        
        return Response({
            'success': True,
            'message': 'Password changed successfully.'
        })


class SetPINView(APIView):
    """
    Set quick login PIN for POS.
    
    POST /api/v1/auth/set-pin/
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = SetPINSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        
        request.user.pin_code = serializer.validated_data['pin_code']
        request.user.save(update_fields=['pin_code'])
        
        return Response({
            'success': True,
            'message': 'PIN set successfully.'
        })


class PINLoginView(APIView):
    """
    Quick login using PIN (for POS terminals).
    
    POST /api/v1/auth/pin-login/
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = PINLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            user = User.objects.get(
                email=serializer.validated_data['email'],
                pin_code=serializer.validated_data['pin_code'],
                is_active=True
            )
        except User.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Invalid email or PIN.'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'success': True,
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        })


class UserListView(generics.ListCreateAPIView):
    """
    List all users or create new user (admin/manager only).
    
    GET /api/v1/auth/users/
    POST /api/v1/auth/users/
    """
    queryset = User.objects.all()
    permission_classes = [IsManagerOrAdmin]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return UserCreateSerializer
        return UserSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by role
        role = self.request.query_params.get('role')
        if role:
            queryset = queryset.filter(role=role)
        
        # Filter by active status
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        return queryset


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Get, update, or delete a user (admin only).
    
    GET /api/v1/auth/users/<id>/
    PATCH /api/v1/auth/users/<id>/
    DELETE /api/v1/auth/users/<id>/
    """
    queryset = User.objects.all()
    permission_classes = [IsAdminUser]
    
    def get_serializer_class(self):
        if self.request.method in ['PATCH', 'PUT']:
            return AdminUserUpdateSerializer
        return UserSerializer
    
    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        user.is_active = False
        user.save(update_fields=['is_active'])
        return Response({
            'success': True,
            'message': 'User deactivated successfully.'
        })
