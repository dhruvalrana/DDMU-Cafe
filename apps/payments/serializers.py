"""
Serializers for payment management.
"""

from django.db import models
from rest_framework import serializers
from .models import (
    PaymentMethod,
    UPIConfiguration,
    CardConfiguration,
    Payment,
    PaymentRefund,
)
from apps.core.utils import generate_upi_qr


class UPIConfigurationSerializer(serializers.ModelSerializer):
    """Serializer for UPI configuration."""
    
    class Meta:
        model = UPIConfiguration
        fields = [
            'id', 'upi_id', 'merchant_name', 'merchant_code',
            'qr_box_size', 'qr_border', 'auto_verify', 'verification_timeout',
        ]
        read_only_fields = ['id']


class CardConfigurationSerializer(serializers.ModelSerializer):
    """Serializer for Card configuration."""
    
    class Meta:
        model = CardConfiguration
        fields = [
            'id', 'terminal_id', 'merchant_id',
            'accept_visa', 'accept_mastercard', 'accept_amex', 'accept_rupay',
        ]
        read_only_fields = ['id']


class PaymentMethodSerializer(serializers.ModelSerializer):
    """Serializer for PaymentMethod."""
    
    upi_config = UPIConfigurationSerializer(read_only=True)
    card_config = CardConfigurationSerializer(read_only=True)
    
    class Meta:
        model = PaymentMethod
        fields = [
            'id', 'name', 'method_type', 'description', 'icon',
            'display_order', 'is_active', 'is_default', 'requires_verification',
            'allows_change', 'min_amount', 'max_amount',
            'upi_config', 'card_config', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class PaymentMethodCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating PaymentMethod with configuration."""
    
    upi_config = UPIConfigurationSerializer(required=False)
    card_config = CardConfigurationSerializer(required=False)
    
    class Meta:
        model = PaymentMethod
        fields = [
            'name', 'method_type', 'description', 'icon',
            'display_order', 'is_active', 'is_default', 'requires_verification',
            'allows_change', 'min_amount', 'max_amount',
            'upi_config', 'card_config',
        ]
    
    def create(self, validated_data):
        upi_config_data = validated_data.pop('upi_config', None)
        card_config_data = validated_data.pop('card_config', None)
        
        payment_method = PaymentMethod.objects.create(**validated_data)
        
        if upi_config_data and validated_data.get('method_type') == 'upi':
            UPIConfiguration.objects.create(
                payment_method=payment_method,
                **upi_config_data
            )
        
        if card_config_data and validated_data.get('method_type') == 'card':
            CardConfiguration.objects.create(
                payment_method=payment_method,
                **card_config_data
            )
        
        return payment_method
    
    def update(self, instance, validated_data):
        upi_config_data = validated_data.pop('upi_config', None)
        card_config_data = validated_data.pop('card_config', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        if upi_config_data:
            UPIConfiguration.objects.update_or_create(
                payment_method=instance,
                defaults=upi_config_data
            )
        
        if card_config_data:
            CardConfiguration.objects.update_or_create(
                payment_method=instance,
                defaults=card_config_data
            )
        
        return instance


class PaymentSerializer(serializers.ModelSerializer):
    """Serializer for Payment."""
    
    payment_method_name = serializers.CharField(source='payment_method.name', read_only=True)
    processed_by_name = serializers.CharField(source='processed_by.get_full_name', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id', 'order', 'payment_method', 'payment_method_name',
            'amount', 'amount_received', 'change_amount', 'status',
            'transaction_id', 'reference_number',
            'card_last_four', 'card_type', 'upi_transaction_id',
            'notes', 'processed_by', 'processed_by_name', 'processed_at',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'processed_at']


class PaymentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a payment."""
    
    class Meta:
        model = Payment
        fields = [
            'order', 'payment_method', 'amount', 'amount_received',
            'transaction_id', 'reference_number', 'notes',
        ]
    
    def validate(self, attrs):
        payment_method = attrs['payment_method']
        amount = attrs['amount']
        
        if not payment_method.is_active:
            raise serializers.ValidationError({
                'payment_method': 'This payment method is not available.'
            })
        
        if amount < payment_method.min_amount:
            raise serializers.ValidationError({
                'amount': f'Minimum amount for this method is {payment_method.min_amount}'
            })
        
        if payment_method.max_amount and amount > payment_method.max_amount:
            raise serializers.ValidationError({
                'amount': f'Maximum amount for this method is {payment_method.max_amount}'
            })
        
        return attrs
    
    def create(self, validated_data):
        from django.utils import timezone
        payment_method = validated_data['payment_method']
        amount_received = validated_data.get('amount_received', validated_data['amount'])
        
        # Calculate change for cash payments
        if payment_method.allows_change and amount_received > validated_data['amount']:
            validated_data['change_amount'] = amount_received - validated_data['amount']
        
        validated_data['amount_received'] = amount_received
        validated_data['processed_by'] = self.context['request'].user
        
        # Automatically set as completed and processed
        validated_data['status'] = 'completed'
        validated_data['processed_at'] = timezone.now()
        
        payment = super().create(validated_data)
        
        # Update order status to paid if fully paid
        order = payment.order
        total_paid = order.payments.filter(status='completed').aggregate(
            total=models.Sum('amount')
        )['total'] or 0
        
        if total_paid >= order.total_amount:
            order.status = 'paid'
            order.paid_at = timezone.now()
            order.save(update_fields=['status', 'paid_at'])
        
        return payment


class UPIQRSerializer(serializers.Serializer):
    """Serializer for generating UPI QR code."""
    
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    order_id = serializers.UUIDField(required=False)
    upi_id = serializers.CharField(required=False)
    merchant_name = serializers.CharField(required=False)
    payment_ref = serializers.CharField(required=False, max_length=50)
    
    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('Amount must be greater than 0')
        return value
    
    def create(self, validated_data):
        """Generate QR code data."""
        return generate_upi_qr(
            amount=validated_data['amount'],
            upi_id=validated_data.get('upi_id'),
            merchant_name=validated_data.get('merchant_name'),
            order_id=validated_data.get('order_id'),
        )


class PaymentRefundSerializer(serializers.ModelSerializer):
    """Serializer for payment refunds."""
    
    class Meta:
        model = PaymentRefund
        fields = [
            'id', 'payment', 'amount', 'reason', 'notes',
            'processed_by', 'refund_transaction_id', 'created_at',
        ]
        read_only_fields = ['id', 'processed_by', 'created_at']
    
    def validate(self, attrs):
        payment = attrs['payment']
        refund_amount = attrs['amount']
        
        # Calculate already refunded amount
        existing_refunds = payment.refunds.aggregate(
            total=models.Sum('amount')
        )['total'] or 0
        
        available_for_refund = payment.amount - existing_refunds
        
        if refund_amount > available_for_refund:
            raise serializers.ValidationError({
                'amount': f'Maximum refundable amount is {available_for_refund}'
            })
        
        return attrs
    
    def create(self, validated_data):
        validated_data['processed_by'] = self.context['request'].user
        refund = super().create(validated_data)
        
        # Update payment status if fully refunded
        payment = refund.payment
        total_refunded = payment.refunds.aggregate(
            total=models.Sum('amount')
        )['total'] or 0
        
        if total_refunded >= payment.amount:
            payment.refund()
        
        return refund


class ConfirmUPIPaymentSerializer(serializers.Serializer):
    """Serializer for confirming UPI payment."""
    
    order_id = serializers.UUIDField()
    upi_transaction_id = serializers.CharField(max_length=100)
    
    def validate_upi_transaction_id(self, value):
        if len(value) < 5:
            raise serializers.ValidationError('Invalid UPI transaction ID')
        return value
