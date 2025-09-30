from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.core.cache import cache
from .services import AuthService
from .models import Session
from .serializers import UserDataSerializer
from .permissions import IsAuthenticatedUserData
import re

PHONE_REGEX = re.compile(r'^\+?\d{10,15}$')

@api_view(['POST'])
@permission_classes([AllowAny])
def send_code(request):
    phone_number = request.data.get('phone_number')

    if not phone_number:
        return Response(
            {'error': 'Phone number is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if not PHONE_REGEX.match(phone_number):
        return Response(
            {'error': 'Invalid phone number format. '
                      'Use international format, e.g. +1234567890'},
            status=status.HTTP_400_BAD_REQUEST
        )

    cache.delete(f"verification_attempts_{phone_number}")

    # Send the code
    AuthService.send_verification_code(phone_number)

    return Response({'message': 'Verification code sent'})


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_code(request):
    phone_number = request.data.get('phone_number')
    code = request.data.get('code')

    if not all([phone_number, code]):
        return Response(
            {'error': 'Phone number and code are required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if not AuthService.verify_code(phone_number, code):
        return Response(
            {'error': 'Invalid verification code'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Getting or creating a user
    user_data, created = AuthService.get_or_create_user(phone_number)

    # Create a session
    session = AuthService.create_session(user_data)

    # Deactivate previous sessions
    Session.objects.filter(
        user_data=user_data,
        is_active=True
    ).exclude(uuid=session.uuid).update(is_active=False)

    user_serializer = UserDataSerializer(user_data)

    response_data = {
        'session_id': str(session.uuid),
        'user_data': user_serializer.data,
        'created': created,
        'profile_complete': user_data.is_profile_complete
    }

    return Response(response_data)


@api_view(['POST'])
@permission_classes([IsAuthenticatedUserData])
def complete_profile(request):
    """
    Filling out a new user profile
    """
    user_data = request.user

    if user_data.is_profile_complete:
        return Response(
            {'error': 'Profile already completed'},
            status=status.HTTP_400_BAD_REQUEST
        )

    serializer = UserDataSerializer(user_data, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response({
            'success': True,
            'profile_complete': user_data.is_profile_complete,
            'user_data': serializer.data,
            'message': 'Profile updated successfully'
        })

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticatedUserData])
def profile_status(request):
    """
    Checking the profile completion status
    """
    user_data = request.user
    serializer = UserDataSerializer(user_data)

    return Response({
        'profile_complete': user_data.is_profile_complete,
        'user_data': serializer.data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticatedUserData])
def logout(request):
    session_id = request.headers.get('X-Session-ID')
    if session_id:
        try:
            session = Session.objects.get(uuid=session_id, is_active=True)
            session.is_active = False
            session.save(update_fields=["is_active"])
        except Session.DoesNotExist:
            pass

    return Response({'message': 'Logged out successfully'})

@api_view(['POST'])
@permission_classes([AllowAny])
def guest_login(request):
    """
    Creates a guest session without registration
    """
    user, session = AuthService.create_guest_session()
    return Response({
        'session_id': str(session.uuid),
        'user_data': {
            'uuid': str(user.uuid),
            'user_type': user.user_type
        },
        'expires_at': session.expires_at
    })