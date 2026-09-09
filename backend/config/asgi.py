"""
ASGI config - routes both HTTP (Django) and WebSocket (Channels).
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# get_asgi_application() must be called before importing anything that
# touches models, so Django app registry is populated first.
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from core.middleware.jwt_ws_auth import JWTAuthMiddlewareStack
from core.routing import websocket_urlpatterns as core_ws_urlpatterns
from workspace.routing import websocket_urlpatterns as workspace_ws_urlpatterns
from notifications.routing import websocket_urlpatterns as notifications_ws_urlpatterns

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": JWTAuthMiddlewareStack(
            URLRouter(core_ws_urlpatterns + workspace_ws_urlpatterns + notifications_ws_urlpatterns)
        ),
    }
)
