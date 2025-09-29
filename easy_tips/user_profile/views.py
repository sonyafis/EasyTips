from django.db.models import Count, Sum, Q
from django.db.models.functions import TruncMonth
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response
from auth_app.authentication import SessionAuthentication
from auth_app.permissions import IsAuthenticatedUserData
from auth_app.serializers import UserDataSerializer
from .payment_service import PaymentService
from .serializers import TipPaymentSerializer, WithdrawSerializer, TransactionSerializer
from django.conf import settings
from django.utils import timezone
from datetime import datetime, timedelta


# @api_view(['GET', 'PUT'])
# @authentication_classes([SessionAuthentication])
# @permission_classes([IsAuthenticated])
# def profile(request):
#     user_data = request.user

#     if request.method == 'GET':
#         serializer = UserDataSerializer(user_data)
#         return Response(serializer.data)

#     elif request.method == 'PUT':
#         serializer = UserDataSerializer(user_data, data=request.data, partial=True)
#         if serializer.is_valid():
#             serializer.save()
#             return Response({'message': 'Profile completed', 'user_data': serializer.data})
#         return Response(serializer.errors, status=400)


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
def get_qr_code(request):
    """
    Generate a QR code to redirect to the tip amount selection form.
    """
    amount = request.query_params.get('amount')
    if not amount:
        return Response({"error": "amount is required"}, status=400)

    qr_data = PaymentService.generate_qr_code(request.user, amount)
    return Response(qr_data)


@api_view(['POST'])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticatedUserData])
def payment_tips(request):
    """Processing tip payments"""
    serializer = TipPaymentSerializer(data=request.data)

    if not serializer.is_valid():
        return Response({'error': serializer.errors}, status=400)

    try:
        transaction = PaymentService.process_tip_payment(
            user=request.user,
            amount=serializer.validated_data['amount'],
            employee_rating=serializer.validated_data.get('employee_rating'),
            comment=serializer.validated_data.get('comment'),
            payment_method=serializer.validated_data['payment_method']
        )

        return Response({
            'success': True,
            'transaction_id': str(transaction.id),
            'redirect_url': f"{settings.FRONTEND_URL}/success-page"
        })

    except Exception as e:
        return Response({'error': str(e)}, status=400)


@api_view(['POST'])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticatedUserData])
def withdraw_tips(request):
    """withdrawal of funds"""
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
    """Getting balance"""
    return Response({
        'balance': float(request.user.balance),
        'currency': 'RUB'
    })


@api_view(['GET'])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticatedUserData])
def transaction_history(request):
    """Transaction history"""
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
            end_date = timezone.make_aware(end_date).replace(hour=23, minute=59, second=59, microsecond=999999)
            transactions = transactions.filter(created_at__lte=end_date)
        except ValueError:
            pass

    # Statistics
    total_tips = transactions.filter(transaction_type='tip').count()
    total_payouts = transactions.filter(transaction_type='payout').count()
    total_tips_amount = transactions.filter(transaction_type='tip').aggregate(Sum('amount'))['amount__sum'] or 0
    total_payouts_amount = transactions.filter(transaction_type='payout').aggregate(Sum('amount'))['amount__sum'] or 0

    # Statistics by month (last 6 months)
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

