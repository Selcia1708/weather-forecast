from rest_framework import serializers
from .models import WeatherSnapshot, ForecastDay, HourlyForecast, AirQuality, SevereWeatherAlert


class WeatherSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model  = WeatherSnapshot
        fields = '__all__'


class ForecastDaySerializer(serializers.ModelSerializer):
    class Meta:
        model  = ForecastDay
        exclude = ['fetched_at']


class HourlyForecastSerializer(serializers.ModelSerializer):
    class Meta:
        model  = HourlyForecast
        fields = '__all__'


class AirQualitySerializer(serializers.ModelSerializer):
    label = serializers.CharField(source='label', read_only=True)

    class Meta:
        model  = AirQuality
        fields = ['aqi', 'label', 'co', 'no2', 'o3', 'pm2_5', 'pm10', 'so2', 'recorded_at']


class SevereWeatherAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model  = SevereWeatherAlert
        fields = ['id', 'event', 'severity', 'description', 'start', 'end', 'sender_name', 'tags', 'is_active']


# ── Composite response serializer (single-call full data) ────────────────
class FullWeatherSerializer(serializers.Serializer):
    current   = serializers.DictField()
    daily     = serializers.ListField()
    hourly    = serializers.ListField()
    alerts    = serializers.ListField()
    aqi       = serializers.DictField()
    lifestyle = serializers.DictField()