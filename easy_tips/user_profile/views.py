from django.conf import settings
from django.db.models import Count, Sum, Q
from django.db.models.functions import TruncMonth
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import datetime, timedelta

from auth_app.authentication import SessionAuthentication
from auth_app.models import UserData
from auth_app.permissions import IsAuthenticatedUserData
from auth_app.serializers import UserDataSerializer
from .models import Transaction
from .payment_service import PaymentService
from .serializers import (
    TipPaymentSerializer,
    WithdrawSerializer,
    TransactionSerializer,
    EmployeeQRCodeSerializer,
    CheckoutSessionResponseSerializer,
    GuestTipPaymentSerializer, OrganizationStatisticsSerializer
)
from .stripe_service import StripeService


@api_view(['GET', 'PUT'])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticatedUserData])
def profile(request):
    """User Profile Management"""
    user_data = request.user

    if request.method == 'GET':
        serializer = UserDataSerializer(user_data)
        return Response(serializer.data)

    elif request.method == 'PUT':
        serializer = UserDataSerializer(user_data, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)


@api_view(['GET'])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticatedUserData])
def get_employee_qr_code(request):
    """Returns a QR code for the employee that leads to the tip payment form"""
    if request.user.user_type != 'employee':
        return Response(
            {'error': 'Only employees can generate tip QR codes'},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        qr_data = PaymentService.get_employee_qr_code(str(request.user.uuid))

        serializer = EmployeeQRCodeSerializer({
            'qr_code': qr_data['qr_code'],
            'form_url': qr_data['payment_url']
        })

        return Response({
            'success': True,
            'employee': {
                'uuid': str(request.user.uuid),
                'name': request.user.name,
                'phone_number': request.user.phone_number
            },
            'qr_data': serializer.data
        })

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def create_guest_tip_payment(request):
    """Creates a tip payment from a guest to an employee (no auth required)"""
    serializer = GuestTipPaymentSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    try:
        employee_id = serializer.validated_data['employee_id']
        amount = serializer.validated_data['amount']
        employee_rating = serializer.validated_data.get('employee_rating')
        comment = serializer.validated_data.get('comment')
        guest_session_id = serializer.validated_data.get('guest_session_id')

        result = PaymentService.create_guest_tip_payment(
            employee_uuid=employee_id,
            amount=amount,
            employee_rating=employee_rating,
            comment=comment,
            guest_session_id=guest_session_id
        )

        response_serializer = CheckoutSessionResponseSerializer({
            'session_id': result['session_id'],
            'url': result['url'],
            'transaction_id': result['transaction_id']
        })

        return Response({
            'success': True,
            'checkout_data': response_serializer.data
        })

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_employee_info(request, employee_uuid):
    """Returns employee information for the payment form (no auth required)"""
    try:
        employee = UserData.objects.get(uuid=employee_uuid, user_type='employee')
        return Response({
            'success': True,
            'employee': {
                'uuid': str(employee.uuid),
                'name': employee.name,
                'phone_number': employee.phone_number,
                'avatar_url': employee.avatar_url
            }
        })
    except UserData.DoesNotExist:
        return Response({'error': 'Employee not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@csrf_exempt
@permission_classes([AllowAny])
def stripe_webhook(request):
    """Handles Stripe webhooks"""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')

    try:
        event = StripeService.verify_webhook_signature(payload, sig_header)
    except Exception as e:
        print(f"❌ Webhook verification failed: {str(e)}")
        return Response({'error': str(e)}, status=400)

    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']

        transaction = PaymentService.confirm_tip_payment(payment_intent['id'])
        if transaction:
            print(f"✅ Transaction {transaction.id} confirmed successfully")
        else:
            print(f"❌ Failed to confirm transaction for payment intent {payment_intent['id']}")

    elif event['type'] == 'checkout.session.completed':
        session = event['data']['object']

        try:
            transaction = Transaction.objects.get(stripe_checkout_session_id=session['id'])
            print(f"📄 Found transaction by checkout_session_id: {transaction.id}")

            if session.get('payment_intent'):
                transaction.stripe_payment_intent_id = session['payment_intent']
                transaction.save(update_fields=['stripe_payment_intent_id'])
                print(f"📝 Updated transaction {transaction.id} with payment_intent: {session['payment_intent']}")

            transaction = PaymentService.confirm_tip_payment(session['payment_intent'])
            if transaction:
                print(f"✅ Transaction {transaction.id} confirmed from session")
            else:
                print(f"❌ Failed to confirm transaction from session {session['id']}")

        except Transaction.DoesNotExist:
            print(f"❌ Transaction not found for checkout_session_id {session['id']}")
            metadata = session.get('metadata', {})
            transaction_id = metadata.get('transaction_id')
            if transaction_id:
                try:
                    transaction = Transaction.objects.get(id=transaction_id)
                    print(f"📄 Found transaction by metadata transaction_id: {transaction.id}")

                    transaction.stripe_checkout_session_id = session['id']
                    if session.get('payment_intent'):
                        transaction.stripe_payment_intent_id = session['payment_intent']
                    transaction.save()

                    if session.get('payment_intent'):
                        transaction = PaymentService.confirm_tip_payment(session['payment_intent'])
                        if transaction:
                            print(f"✅ Transaction {transaction.id} confirmed from metadata")

                except Transaction.DoesNotExist:
                    print(f"❌ Transaction not found by metadata either: {transaction_id}")

    elif event['type'] == 'charge.succeeded':
        charge = event['data']['object']

        if charge.get('payment_intent'):
            transaction = PaymentService.confirm_tip_payment(charge['payment_intent'])
            if transaction:
                print(f"✅ Transaction {transaction.id} confirmed from charge")
            else:
                print(f"❌ Failed to confirm transaction from charge {charge['id']}")

    elif event['type'] == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        print(f"❌ Payment failed: {payment_intent['id']}")

        try:
            transaction = Transaction.objects.get(stripe_payment_intent_id=payment_intent['id'])
            transaction.status = 'failed'
            transaction.save(update_fields=['status'])
            print(f"📝 Transaction {transaction.id} marked as failed")
        except Transaction.DoesNotExist:
            print(f"⚠️ Transaction not found for failed payment intent {payment_intent['id']}")

    else:
        print(f"ℹ️ Unhandled event type: {event['type']}")

    return Response({'success': True})


@api_view(['POST'])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticatedUserData])
def withdraw_tips(request):
    """Withdraw funds by an employee"""
    serializer = WithdrawSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'error': serializer.errors}, status=400)

    try:
        transaction = PaymentService.process_withdrawal(
            user=request.user,
            amount=serializer.validated_data['amount'],
            withdraw_type=serializer.validated_data['withdraw_type'],
            details=serializer.validated_data['details']
        )

        return Response({
            'success': True,
            'transaction_id': str(transaction.id),
            'new_balance': float(request.user.balance),
            'message': 'Withdrawal request sent',
            'redirect_url': f"{settings.FRONTEND_URL}/success-page_withdrawal"
        })
    except ValueError as e:
        return Response({'error': str(e)}, status=400)
    except Exception as e:
        return Response({'error': 'Error while withdrawing funds'}, status=500)


