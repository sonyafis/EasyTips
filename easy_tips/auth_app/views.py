from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.core.cache import cache
from .services import AuthService, OrganizationService
from .models import Session, UserData
from .serializers import UserDataSerializer, AddEmployeeSerializer, OrganizationProfileSerializer, \
    OrganizationLoginSerializer, OrganizationRegisterSerializer, OrganizationUserDataSerializer
from .permissions import IsAuthenticatedUserData
from django.conf import settings
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

    response = Response(response_data)
    response.set_cookie(
        'session_id',
        str(session.uuid),
        httponly=settings.SESSION_COOKIE_HTTPONLY,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite=settings.SESSION_COOKIE_SAMESITE,
        max_age=settings.SESSION_COOKIE_AGE
    )

    return response


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
    session_id = request.COOKIES.get('session_id')

    if session_id:
        try:
            session = Session.objects.get(uuid=session_id, is_active=True)
            session.is_active = False
            session.save(update_fields=["is_active"])
        except Session.DoesNotExist:
            pass

    response = Response({'message': 'Logged out successfully'})
    response.delete_cookie('session_id')
    return response

@api_view(['POST'])
@permission_classes([AllowAny])
def guest_login(request):
    """
    Creates a guest session without registration
    """
    user, session = AuthService.create_guest_session()

    response = Response({
        'session_id': str(session.uuid),
        'user_data': {
            'uuid': str(user.uuid),
            'user_type': user.user_type
        },
        'expires_at': session.expires_at
    })

    response.set_cookie(
        'session_id',
        str(session.uuid),
        httponly=settings.SESSION_COOKIE_HTTPONLY,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite=settings.SESSION_COOKIE_SAMESITE,
        max_age=settings.SESSION_COOKIE_AGE
    )

    return response


@api_view(['GET'])
@permission_classes([IsAuthenticatedUserData])
def renew_auth(request):
    """
    Checking the auth status
    """

    return Response(status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def organization_register(request):
    """Registering an organization using login and password"""
    serializer = OrganizationRegisterSerializer(data=request.data)
    if serializer.is_valid():
        organization = serializer.save()

        session = AuthService.create_organization_session(organization)

        user_data_serializer = OrganizationUserDataSerializer(organization)

        response_data = {
            'session_id': str(session.uuid),
            'user_data': user_data_serializer.data,
            'profile_complete': organization.is_profile_complete,
            'message': 'Organization registered successfully'
        }

        response = Response(response_data)
        response.set_cookie(
            'session_id',
            str(session.uuid),
            httponly=settings.SESSION_COOKIE_HTTPONLY,
            secure=settings.SESSION_COOKIE_SECURE,
            samesite=settings.SESSION_COOKIE_SAMESITE,
            max_age=settings.SESSION_COOKIE_AGE
        )

        return response

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def organization_login(request):
    """Organization login using username and password"""
    serializer = OrganizationLoginSerializer(data=request.data)
    if serializer.is_valid():
        organization = OrganizationService.authenticate_organization(
            serializer.validated_data['login'],
            serializer.validated_data['password']
        )

        if organization:
            session = AuthService.create_organization_session(organization)

            user_data_serializer = OrganizationUserDataSerializer(organization)

            Session.objects.filter(
                user_data=organization,
                is_active=True
            ).exclude(uuid=session.uuid).update(is_active=False)

            response_data = {
                'session_id': str(session.uuid),
                'user_data': user_data_serializer.data,
                'profile_complete': organization.is_profile_complete,
                'message': 'Login successful'
            }

            response = Response(response_data)
            response.set_cookie(
                'session_id',
                str(session.uuid),
                httponly=settings.SESSION_COOKIE_HTTPONLY,
                secure=settings.SESSION_COOKIE_SECURE,
                samesite=settings.SESSION_COOKIE_SAMESITE,
                max_age=settings.SESSION_COOKIE_AGE
            )

            return response

        return Response(
            {'error': 'Invalid login or password'},
            status=status.HTTP_400_BAD_REQUEST
        )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def organization_complete_profile(request):
    """Filling out an organization profile after registration/login"""
    if request.user.user_type != 'organization':
        return Response(
            {'error': 'Only organizations can access this endpoint'},
            status=status.HTTP_403_FORBIDDEN
        )

    serializer = OrganizationProfileSerializer(
        request.user,
        data=request.data,
        partial=True
    )

    if serializer.is_valid():
        organization = serializer.save()
        user_data_serializer = OrganizationUserDataSerializer(organization)

        return Response({
            'success': True,
            'profile_complete': organization.is_profile_complete,
            'user_data': user_data_serializer.data,
            'message': 'Profile updated successfully'
        })

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_employee(request):
    """Adding an employee to an organization"""
    if request.user.user_type != 'organization':
        return Response(
            {'error': 'Only organizations can add employees'},
            status=status.HTTP_403_FORBIDDEN
        )

    serializer = AddEmployeeSerializer(
        data=request.data,
        context={'request': request}
    )

    if serializer.is_valid():
        employee = OrganizationService.create_employee(
            organization=request.user,
            phone_number=serializer.validated_data['phone_number'],
            name=serializer.validated_data.get('name'),
            email=serializer.validated_data.get('email')
        )

        return Response({
            'success': True,
            'employee': {
                'uuid': str(employee.uuid),
                'phone_number': employee.phone_number,
                'name': employee.name,
                'email': employee.email
            },
            'message': 'Employee added successfully'
        })

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def organization_employees(request):
    """Obtaining a list of employees of an organization"""
    if request.user.user_type != 'organization':
        return Response(
            {'error': 'Only organizations can view employees'},
            status=status.HTTP_403_FORBIDDEN
        )

    employees = UserData.objects.filter(
        organization=request.user,
        user_type='employee'
    )

    serializer = UserDataSerializer(employees, many=True)
    return Response({
        'employees': serializer.data,
        'count': employees.count()
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def organization_profile(request):
    """Obtaining organization profile data"""
    user = request.user

    if user.user_type != 'organization':
        return Response(
            {'error': 'Only organizations can access this endpoint'},
            status=status.HTTP_403_FORBIDDEN
        )

    data = {
        "name": user.name or "",
        "description": user.description or "",
        "avatar_url": user.avatar_url or None,
    }

    return Response(data)
