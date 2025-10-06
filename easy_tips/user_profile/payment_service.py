import qrcode
import base64
from io import BytesIO
from django.conf import settings
from urllib.parse import urlencode
from django.core.exceptions import ValidationError
from .models import Transaction, UserData
from .stripe_service import StripeService


class PaymentService:
    @staticmethod
    def generate_employee_qr_code(employee_uuid: str):
        """Generates a QR code for the employee that leads to the payment form"""
        FRONTEND_URL = getattr(settings, "FRONTEND_URL", "http://194.87.202.132:3000/")
        form_url = f"{FRONTEND_URL}/tip-form/?employee_id={employee_uuid}"

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4
        )
        qr.add_data(form_url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        img_str = base64.b64encode(buffer.getvalue()).decode()

        return {
            "qr_code": f"data:image/png;base64,{img_str}",
            "payment_url": form_url
        }

    @staticmethod
    def create_guest_tip_payment(
            employee_uuid: str,
            amount: float,
            employee_rating: int = None,
            comment: str = None,
            guest_session_id: str = None
    ):
        """Creates a tip payment from a guest to an employee"""
        try:
            employee = UserData.objects.get(uuid=employee_uuid, user_type='employee')
        except UserData.DoesNotExist:
            raise ValidationError("Employee not found")

        # Create a Stripe customer for the employee if not exists
        if not employee.stripe_customer_id:
            StripeService.create_customer(employee)

        description = f"Tip for {employee.name}"
        if employee_rating:
            description += f" (Rating: {employee_rating}/5)"
        if comment:
            description += f" - {comment[:50]}..."

        metadata = {
            'employee_uuid': str(employee.uuid),
            'transaction_type': 'tip',
            'employee_rating': str(employee_rating) if employee_rating else '',
            'comment': comment or '',
            'guest_session_id': guest_session_id or '',
            'payment_type': 'guest_tip'
        }

        success_url = f"{settings.FRONTEND_URL}/payment/success?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{settings.FRONTEND_URL}/payment/cancel"

        checkout_session = StripeService.create_checkout_session(
            amount=amount,
            customer_id=employee.stripe_customer_id,
            metadata=metadata,
            description=description,
            success_url=success_url,
            cancel_url=cancel_url
        )

        transaction = Transaction.objects.create(
            user=employee,
            transaction_type='tip',
            amount=amount,
            status='pending',
            employee_rating=employee_rating,
            comment=comment,
            payment_method='card',
            stripe_payment_intent_id=checkout_session['payment_intent_id'],
            guest_session_id=guest_session_id,
            employee=employee
        )

        return {
            'session_id': checkout_session['session_id'],
            'url': checkout_session['url'],
            'payment_intent_id': checkout_session['payment_intent_id'],
            'transaction_id': str(transaction.id)
        }

    @staticmethod
    def confirm_tip_payment(payment_intent_id):
        """Confirms a successful payment and updates the balance"""
        try:
            transaction = Transaction.objects.get(stripe_payment_intent_id=payment_intent_id)
            transaction.status = 'completed'
            transaction.save(update_fields=['status'])

            employee = transaction.employee
            employee.balance += transaction.amount
            employee.save(update_fields=['balance'])

            return transaction
        except Transaction.DoesNotExist:
            return None

    @staticmethod
    def process_tip_payment(user, amount, employee_rating=None, comment=None, payment_method='card'):
        """Direct processing of payments (without Stripe). Can be used for internal operations or testing"""
        transaction = Transaction.objects.create(
            user=user,
            transaction_type='tip',
            amount=amount,
            status='completed',
            employee_rating=employee_rating,
            comment=comment,
            payment_method=payment_method,
            employee=user
        )

        user.balance += amount
        user.save()

        return transaction

    @staticmethod
    def process_withdrawal(user, amount, withdraw_type, details):
        """Processes withdrawals. Will be integrated with Stripe Connect in the future"""
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

    @staticmethod
    def get_employee_balance(employee_uuid: str):
        """Gets the employee's balance"""
        try:
            employee = UserData.objects.get(uuid=employee_uuid, user_type='employee')
            return employee.balance
        except UserData.DoesNotExist:
            raise ValidationError("Employee not found")

    @staticmethod
    def get_employee_transactions(employee_uuid: str, limit=50):
        """Gets the employee's transaction history"""
        try:
            employee = UserData.objects.get(uuid=employee_uuid, user_type='employee')
            transactions = Transaction.objects.filter(employee=employee).order_by('-created_at')[:limit]
            return transactions
        except UserData.DoesNotExist:
            raise ValidationError("Employee not found")

    @staticmethod
    def get_employee_qr_code(employee_uuid: str):
        """Returns a QR code for the employee"""
        return PaymentService.generate_employee_qr_code(employee_uuid)