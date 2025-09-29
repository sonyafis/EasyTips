import qrcode
import base64
from io import BytesIO
from django.conf import settings
from urllib.parse import urlencode
from .models import Transaction


class PaymentService:
    @staticmethod
    def generate_qr_code(user):
        FRONTEND_URL = getattr(settings, "FRONTEND_URL", "https://tips.yoursite.com")
        form_page_url = "/payment-form/"  # route React
        params = {'user_id': str(user.uuid)}

        payment_url = f"{FRONTEND_URL}{form_page_url}?{urlencode(params)}"

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4
        )
        qr.add_data(payment_url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        img_str = base64.b64encode(buffer.getvalue()).decode()

        return {
            # "qr_code": f"data:image/png;base64,{img_str}",
            "qr_code": f"{img_str}",
            "payment_url": payment_url
        }

    @staticmethod
    def process_tip_payment(user, amount, employee_rating=None, comment=None, payment_method='card'):
        """Processes tip payments"""
        transaction = Transaction.objects.create(
            user=user,
            transaction_type='tip',
            amount=amount,
            status='completed',
            employee_rating=employee_rating,
            comment=comment,
            payment_method=payment_method
        )

        # Updating a balance
        user.balance += amount
        user.save()

        return transaction

    @staticmethod
    def process_withdrawal(user, amount, withdraw_type, details):
        """Processing withdrawals"""
        if user.balance < amount:
            raise ValueError("Insufficient funds")

        transaction = Transaction.objects.create(
            user=user,
            transaction_type='payout',
            amount=amount,
            status='completed',
            payment_method=withdraw_type
        )

        user.balance -= amount
        user.save()

        return transaction