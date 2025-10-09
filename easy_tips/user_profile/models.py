import uuid
from django.db import models
from auth_app.models import UserData

class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('tip', 'Чаевые'),
        ('payout', 'Вывод средств'),
    ]

    STATUS_CHOICES = [
        ('pending', 'В обработке'),
        ('completed', 'Завершено'),
        ('failed', 'Ошибка'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(UserData, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    employee_rating = models.IntegerField(null=True, blank=True)
    comment = models.TextField(blank=True, null=True)
    payment_method = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_transfer_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_charge_id = models.CharField(max_length=255, blank=True, null=True)
    guest_session_id = models.CharField(max_length=255, blank=True, null=True)
    employee = models.ForeignKey(
        UserData,
        on_delete=models.CASCADE,
        related_name='received_tips',
        null=True,
        blank=True,
        help_text="The employee to whom the tip is intended"
    )

    def __str__(self):
        return f"{self.transaction_type} - {self.amount} - {self.status}"