@api_view(['GET'])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticatedUserData])
def get_balance(request):
    """Get employee balance"""
    return Response({
        'balance': float(request.user.balance),
        'currency': 'RUB'
    })


@api_view(['GET'])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticatedUserData])
def transaction_history(request):
    """Transaction history"""
    if request.user.user_type == 'employee':
        transactions = request.user.received_tips.all().order_by('-created_at')[:50]
    else:
        transactions = request.user.transactions.all().order_by('-created_at')[:50]

    serializer = TransactionSerializer(transactions, many=True)
    return Response({
        'transactions': serializer.data,
        'total_count': transactions.count()
    })


@api_view(['GET'])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticatedUserData])
def transaction_statistics(request):
    """Transaction statistics for the period"""
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    transactions = request.user.transactions.all()

    # Filter by date
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            start_date = timezone.make_aware(start_date)
            transactions = transactions.filter(created_at__gte=start_date)
        except ValueError:
            pass

    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            end_date = timezone.make_aware(end_date).replace(
                hour=23, minute=59, second=59, microsecond=999999)
            transactions = transactions.filter(created_at__lte=end_date)
        except ValueError:
            pass

    # Summary
    total_tips = transactions.filter(transaction_type='tip').count()
    total_payouts = transactions.filter(transaction_type='payout').count()
    total_tips_amount = transactions.filter(transaction_type='tip').aggregate(Sum('amount'))['amount__sum'] or 0
    total_payouts_amount = transactions.filter(transaction_type='payout').aggregate(Sum('amount'))['amount__sum'] or 0

    # Monthly statistics (last 6 months)
    six_months_ago = timezone.now() - timedelta(days=180)
    monthly_stats = (
        transactions.filter(created_at__gte=six_months_ago)
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(
            tips_count=Count('id', filter=Q(transaction_type='tip')),
            tips_amount=Sum('amount', filter=Q(transaction_type='tip')),
            payouts_count=Count('id', filter=Q(transaction_type='payout')),
            payouts_amount=Sum('amount', filter=Q(transaction_type='payout')),
        )
        .order_by('month')
    )

    return Response({
        'success': True,
        'data': {
            'period': {
                'start_date': start_date_str,
                'end_date': end_date_str
            },
            'summary': {
                'total_transactions': transactions.count(),
                'tips_count': total_tips,
                'payouts_count': total_payouts,
                'tips_amount': float(total_tips_amount),
                'payouts_amount': float(total_payouts_amount),
                'net_income': float(total_tips_amount - total_payouts_amount)
            },
            'monthly_stats': list(monthly_stats)
        }
    })


import logging

logger = logging.getLogger(__name__)


@api_view(['GET'])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticatedUserData])
def organization_statistics(request):
    """Статистика для организации"""
    logger.info(f"Organization statistics requested by user: {request.user.uuid}, type: {request.user.user_type}")

    if request.user.user_type != 'organization':
        logger.warning(f"User {request.user.uuid} is not an organization")
        return Response(
            {'error': 'Only organizations can access this endpoint'},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        logger.info(f"Getting statistics for organization: {request.user.uuid}")
        statistics = PaymentService.get_organization_statistics(str(request.user.uuid))
        logger.info(f"Statistics retrieved successfully: {statistics}")

        return Response({
            'success': True,
            'statistics': statistics
        })

    except ValidationError as e:
        logger.error(f"Validation error in organization statistics: {str(e)}")
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Unexpected error in organization statistics: {str(e)}", exc_info=True)
        return Response(
            {'error': 'Error retrieving organization statistics'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )