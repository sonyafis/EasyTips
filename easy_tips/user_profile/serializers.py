from decimal import Decimal

from rest_framework import serializers
from .models import Transaction


class TransactionSerializer(serializers.ModelSerializer):
    created_at_formatted = serializers.SerializerMethodField()
    transaction_type_display = serializers.SerializerMethodField()
    employee_name = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = [
            'id', 'transaction_type', 'transaction_type_display', 'amount',
            'status', 'employee_rating', 'comment', 'payment_method',
            'created_at', 'created_at_formatted'
            'created_at', 'created_at_formatted', 'employee_name', 'guest_session_id']

    def get_created_at_formatted(self, obj):
        return obj.created_at.strftime('%d.%m.%Y %H:%M')

    def get_transaction_type_display(self, obj):
        return dict(Transaction.TRANSACTION_TYPES).get(obj.transaction_type, obj.transaction_type)

class TipPaymentSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('1.00'))
    employee_rating = serializers.IntegerField(min_value=1, max_value=5, required=False)
    comment = serializers.CharField(required=False, allow_blank=True)
    payment_method = serializers.ChoiceField(choices=['card', 'phone'])
    def get_employee_name(self, obj):
        return obj.employee.name if obj.employee else None


class GuestTipPaymentSerializer(serializers.Serializer):
    employee_id = serializers.UUIDField(help_text="Employee UUID")
    amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal('0.50'),
        help_text="Tip amount (minimum 50 cents)"
    )
    employee_rating = serializers.IntegerField(
        min_value=1,
        max_value=5,
        required=False,
        allow_null=True,
        help_text="Employee rating (1-5)"
    )
    comment = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500,
        help_text="Payment comment"
    )
    guest_session_id = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Guest session identifier"
    )

class EmployeeQRCodeSerializer(serializers.Serializer):
    qr_code = serializers.CharField(help_text="Base64 encoded QR code")
    form_url = serializers.URLField(help_text="URL of the payment form")


class CheckoutSessionResponseSerializer(serializers.Serializer):
    session_id = serializers.CharField(help_text="Checkout session ID")
    url = serializers.URLField(help_text="URL to redirect for payment")
    transaction_id = serializers.CharField(help_text="Transaction ID")

class WithdrawSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('1.00'))
    withdraw_type = serializers.ChoiceField(choices=['phone', 'card'])
    details = serializers.JSONField()
