"""
Serializers for authentication endpoints.
"""

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.password_validation import validate_password
from .models import User


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model (read operations)."""
    
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'phone', 'role', 'avatar',
            'can_access_pos', 'can_access_kitchen', 'can_access_reports',
            'can_manage_products', 'can_manage_users', 'can_void_orders',
            'can_apply_discounts', 'max_discount_percent',
            'is_active', 'created_at', 'last_login',
        ]
        read_only_fields = ['id', 'created_at', 'last_login']


class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""
    
    password = serializers.CharField(
        write_only=True, 
        required=True, 
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True, 
        required=True,
        style={'input_type': 'password'}
    )
    
    class Meta:
        model = User
        fields = [
            'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'phone', 'role',
        ]
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': 'Passwords do not match.'
            })
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile."""
    
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'phone', 'avatar',
        ]


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for admin to update user details including role and permissions."""
    
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'phone', 'role', 'avatar',
            'is_active', 'can_access_pos', 'can_access_kitchen',
            'can_access_reports', 'can_manage_products', 'can_manage_users',
            'can_void_orders', 'can_apply_discounts', 'max_discount_percent',
        ]


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for password change."""
    
    old_password = serializers.CharField(
        required=True,
        style={'input_type': 'password'}
    )
    new_password = serializers.CharField(
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(
        required=True,
        style={'input_type': 'password'}
    )
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': 'New passwords do not match.'
            })
        return attrs
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Current password is incorrect.')
        return value


class SetPINSerializer(serializers.Serializer):
    """Serializer for setting quick login PIN."""
    
    pin_code = serializers.CharField(min_length=4, max_length=6)
    password = serializers.CharField(style={'input_type': 'password'})
    
    def validate_pin_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError('PIN must contain only digits.')
        return value
    
    def validate_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Password is incorrect.')
        return value


class PINLoginSerializer(serializers.Serializer):
    """Serializer for PIN-based login."""
    
    email = serializers.EmailField()
    pin_code = serializers.CharField(min_length=4, max_length=6)


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT token serializer with additional user data."""
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        # Add custom claims
        token['email'] = user.email
        token['role'] = user.role
        token['full_name'] = user.get_full_name()
        
        return token
    
    def validate(self, attrs):
        data = super().validate(attrs)
        
        # Add extra response data
        data['user'] = {
            'id': self.user.id,
            'email': self.user.email,
            'full_name': self.user.get_full_name(),
            'role': self.user.role,
            'permissions': {
                'can_access_pos': self.user.can_access_pos,
                'can_access_kitchen': self.user.can_access_kitchen,
                'can_access_reports': self.user.can_access_reports,
                'can_manage_products': self.user.can_manage_products,
                'can_manage_users': self.user.can_manage_users,
                'can_void_orders': self.user.can_void_orders,
                'can_apply_discounts': self.user.can_apply_discounts,
                'max_discount_percent': float(self.user.max_discount_percent),
            }
        }
        
        return data
