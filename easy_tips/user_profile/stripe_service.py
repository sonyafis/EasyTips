import stripe
from stripe import StripeError, SignatureVerificationError
from django.conf import settings
from django.core.exceptions import ValidationError
from .models import UserData

stripe.api_key = settings.STRIPE_SECRET_KEY

class StripeService:
    @staticmethod
    def create_customer(user_data: UserData) -> str:
        """Creates a customer in Stripe"""
        try:
            customer = stripe.Customer.create(
                email=user_data.email,
                phone=user_data.phone_number,
                name=user_data.name,
                metadata={
                    'user_uuid': str(user_data.uuid),
                    'user_type': user_data.user_type
                }
            )

            user_data.stripe_customer_id = customer.id
            user_data.save(update_fields=['stripe_customer_id'])

            return customer.id
        except StripeError as e:
            raise ValidationError(f"Stripe error: {str(e)}")
        except Exception as e:
            raise ValidationError(f"Error creating customer: {str(e)}")

    @staticmethod
    def create_payment_intent(
            amount: float,
            currency: str = None,
            customer_id: str = None,
            metadata: dict = None,
            description: str = None
    ) -> dict:
        """Creates a PaymentIntent for processing a payment"""
        try:
            if currency is None:
                currency = settings.DEFAULT_CURRENCY

            intent = stripe.PaymentIntent.create(
                amount=int(amount * 100),
                currency=currency,
                customer=customer_id,
                automatic_payment_methods={
                    'enabled': True,
                },
                metadata=metadata or {},
                description=description
            )

            return {
                'client_secret': intent.client_secret,
                'payment_intent_id': intent.id,
                'status': intent.status,
                'amount': intent.amount / 100,
                'currency': intent.currency
            }
        except StripeError as e:
            raise ValidationError(f"Stripe error: {str(e)}")
        except Exception as e:
            raise ValidationError(f"Error creating payment intent: {str(e)}")

    @staticmethod
    def create_checkout_session(
            amount: float,
            currency: str = None,
            customer_id: str = None,
            metadata: dict = None,
            success_url: str = None,
            cancel_url: str = None,
            description: str = None
    ) -> dict:
        """Creates a Stripe Checkout Session for redirecting the user"""
        try:
            if currency is None:
                currency = settings.DEFAULT_CURRENCY

            session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': currency,
                        'product_data': {
                            'name': 'Tip',
                            'description': description or 'Tip payment',
                        },
                        'unit_amount': int(amount * 100),
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=success_url,
                cancel_url=cancel_url,
                metadata=metadata or {},
            )

            return {
                'session_id': session.id,
                'url': session.url,
                'payment_intent_id': session.payment_intent
            }
        except StripeError as e:
            raise ValidationError(f"Stripe error: {str(e)}")
        except Exception as e:
            raise ValidationError(f"Error creating checkout session: {str(e)}")

    @staticmethod
    def confirm_payment_intent(payment_intent_id: str) -> dict:
        """Confirms a payment"""
        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            return {
                'status': intent.status,
                'amount': intent.amount / 100,
                'currency': intent.currency
            }
        except StripeError as e:
            raise ValidationError(f"Stripe error: {str(e)}")
        except Exception as e:
            raise ValidationError(f"Error confirming payment: {str(e)}")

    @staticmethod
    def verify_webhook_signature(payload: bytes, sig_header: str) -> dict:
        """Verifies the webhook signature"""
        try:
            return stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except ValueError as e:
            raise ValidationError(f"Invalid payload: {str(e)}")
        except SignatureVerificationError as e:
            raise ValidationError(f"Invalid signature: {str(e)}")
        except Exception as e:
            raise ValidationError(f"Webhook error: {str(e)}")