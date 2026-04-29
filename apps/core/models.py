"""
Base models for the POS system.
Provides common fields and methods for all models.
"""

import uuid
from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    """
    Abstract base model with created and updated timestamps.
    """
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ['-created_at']


class UUIDModel(models.Model):
    """
    Abstract base model with UUID primary key.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    """
    Abstract base model for soft delete functionality.
    """
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    def soft_delete(self):
        """Mark record as deleted without actual deletion."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_deleted', 'deleted_at'])

    def restore(self):
        """Restore a soft-deleted record."""
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=['is_deleted', 'deleted_at'])


class ActiveManager(models.Manager):
    """Manager that returns only active (non-deleted) records."""
    
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class BaseModel(UUIDModel, TimeStampedModel, SoftDeleteModel):
    """
    Complete base model combining UUID, timestamps, and soft delete.
    Use this as the base for most POS models.
    """
    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True


class EnableableModel(models.Model):
    """
    Abstract model for entities that can be enabled/disabled.
    """
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        abstract = True

    def enable(self):
        """Enable this record."""
        self.is_active = True
        self.save(update_fields=['is_active'])

    def disable(self):
        """Disable this record."""
        self.is_active = False
        self.save(update_fields=['is_active'])


class SystemSettings(models.Model):
    """
    Singleton model for storing system-wide settings.
    Only one record should exist in the database.
    """
    # Restaurant Information
    restaurant_name = models.CharField(max_length=200, default='Odoo Cafe')
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    
    # Tax Settings
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=5.00)
    tax_name = models.CharField(max_length=50, default='GST')
    tax_number = models.CharField(max_length=50, blank=True)
    
    # Receipt Settings
    receipt_header = models.TextField(blank=True)
    receipt_footer = models.TextField(default='Thank you for dining with us!')
    print_auto = models.BooleanField(default=False)
    
    # Timestamps
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'pos_system_settings'
        verbose_name = 'System Settings'
        verbose_name_plural = 'System Settings'
    
    def save(self, *args, **kwargs):
        """Ensure only one settings record exists."""
        if not self.pk and SystemSettings.objects.exists():
            # Update existing record instead of creating new one
            existing = SystemSettings.objects.first()
            self.pk = existing.pk
        super().save(*args, **kwargs)
    
    @classmethod
    def get_settings(cls):
        """Get or create the singleton settings instance."""
        settings, created = cls.objects.get_or_create(pk=1)
        return settings
    
    def __str__(self):
        return f"System Settings - {self.restaurant_name}"

