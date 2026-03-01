# ══════════════════════════════════════════════════════════════════════════
# apps/notifications/tasks.py
# ══════════════════════════════════════════════════════════════════════════
import logging
from celery import shared_task
from django.utils import timezone

from apps.users.models import UserPreferences
from apps.weather.models import SevereWeatherAlert
from .fcm import send_push
from .models import PushNotificationLog

logger = logging.getLogger(__name__)

SEVERITY_ORDER = {'minor': 1, 'moderate': 2, 'severe': 3, 'extreme': 4}


@shared_task(name='apps.notifications.tasks.dispatch_pending_alerts')
def dispatch_pending_alerts():
    """
    Find un-notified active severe weather alerts whose severity meets
    the user's threshold, then fire FCM push notifications.
    """
    now = timezone.now()
    pending = (
        SevereWeatherAlert.objects
        .filter(is_active=True, notified=False, end__gt=now)
        .select_related('location__user__preferences')
    )

    for alert in pending:
        location = alert.location
        user     = getattr(location, 'user', None)
        if not user:
            alert.notified = True
            alert.save(update_fields=['notified'])
            continue

        prefs = getattr(user, 'preferences', None)
        if not prefs or not prefs.push_alerts or not prefs.fcm_token:
            continue

        # Severity threshold check
        user_threshold  = SEVERITY_ORDER.get(prefs.alert_severity, 2)
        alert_severity  = SEVERITY_ORDER.get(alert.severity, 1)
        if alert_severity < user_threshold:
            continue

        title = f'⚠️ {alert.event}'
        body  = alert.description[:200]
        ok    = send_push(
            prefs.fcm_token, title, body,
            data={'location_id': str(location.id), 'severity': alert.severity}
        )

        PushNotificationLog.objects.create(
            user        = user,
            title       = title,
            body        = body,
            status      = 'sent' if ok else 'failed',
            alert_event = alert.event,
        )

        if ok:
            alert.notified = True
            alert.save(update_fields=['notified'])
            logger.info('Push sent to %s for alert: %s', user.email, alert.event)


@shared_task(name='apps.notifications.tasks.send_single_push')
def send_single_push(user_id: int, title: str, body: str, data: dict = None):
    """Helper task to send a one-off push to a specific user."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    try:
        prefs = UserPreferences.objects.get(user_id=user_id)
        if not prefs.fcm_token:
            return
        ok = send_push(prefs.fcm_token, title, body, data)
        PushNotificationLog.objects.create(
            user_id = user_id,
            title   = title,
            body    = body,
            status  = 'sent' if ok else 'failed',
        )
    except UserPreferences.DoesNotExist:
        logger.warning('No preferences found for user %s', user_id)