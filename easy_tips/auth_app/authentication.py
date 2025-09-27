from rest_framework.authentication import BaseAuthentication
from django.utils import timezone
from .models import Session

# class SessionAuthentication(BaseAuthentication):
#     def authenticate(self, request):
#         session_id = request.headers.get('X-Session-ID')
#         if not session_id:
#             return None

#         try:
#             session = Session.objects.get(uuid=session_id, is_active=True)
#         except Session.DoesNotExist:
#             return None

#         # Checking expiration date
#         if session.expires_at <= timezone.now():
#             session.is_active = False
#             session.save(update_fields=["is_active"])
#             return None

#         return (session.user_data, None)

class SessionAuthentication(BaseAuthentication):
    def authenticate(self, request):
        session_id = request.COOKIES.get('session_id')

        if not session_id:
            return None

        try:
            session = Session.objects.get(uuid=session_id, is_active=True)
        except Session.DoesNotExist:
            return None

        # Checking expiration date
        if session.expires_at <= timezone.now():
            session.is_active = False
            session.save(update_fields=["is_active"])
            return None

        return (session.user_data, None)