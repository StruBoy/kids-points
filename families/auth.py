from django.contrib.auth.backends import ModelBackend

from .models import Role, User


class KidPinBackend(ModelBackend):
    """Authenticate a kid by user_id + 4-digit PIN."""

    def authenticate(self, request, user_id=None, pin=None, **kwargs):
        if user_id is None or pin is None:
            return None
        try:
            user = User.objects.get(pk=user_id, role=Role.KID, is_active=True)
        except User.DoesNotExist:
            return None
        if user.check_password(pin):
            return user
        return None
