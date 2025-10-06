import random
import hashlib
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
from .models import UserData, Session


class AuthService:
    @staticmethod
    def generate_verification_code() -> str:
        return str(random.randint(1000, 9999))

    @staticmethod
    def _hash_code(code: str) -> str:
        return hashlib.sha256(code.encode()).hexdigest()

    @staticmethod
    def send_verification_code(phone_number: str) -> bool:
        """Generates a verification code and stores its hash in the cache"""
        code = AuthService.generate_verification_code()
        code_hash = AuthService._hash_code(code)
        cache.set(f"verification_code_{phone_number}", code_hash, 300)
        # You can integrate the SMS service here
        print(f"Код для {phone_number}: {code}")
        return True

    @staticmethod
    def verify_code(phone_number: str, code: str) -> bool:
        """Checks the entered code against the hash"""
        stored_hash = cache.get(f"verification_code_{phone_number}")
        if not stored_hash:
            return False
        return stored_hash == AuthService._hash_code(code)

    @staticmethod
    def get_or_create_user(phone_number: str, user_type='employee') -> tuple[UserData, bool]:
        """
        Gets or creates a user.
        user_type: 'employee', 'organization', 'guest'
        """
        if user_type == 'guest':
            # New guests are created every time
            user_data = UserData.objects.create(
                phone_number=None,
                user_type='guest',
                is_profile_complete=False
            )
            created = True
            return user_data, created

        try:
            user_data = UserData.objects.get(phone_number=phone_number)
            created = False
            print(f"User found: {user_data.phone_number}")
        except UserData.DoesNotExist:
            user_data = UserData.objects.create(
                phone_number=phone_number,
                is_profile_complete=False,
                user_type=user_type
            )
            created = True
            print(f"New user created: {user_data.phone_number}")

        return user_data, created

    @staticmethod
    def create_session(user_data: UserData, session_type: str = 'employee', days: int = 30) -> Session:
        """
        A universal method for creating a session for any user type.
        session_type: 'guest', 'employee', 'organization'
        days: session expiration
        """
        now = timezone.now()
        expires_at = now + timedelta(days=days)
        return Session.objects.create(
            user_data=user_data,
            expires_at=expires_at,
            session_type=session_type
        )

    @staticmethod
    def create_guest_session() -> tuple[UserData, Session]:
        guest_user, _ = AuthService.get_or_create_user(phone_number=None, user_type='guest')
        session = AuthService.create_session(guest_user, session_type='guest', days=7)
        return guest_user, session

    @staticmethod
    def create_employee_session(user_data: UserData) -> Session:
        return AuthService.create_session(user_data, session_type='employee', days=30)

    @staticmethod
    def create_organization_session(user_data: UserData) -> Session:
        return AuthService.create_session(user_data, session_type='organization', days=30)

    def create_organization_session(user_data: UserData, days: int = 30) -> Session:
        return AuthService.create_session(user_data, session_type='organization', days=days)

class OrganizationService:
    @staticmethod
    def authenticate_organization(login: str, password: str) -> UserData:
        try:
            organization = UserData.objects.get(
                login=login,
                user_type='organization'
            )
            if organization.check_password(password):
                return organization
        except UserData.DoesNotExist:
            pass
        return None

    @staticmethod
    def create_employee(organization: UserData, phone_number: str, name: str = None, email: str = None) -> UserData:
        """Creates an employee for the organization"""
        employee, created = UserData.objects.get_or_create(
            phone_number=phone_number,
            defaults={
                'user_type': 'employee',
                'organization': organization,
                'name': name,
                'email': email,
                'is_profile_complete': False
            }
        )

        if not created:
            employee.organization = organization
            if name:
                employee.name = name
            if email:
                employee.email = email
            employee.save()

        # We send an SMS with an invitation
        OrganizationService._send_employee_invitation(employee, organization)

        return employee

    @staticmethod
    def _send_employee_invitation(employee: UserData, organization: UserData):
        """Sends an SMS with an invitation to an employee"""
        # Integrate with your SMS service
        message = f"You have been added to the organization {organization.name}. Use your phone number to log in."
        print(f"SMS для {employee.phone_number}: {message}")