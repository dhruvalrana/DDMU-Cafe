"""
Custom User model and authentication-related models.
"""

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from apps.core.models import TimeStampedModel


class UserManager(BaseUserManager):
    """Custom user manager for the POS system."""
    
    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular User."""
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a SuperUser."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser, TimeStampedModel):
    """
    Custom User model for POS system.
    Uses email as the primary identifier instead of username.
    """
    
    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('manager', 'Manager'),
        ('staff', 'Staff'),
        ('kitchen', 'Kitchen Staff'),
        ('customer', 'Customer'),
    ]
    
    username = None  # Remove username field
    email = models.EmailField('Email Address', unique=True)
    phone = models.CharField(max_length=20, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='staff')
    pin_code = models.CharField(max_length=6, blank=True, help_text='Quick PIN for POS login')
    
    # Profile info
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    
    # Permissions
    can_access_pos = models.BooleanField(default=True)
    can_access_kitchen = models.BooleanField(default=False)
    can_access_reports = models.BooleanField(default=False)
    can_manage_products = models.BooleanField(default=False)
    can_manage_users = models.BooleanField(default=False)
    can_void_orders = models.BooleanField(default=False)
    can_apply_discounts = models.BooleanField(default=False)
    max_discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    objects = UserManager()
    
    class Meta:
        db_table = 'pos_users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.email})"
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.email
    
    @property
    def is_admin(self):
        return self.role == 'admin'
    
    @property
    def is_manager(self):
        return self.role in ['admin', 'manager']
    
    @property
    def is_kitchen_staff(self):
        return self.role in ['admin', 'manager', 'kitchen']
    
    def set_role_permissions(self):
        """Set default permissions based on role."""
        if self.role == 'admin':
            self.is_staff = True
            self.is_superuser = True
            self.can_access_pos = True
            self.can_access_kitchen = True
            self.can_access_reports = True
            self.can_manage_products = True
            self.can_manage_users = True
            self.can_void_orders = True
            self.can_apply_discounts = True
            self.max_discount_percent = 100
        elif self.role == 'manager':
            self.can_access_pos = True
            self.can_access_kitchen = True
            self.can_access_reports = True
            self.can_manage_products = True
            self.can_void_orders = True
            self.can_apply_discounts = True
            self.max_discount_percent = 50
        elif self.role == 'staff':
            self.can_access_pos = True
            self.can_apply_discounts = True
            self.max_discount_percent = 10
        elif self.role == 'kitchen':
            self.can_access_pos = False
            self.can_access_kitchen = True
        elif self.role == 'customer':
            self.can_access_pos = False
            self.can_access_kitchen = False
    
    def save(self, *args, **kwargs):
        if not self.pk:  # New user
            self.set_role_permissions()
        super().save(*args, **kwargs)


class UserSession(TimeStampedModel):
    """
    Track user login sessions for security and audit.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    token_jti = models.CharField(max_length=255, unique=True)  # JWT token ID
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    last_activity = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField()
    
    class Meta:
        db_table = 'pos_user_sessions'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.created_at}"
