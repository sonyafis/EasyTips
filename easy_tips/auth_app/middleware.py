from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from .models import Session

class RefreshSessionMiddleware:
    """
    Automatically extends session and cookie expiration on each request if the user is logged in.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        session_id = request.COOKIES.get(settings.SESSION_COOKIE_NAME)
        if session_id:
            self.renew_session_cookie(session_id, response)

        return response
    
    def renew_session_cookie(self, session_id, response):
        cookie_value = response.cookies.get(settings.SESSION_COOKIE_NAME)

        if cookie_value:
            session_id = cookie_value.value

        try:
            session = Session.objects.get(uuid=session_id, is_active=True)
        except Session.DoesNotExist:
            return

        now = timezone.now()
        if session.expires_at > now:
            # Extending the session
            session.expires_at += timedelta(seconds=settings.SESSION_COOKIE_AGE)
            session.save(update_fields=["expires_at"])

            # We update the cookie with a new expiration date.
            response.set_cookie(
                settings.SESSION_COOKIE_NAME,
                str(session.uuid),
                httponly=True,
                secure=settings.SESSION_COOKIE_SECURE,
                samesite=settings.SESSION_COOKIE_SAMESITE,
                max_age=settings.SESSION_COOKIE_AGE
            )

        pass
