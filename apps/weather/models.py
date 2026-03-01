from django.db import models
from django.utils.translation import gettext_lazy as _


class WeatherSnapshot(models.Model):
    """Current-conditions snapshot stored for every refresh cycle."""

    location    = models.ForeignKey(
        'locations.Location', on_delete=models.CASCADE, related_name='snapshots'
    )
    recorded_at = models.DateTimeField(db_index=True)

    # ── Temperature ───────────────────────────────────────────────────────
    temp        = models.FloatField(_('Temperature'))
    feels_like  = models.FloatField(_('Feels like'))
    temp_min    = models.FloatField(_('Min temperature'))
    temp_max    = models.FloatField(_('Max temperature'))

    # ── Precipitation ─────────────────────────────────────────────────────
    rain_1h     = models.FloatField(_('Rain 1h (mm)'), default=0)
    snow_1h     = models.FloatField(_('Snow 1h (mm)'), default=0)
    precip_prob = models.FloatField(_('Precipitation probability 0-1'), default=0)

    # ── Wind ──────────────────────────────────────────────────────────────
    wind_speed     = models.FloatField(_('Wind speed'))
    wind_direction = models.IntegerField(_('Wind direction (°)'))
    wind_gust      = models.FloatField(_('Wind gust'), default=0)

    # ── Atmosphere ────────────────────────────────────────────────────────
    humidity    = models.IntegerField(_('Humidity %'))
    dew_point   = models.FloatField(_('Dew point'), null=True)
    pressure    = models.FloatField(_('Pressure hPa'))
    visibility  = models.IntegerField(_('Visibility (m)'), default=10000)
    uv_index    = models.FloatField(_('UV Index'), default=0)
    cloud_cover = models.IntegerField(_('Cloud cover %'), default=0)

    # ── Sky description ───────────────────────────────────────────────────
    weather_code = models.IntegerField(_('OWM weather code'))
    description  = models.CharField(max_length=200)
    icon         = models.CharField(max_length=20)

    # ── Sun ───────────────────────────────────────────────────────────────
    sunrise = models.DateTimeField(null=True)
    sunset  = models.DateTimeField(null=True)

    class Meta:
        ordering = ['-recorded_at']
        indexes  = [models.Index(fields=['location', 'recorded_at'])]

    def __str__(self):
        return f'{self.location} @ {self.recorded_at:%Y-%m-%d %H:%M}'


class ForecastDay(models.Model):
    """Daily forecast row — up to 8 days ahead."""

    location      = models.ForeignKey(
        'locations.Location', on_delete=models.CASCADE, related_name='daily_forecasts'
    )
    forecast_date = models.DateField(db_index=True)
    fetched_at    = models.DateTimeField(auto_now=True)

    # Temperatures
    temp_day   = models.FloatField()
    temp_night = models.FloatField()
    temp_min   = models.FloatField()
    temp_max   = models.FloatField()
    feels_like_day = models.FloatField()

    # Precipitation
    rain_prob   = models.FloatField(default=0)
    rain_amount = models.FloatField(default=0)
    snow_amount = models.FloatField(default=0)

    # Wind
    wind_speed    = models.FloatField()
    wind_gust     = models.FloatField(default=0)
    wind_direction = models.IntegerField()

    # Atmosphere
    humidity  = models.IntegerField()
    dew_point = models.FloatField(null=True)
    uv_index  = models.FloatField(default=0)
    pressure  = models.FloatField()

    # Sky
    weather_code = models.IntegerField()
    description  = models.CharField(max_length=200)
    icon         = models.CharField(max_length=20)
    sunrise      = models.DateTimeField()
    sunset       = models.DateTimeField()

    class Meta:
        unique_together = ('location', 'forecast_date')
        ordering        = ['forecast_date']

    def __str__(self):
        return f'{self.location} – {self.forecast_date}'


class HourlyForecast(models.Model):
    """48-hour hourly forecast."""

    location    = models.ForeignKey(
        'locations.Location', on_delete=models.CASCADE, related_name='hourly_forecasts'
    )
    dt          = models.DateTimeField(db_index=True)
    temp        = models.FloatField()
    feels_like  = models.FloatField()
    humidity    = models.IntegerField()
    wind_speed  = models.FloatField()
    wind_gust   = models.FloatField(default=0)
    rain_1h     = models.FloatField(default=0)
    snow_1h     = models.FloatField(default=0)
    rain_prob   = models.FloatField(default=0)
    uv_index    = models.FloatField(default=0)
    weather_code = models.IntegerField()
    description  = models.CharField(max_length=200)
    icon         = models.CharField(max_length=20)

    class Meta:
        unique_together = ('location', 'dt')
        ordering        = ['dt']

    def __str__(self):
        return f'{self.location} @ {self.dt:%H:%M}'


class AirQuality(models.Model):
    """AQI snapshot from OWM Air Pollution API."""

    AQI_LABELS = {1: 'Good', 2: 'Fair', 3: 'Moderate', 4: 'Poor', 5: 'Very Poor'}

    location    = models.ForeignKey(
        'locations.Location', on_delete=models.CASCADE, related_name='aqi_readings'
    )
    recorded_at = models.DateTimeField(db_index=True)
    aqi         = models.IntegerField(_('AQI level 1-5'))
    co          = models.FloatField(_('CO μg/m³'))
    no2         = models.FloatField(_('NO₂ μg/m³'))
    o3          = models.FloatField(_('O₃ μg/m³'))
    pm2_5       = models.FloatField(_('PM2.5 μg/m³'))
    pm10        = models.FloatField(_('PM10 μg/m³'))
    so2         = models.FloatField(_('SO₂ μg/m³'))

    class Meta:
        ordering = ['-recorded_at']

    @property
    def label(self):
        return self.AQI_LABELS.get(self.aqi, 'Unknown')

    def __str__(self):
        return f'{self.location} AQI={self.aqi} ({self.label})'


class SevereWeatherAlert(models.Model):
    """Severe weather alert (from OWM One Call or national sources)."""

    SEVERITY_CHOICES = [
        ('minor',    _('Minor')),
        ('moderate', _('Moderate')),
        ('severe',   _('Severe')),
        ('extreme',  _('Extreme')),
    ]

    location    = models.ForeignKey(
        'locations.Location', on_delete=models.CASCADE, related_name='alerts'
    )
    event       = models.CharField(max_length=200)
    severity    = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='moderate')
    description = models.TextField()
    start       = models.DateTimeField()
    end         = models.DateTimeField()
    sender_name = models.CharField(max_length=200, blank=True)
    tags        = models.JSONField(default=list)
    is_active   = models.BooleanField(default=True)
    notified    = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-start']
        indexes  = [models.Index(fields=['location', 'is_active', 'notified'])]

    def __str__(self):
        return f'[{self.severity.upper()}] {self.event} – {self.location}'