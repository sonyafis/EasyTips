from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response
from auth_app.authentication import SessionAuthentication
from auth_app.permissions import IsAuthenticatedUserData
from auth_app.serializers import UserDataSerializer
from .payment_service import PaymentService
from .serializers import TipPaymentSerializer, WithdrawSerializer, TransactionSerializer
from django.conf import settings


@api_view(['GET', 'PUT'])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def profile(request):
    user_data = request.user

    if request.method == 'GET':
        serializer = UserDataSerializer(user_data)
        return Response(serializer.data)

    elif request.method == 'PUT':
        serializer = UserDataSerializer(user_data, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Profile completed', 'user_data': serializer.data})
        return Response(serializer.errors, status=400)


@api_view(['GET', 'PUT'])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticatedUserData])
def profile(request):
    """Управление профилем пользователя"""
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
    Генерация QR-кода для перехода на форму выбора суммы чаевых.
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
    """Обработка платежа чаевых"""
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
            'new_balance': float(request.user.balance),
            'redirect_url': f"{settings.FRONTEND_URL}/success-page"
        })

    except Exception as e:
        return Response({'error': str(e)}, status=400)


@api_view(['POST'])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticatedUserData])
def withdraw_tips(request):
    """Вывод средств"""
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
            'message': 'Запрос на вывод средств отправлен'
        })

    except ValueError as e:
        return Response({'error': str(e)}, status=400)
    except Exception as e:
        return Response({'error': 'Ошибка при выводе средств'}, status=500)


@api_view(['GET'])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticatedUserData])
def get_balance(request):
    """Получение баланса"""
    return Response({
        'balance': float(request.user.balance),
        'currency': 'RUB'
    })


@api_view(['GET'])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticatedUserData])
def transaction_history(request):
    """История транзакций"""
    transactions = request.user.transactions.all().order_by('-created_at')[:50]  # Ограничиваем вывод
    serializer = TransactionSerializer(transactions, many=True)

    return Response({
        'transactions': serializer.data,
        'total_count': transactions.count()
    })
