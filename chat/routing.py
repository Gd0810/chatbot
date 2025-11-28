from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/chat/(?P<public_key>[^/]+)/(?P<session_id>[^/]+)/$', consumers.ChatConsumer.as_asgi()),
    re_path(r'ws/live-chat/(?P<public_key>[^/]+)/$', consumers.ChatConsumer.as_asgi()),
]
