# ══════════════════════════════════════════════════════════════════════════
# apps/weather/routing.py   (WebSocket URL patterns)
# ══════════════════════════════════════════════════════════════════════════
from django.urls import re_path
from .consumers import WeatherConsumer

websocket_urlpatterns = [
    re_path(r'^ws/weather/(?P<location_id>\d+)/$', WeatherConsumer.as_asgi()),
]