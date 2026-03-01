import logging
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status

from .services import weather_service, enrich_aqi, enrich_alert
from .models import WeatherSnapshot, SevereWeatherAlert
from .serializers import (
    WeatherSnapshotSerializer, ForecastDaySerializer,
    HourlyForecastSerializer, AirQualitySerializer,
    SevereWeatherAlertSerializer,
)

logger = logging.getLogger(__name__)


# ── HTML dashboard ────────────────────────────────────────────────────────

def dashboard(request):
    """Serve the single-page weather dashboard."""
    return render(request, 'dashboard.html', {
        'OWM_KEY': '',  # exposed only for tile layer; sensitive key kept server-side
    })


# ── Full composite endpoint ───────────────────────────────────────────────

class FullWeatherAPIView(APIView):
    """
    GET /api/weather/full/?lat=&lon=&units=metric
    Returns current + hourly + daily + alerts + AQI + lifestyle in one call.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        lat   = request.query_params.get('lat')
        lon   = request.query_params.get('lon')
        units = request.query_params.get('units', 'metric')

        if not lat or not lon:
            return Response({'error': 'lat and lon are required'}, status=400)

        try:
            lat, lon = float(lat), float(lon)
            raw      = weather_service.get_one_call(lat, lon, units)
            current  = weather_service.parse_current(raw)
            daily    = weather_service.parse_daily(raw)
            hourly   = weather_service.parse_hourly(raw)
            raw_alerts = weather_service.parse_alerts(raw)
            alerts   = [enrich_alert(a) for a in raw_alerts]

            aqi_raw  = weather_service.get_aqi(lat, lon)
            aqi      = enrich_aqi(weather_service.parse_aqi(aqi_raw))
            lifestyle = weather_service.lifestyle_advice(current, daily[0] if daily else {})

            return Response({
                'current':   current,
                'daily':     daily,
                'hourly':    hourly[:24],
                'alerts':    alerts,
                'aqi':       aqi,
                'lifestyle': lifestyle,
            })
        except Exception:
            logger.exception('FullWeatherAPIView error')
            return Response({'error': 'Failed to fetch weather data'}, status=500)


# ── Current weather ───────────────────────────────────────────────────────

class CurrentWeatherAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        lat   = request.query_params.get('lat')
        lon   = request.query_params.get('lon')
        units = request.query_params.get('units', 'metric')

        if not lat or not lon:
            return Response({'error': 'lat and lon required'}, status=400)
        try:
            raw     = weather_service.get_one_call(float(lat), float(lon), units)
            current = weather_service.parse_current(raw)
            return Response(current)
        except Exception:
            logger.exception('CurrentWeatherAPIView error')
            return Response({'error': 'Fetch failed'}, status=500)


# ── Forecast (daily + hourly) ─────────────────────────────────────────────

class ForecastAPIView(APIView):
    permission_classes = [AllowAny]

    @method_decorator(cache_page(60 * 30))
    def get(self, request):
        lat   = float(request.query_params.get('lat', 0))
        lon   = float(request.query_params.get('lon', 0))
        units = request.query_params.get('units', 'metric')
        days  = min(int(request.query_params.get('days', 7)), 8)

        try:
            raw   = weather_service.get_one_call(lat, lon, units)
            return Response({
                'daily':  weather_service.parse_daily(raw)[:days],
                'hourly': weather_service.parse_hourly(raw),
            })
        except Exception:
            logger.exception('ForecastAPIView error')
            return Response({'error': 'Fetch failed'}, status=500)


# ── AQI ───────────────────────────────────────────────────────────────────

class AQIAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        lat = float(request.query_params.get('lat', 0))
        lon = float(request.query_params.get('lon', 0))
        try:
            raw = weather_service.get_aqi(lat, lon)
            return Response(enrich_aqi(weather_service.parse_aqi(raw)))
        except Exception:
            logger.exception('AQIAPIView error')
            return Response({'error': 'Fetch failed'}, status=500)


# ── Alerts ────────────────────────────────────────────────────────────────

class AlertsAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        lat   = float(request.query_params.get('lat', 0))
        lon   = float(request.query_params.get('lon', 0))
        units = request.query_params.get('units', 'metric')
        try:
            raw    = weather_service.get_one_call(lat, lon, units)
            alerts = [enrich_alert(a) for a in weather_service.parse_alerts(raw)]
            return Response({'alerts': alerts})
        except Exception:
            logger.exception('AlertsAPIView error')
            return Response({'error': 'Fetch failed'}, status=500)


# ── Geocoding ─────────────────────────────────────────────────────────────

class SearchLocationAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        q = request.query_params.get('q', '').strip()
        if not q:
            return Response({'error': 'Query parameter q is required'}, status=400)
        results = weather_service.geocode(q)
        return Response(results)


class ReverseGeocodeAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        lat = request.query_params.get('lat')
        lon = request.query_params.get('lon')
        if not lat or not lon:
            return Response({'error': 'lat and lon required'}, status=400)
        return Response(weather_service.reverse_geocode(float(lat), float(lon)))


# ── Historical snapshots ──────────────────────────────────────────────────

class HistoryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        location_id = request.query_params.get('location_id')
        if not location_id:
            return Response({'error': 'location_id required'}, status=400)
        qs = (
            WeatherSnapshot.objects
            .filter(location_id=location_id, location__user=request.user)
            .order_by('-recorded_at')[:168]  # last 7 days of hourly data
        )
        return Response(WeatherSnapshotSerializer(qs, many=True).data)