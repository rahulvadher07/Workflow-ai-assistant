from django.urls import re_path

from .consumers import DataChangeConsumer

websocket_urlpatterns = [
    re_path(r"^ws/data-changes/$", DataChangeConsumer.as_asgi()),
]
