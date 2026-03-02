# ══════════════════════════════════════════════════════════════════════════
# apps/weather/tasks.py
# ══════════════════════════════════════════════════════════════════════════
import logging
from datetime import timedelta

from celery import shared_task
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils import timezone

from apps.locations.models import Location
from .models import WeatherSnapshot, AirQuality, SevereWeatherAlert, ForecastDay, HourlyForecast
from .services import weather_service, enrich_aqi, enrich_alert

logger = logging.getLogger(__name__)
channel_layer = get_channel_layer()


@shared_task(bind=True, max_retries=3, default_retry_delay=30, name='apps.weather.tasks.refresh_weather_for_location')
def refresh_weather_for_location(self, location_id: int):
    """
    Fetch latest OWM data for one location, persist to DB,
    and broadcast via WebSocket channel layer.
    """
    try:
        loc   = Location.objects.select_related('user__preferences').get(pk=location_id)
        units = 'metric'
        if hasattr(loc, 'user') and loc.user and hasattr(loc.user, 'preferences'):
            units = loc.user.preferences.units

        raw     = weather_service.get_one_call(float(loc.latitude), float(loc.longitude), units)
        current = weather_service.parse_current(raw)
        daily   = weather_service.parse_daily(raw)
        hourly  = weather_service.parse_hourly(raw)
        alerts  = [enrich_alert(a) for a in weather_service.parse_alerts(raw)]
        aqi_raw = weather_service.get_aqi(float(loc.latitude), float(loc.longitude))
        aqi     = enrich_aqi(weather_service.parse_aqi(aqi_raw))
        lifestyle = weather_service.lifestyle_advice(current, daily[0] if daily else {})

        now = timezone.now()

        # ── Persist current snapshot ──────────────────────────────────────
        WeatherSnapshot.objects.create(
            location       = loc,
            recorded_at    = now,
            temp           = current['temp'],
            feels_like     = current['feels_like'],
            temp_min       = current['temp_min'] or current['temp'],
            temp_max       = current['temp_max'] or current['temp'],
            rain_1h        = current['rain_1h'],
            snow_1h        = current['snow_1h'],
            precip_prob    = daily[0]['rain_prob'] if daily else 0,
            wind_speed     = current['wind_speed'],
            wind_direction = current['wind_deg'],
            wind_gust      = current['wind_gust'],
            humidity       = current['humidity'],
            dew_point      = current['dew_point'],
            pressure       = current['pressure'],
            visibility     = current['visibility'],
            uv_index       = current['uv_index'],
            cloud_cover    = current['cloud_cover'],
            weather_code   = current['weather_code'],
            description    = current['description'],
            icon           = current['icon'],
        )

        # ── Persist AQI ───────────────────────────────────────────────────
        AirQuality.objects.create(
            location    = loc,
            recorded_at = now,
            aqi   = aqi['aqi'],
            co    = aqi['co'],
            no2   = aqi['no2'],
            o3    = aqi['o3'],
            pm2_5 = aqi['pm2_5'],
            pm10  = aqi['pm10'],
            so2   = aqi['so2'],
        )

        # ── Upsert daily forecasts ────────────────────────────────────────
        import datetime
        for d in daily:
            date = datetime.date.fromtimestamp(d['dt'])
            ForecastDay.objects.update_or_create(
                location=loc, forecast_date=date,
                defaults={
                    'temp_day':       d['temp_day'],
                    'temp_night':     d['temp_night'],
                    'temp_min':       d['temp_min'],
                    'temp_max':       d['temp_max'],
                    'feels_like_day': d['feels_like_day'],
                    'rain_prob':      d['rain_prob'],
                    'rain_amount':    d['rain_amount'],
                    'snow_amount':    d['snow_amount'],
                    'wind_speed':     d['wind_speed'],
                    'wind_gust':      d['wind_gust'],
                    'wind_direction': d['wind_direction'],
                    'humidity':       d['humidity'],
                    'dew_point':      d['dew_point'],
                    'uv_index':       d['uv_index'],
                    'pressure':       d['pressure'],
                    'weather_code':   d['weather_code'],
                    'description':    d['description'],
                    'icon':           d['icon'],
                    'sunrise':        timezone.datetime.fromtimestamp(d['sunrise'], tz=timezone.utc),
                    'sunset':         timezone.datetime.fromtimestamp(d['sunset'],  tz=timezone.utc),
                }
            )

        # ── Upsert hourly forecasts ───────────────────────────────────────
        for h in hourly:
            dt = timezone.datetime.fromtimestamp(h['dt'], tz=timezone.utc)
            HourlyForecast.objects.update_or_create(
                location=loc, dt=dt,
                defaults={
                    'temp':         h['temp'],
                    'feels_like':   h['feels_like'],
                    'humidity':     h['humidity'],
                    'wind_speed':   h['wind_speed'],
                    'wind_gust':    h['wind_gust'],
                    'rain_1h':      h['rain_1h'],
                    'snow_1h':      h['snow_1h'],
                    'rain_prob':    h['rain_prob'],
                    'uv_index':     h['uv_index'],
                    'weather_code': h['weather_code'],
                    'description':  h['description'],
                    'icon':         h['icon'],
                }
            )

        # ── Save new alerts ───────────────────────────────────────────────
        for a in alerts:
            SevereWeatherAlert.objects.get_or_create(
                location    = loc,
                event       = a['event'],
                start       = timezone.datetime.fromtimestamp(a['start'], tz=timezone.utc),
                defaults={
                    'end':         timezone.datetime.fromtimestamp(a['end'], tz=timezone.utc),
                    'description': a['description'],
                    'sender_name': a['sender_name'],
                    'severity':    a['severity'],
                    'tags':        a['tags'],
                }
            )

        # ── Broadcast over WebSocket ──────────────────────────────────────
        payload = {'current': current, 'aqi': aqi, 'alerts': alerts, 'lifestyle': lifestyle}
        async_to_sync(channel_layer.group_send)(
            f'weather_{location_id}',
            {'type': 'weather.update', 'payload': payload},
        )

        # If active alerts, also push an alert_broadcast event
        active = [a for a in alerts if a.get('is_active')]
        if active:
            async_to_sync(channel_layer.group_send)(
                f'weather_{location_id}',
                {'type': 'alert.broadcast', 'alert': active[0]},
            )

        logger.info('Refreshed weather for location %s', location_id)

    except Location.DoesNotExist:
        logger.error('Location %s not found – skipping task', location_id)
    except Exception as exc:
        logger.exception('refresh_weather_for_location failed for %s', location_id)
        raise self.retry(exc=exc)


@shared_task(name='apps.weather.tasks.refresh_all_active_locations')
def refresh_all_active_locations():
    """Enqueue a refresh task for every saved location."""
    ids = Location.objects.values_list('id', flat=True)
    for lid in ids:
        refresh_weather_for_location.delay(lid)
    logger.info('Queued refresh for %d locations', len(ids))


@shared_task(name='apps.weather.tasks.purge_old_snapshots')
def purge_old_snapshots():
    """
    Delete WeatherSnapshot rows older than the user's data_retention_days preference.
    Falls back to 30 days for anonymous/system locations.
    """
    cutoff  = timezone.now() - timedelta(days=30)
    deleted, _ = WeatherSnapshot.objects.filter(recorded_at__lt=cutoff).delete()
    aqi_del, _ = AirQuality.objects.filter(recorded_at__lt=cutoff).delete()

    logger.info('Purged %d snapshots and %d AQI records', deleted, aqi_del)
