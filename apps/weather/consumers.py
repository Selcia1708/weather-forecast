
# ══════════════════════════════════════════════════════════════════════════
# apps/weather/consumers.py
# ══════════════════════════════════════════════════════════════════════════
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class WeatherConsumer(AsyncWebsocketConsumer):
    """
    WebSocket handler: ws/weather/<location_id>/

    - On connect: joins the Redis channel group for that location.
    - Celery tasks broadcast weather updates → group → this consumer → browser.
    - Supports client-initiated ping to keep the connection alive.
    """

    async def connect(self):
        self.location_id = self.scope['url_route']['kwargs']['location_id']
        self.group_name  = f'weather_{self.location_id}'

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        logger.info('WS connected: location=%s channel=%s', self.location_id, self.channel_name)
        await self.send(text_data=json.dumps({
            'type':        'connected',
            'location_id': self.location_id,
            'message':     'Real-time weather stream active.',
        }))

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        logger.info('WS disconnected: location=%s code=%s', self.location_id, code)

    async def receive(self, text_data=None, bytes_data=None):
        """Handle client → server messages (e.g. ping or unit change)."""
        if not text_data:
            return
        try:
            data = json.loads(text_data)
            if data.get('type') == 'ping':
                await self.send(text_data=json.dumps({'type': 'pong'}))
        except json.JSONDecodeError:
            pass

    # ── Broadcast handler (called by Celery via channel layer) ────────────
    async def weather_update(self, event):
        """Push data received from Celery task to the WebSocket client."""
        await self.send(text_data=json.dumps({
            'type': 'weather_update',
            'data': event['payload'],
        }))

    async def alert_broadcast(self, event):
        """Push a severe-weather alert to the WebSocket client."""
        await self.send(text_data=json.dumps({
            'type':  'severe_alert',
            'alert': event['alert'],
        }))