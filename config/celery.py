# ══════════════════════════════════════════════════════════════════════════
# config/celery.py
# ══════════════════════════════════════════════════════════════════════════
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')

app = Celery('weather_platform')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# ── Periodic task schedule ────────────────────────────────────────────────
app.conf.beat_schedule = {
    # Refresh all saved locations every 10 minutes
    'refresh-all-locations-every-10min': {
        'task':     'apps.weather.tasks.refresh_all_active_locations',
        'schedule': crontab(minute='*/10'),
    },
    # Check & fire unnotified alerts every 2 minutes
    'check-alerts-every-2min': {
        'task':     'apps.notifications.tasks.dispatch_pending_alerts',
        'schedule': crontab(minute='*/2'),
    },
    # Purge old snapshots daily at midnight
    'purge-old-snapshots-daily': {
        'task':     'apps.weather.tasks.purge_old_snapshots',
        'schedule': crontab(hour=0, minute=0),
    },
}