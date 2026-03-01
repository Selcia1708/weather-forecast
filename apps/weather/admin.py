# ══════════════════════════════════════════════════════════════════════════
# apps/weather/admin.py
# ══════════════════════════════════════════════════════════════════════════
from django.contrib import admin
from .models import WeatherSnapshot, ForecastDay, HourlyForecast, AirQuality, SevereWeatherAlert


@admin.register(WeatherSnapshot)
class WeatherSnapshotAdmin(admin.ModelAdmin):
    list_display  = ['location', 'recorded_at', 'temp', 'humidity', 'wind_speed', 'uv_index']
    list_filter   = ['location']
    search_fields = ['location__city']
    date_hierarchy = 'recorded_at'


@admin.register(ForecastDay)
class ForecastDayAdmin(admin.ModelAdmin):
    list_display  = ['location', 'forecast_date', 'temp_day', 'temp_min', 'temp_max', 'rain_prob']
    list_filter   = ['location']
    date_hierarchy = 'forecast_date'


@admin.register(HourlyForecast)
class HourlyForecastAdmin(admin.ModelAdmin):
    list_display  = ['location', 'dt', 'temp', 'rain_prob', 'wind_speed']
    list_filter   = ['location']


@admin.register(AirQuality)
class AirQualityAdmin(admin.ModelAdmin):
    list_display  = ['location', 'recorded_at', 'aqi', 'pm2_5', 'pm10', 'o3']
    list_filter   = ['aqi']
    date_hierarchy = 'recorded_at'


@admin.register(SevereWeatherAlert)
class SevereWeatherAlertAdmin(admin.ModelAdmin):
    list_display  = ['location', 'event', 'severity', 'start', 'end', 'is_active', 'notified']
    list_filter   = ['severity', 'is_active', 'notified']
    search_fields = ['event', 'location__city']
    actions       = ['mark_notified']

    @admin.action(description='Mark selected alerts as notified')
    def mark_notified(self, request, queryset):
        queryset.update(notified=True)