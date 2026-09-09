from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed



class ActiveUserJWTAuthentication(JWTAuthentication):
    """JWT authentication that also enforces the application's account status."""

    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        from accounts.models import User
        if user.status != User.Status.ACTIVE or not user.is_active:
            raise AuthenticationFailed("Your account is not active.", code="user_inactive")
        return user
