"""
Channels auth middleware that reads a JWT access token from the WS
connection's query string (?token=...) and resolves scope["user"],
since the default Channels AuthMiddlewareStack assumes session cookies.
"""

from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError


@database_sync_to_async
def _get_user_from_token(token_str):
    from accounts.models import User

    try:
        validated_token = AccessToken(token_str)
        user_id = validated_token["user_id"]
        user = User.objects.get(pk=user_id)
        if user.status != User.Status.ACTIVE or not user.is_active:
            return AnonymousUser()
        return user
    except (TokenError, User.DoesNotExist, KeyError):
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode()
        params = parse_qs(query_string)
        token = params.get("token", [None])[0]

        if token:
            scope["user"] = await _get_user_from_token(token)
        else:
            scope["user"] = AnonymousUser()

        return await super().__call__(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    return JWTAuthMiddleware(inner)
