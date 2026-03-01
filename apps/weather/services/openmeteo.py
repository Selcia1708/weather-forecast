"""
apps/weather/services/open_meteo.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Full wrapper for Open-Meteo APIs:
  - Forecast API  (current + hourly 48h + daily 16d)
  - Air Quality API (AQI + pollutant components)
  - Geocoding API  (forward search + reverse via coordinates)

No API key required. No rate-limit headaches.
"""

import logging
from datetime import datetime, timezone as tz

import httpx
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

# ── Cache TTLs (seconds) ──────────────────────────────────────────────────
TTL_CURRENT  = 300    # 5 min  — current conditions change quickly
TTL_FORECAST = 1800   # 30 min — hourly/daily forecast
TTL_AQI      = 600    # 10 min — air quality
TTL_GEO      = 86400  # 24 h   — geocoding results are stable


# ── WMO weather-code → (description, icon-slug) ──────────────────────────
# Icons follow the same naming convention used by OpenWeatherMap so any
# existing frontend icon mapping continues to work unchanged.
WMO_CODES: dict[int, tuple[str, str]] = {
    0:  ('Clear Sky',                '01d'),
    1:  ('Mainly Clear',             '01d'),
    2:  ('Partly Cloudy',            '02d'),
    3:  ('Overcast',                 '04d'),
    45: ('Fog',                      '50d'),
    48: ('Depositing Rime Fog',      '50d'),
    51: ('Light Drizzle',            '09d'),
    53: ('Moderate Drizzle',         '09d'),
    55: ('Dense Drizzle',            '09d'),
    61: ('Slight Rain',              '10d'),
    63: ('Moderate Rain',            '10d'),
    65: ('Heavy Rain',               '10d'),
    71: ('Slight Snow',              '13d'),
    73: ('Moderate Snow',            '13d'),
    75: ('Heavy Snow',               '13d'),
    77: ('Snow Grains',              '13d'),
    80: ('Slight Rain Showers',      '09d'),
    81: ('Moderate Rain Showers',    '09d'),
    82: ('Violent Rain Showers',     '09d'),
    85: ('Slight Snow Showers',      '13d'),
    86: ('Heavy Snow Showers',       '13d'),
    95: ('Thunderstorm',             '11d'),
    96: ('Thunderstorm With Hail',   '11d'),
    99: ('Thunderstorm Heavy Hail',  '11d'),
}

# European AQI bands reported by Open-Meteo
AQI_LABEL = {1: 'Good', 2: 'Fair', 3: 'Moderate', 4: 'Poor', 5: 'Very Poor'}


class OpenMeteoService:
    """
    Drop-in replacement for OpenWeatherService.

    Public methods mirror the original interface so view-layer code
    (tasks, serialisers, views) needs zero changes.
    """

    BASE    = settings.OPEN_METEO_BASE_URL   # https://api.open-meteo.com/v1/forecast
    AIR_URL = settings.OPEN_METEO_AIR_URL    # https://air-quality-api.open-meteo.com/v1/air-quality
    GEO_URL = settings.OPEN_METEO_GEO_URL    # https://geocoding-api.open-meteo.com/v1/search

    # ── Public API ────────────────────────────────────────────────────────

    def get_one_call(self, lat: float, lon: float, units: str = 'metric') -> dict:
        """
        Fetch a combined current + hourly + daily + alerts payload.

        The returned dict is shaped identically to what
        OpenWeatherService.get_one_call() used to return so that
        parse_current / parse_hourly / parse_daily / parse_alerts
        all work without modification.
        """
        key  = f'om:onecall:{lat:.4f}:{lon:.4f}:{units}'
        data = cache.get(key)
        if data:
            return data

        wind_unit = 'ms' if units == 'metric' else 'mph'
        temp_unit = 'celsius' if units != 'imperial' else 'fahrenheit'

        params = {
            'latitude':  lat,
            'longitude': lon,
            'current': ','.join([
                'temperature_2m', 'apparent_temperature', 'relative_humidity_2m',
                'dew_point_2m', 'surface_pressure', 'cloud_cover',
                'wind_speed_10m', 'wind_direction_10m', 'wind_gusts_10m',
                'precipitation', 'snowfall', 'visibility',
                'uv_index', 'weather_code', 'is_day',
                # sunrise/sunset are daily-only variables in Open-Meteo;
                # _build_current reads them from daily[0] instead.
            ]),
            'hourly': ','.join([
                'temperature_2m', 'apparent_temperature', 'relative_humidity_2m',
                'precipitation_probability', 'precipitation', 'snowfall',
                'wind_speed_10m', 'wind_gusts_10m', 'uv_index',
                'weather_code',
            ]),
            'daily': ','.join([
                'weather_code', 'temperature_2m_max', 'temperature_2m_min',
                'apparent_temperature_max', 'sunrise', 'sunset',
                'uv_index_max', 'precipitation_sum', 'snowfall_sum',
                'precipitation_probability_max',
                'wind_speed_10m_max', 'wind_gusts_10m_max', 'wind_direction_10m_dominant',
                'rain_sum',
                # showers_sum removed — not available on the free tier
            ]),
            'temperature_unit': temp_unit,
            'wind_speed_unit':  wind_unit,
            'precipitation_unit': 'mm',
            'timezone': 'auto',
            'forecast_days': 8,
            # forecast_hours is not a valid Open-Meteo parameter;
            # hourly data length is determined by forecast_days automatically.
        }

        raw  = self._get(self.BASE, params)
        data = self._normalise_one_call(raw)
        cache.set(key, data, TTL_CURRENT)
        return data

    def get_aqi(self, lat: float, lon: float) -> dict:
        key  = f'om:aqi:{lat:.4f}:{lon:.4f}'
        data = cache.get(key)
        if not data:
            params = {
                'latitude':  lat,
                'longitude': lon,
                'current': 'european_aqi,pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone',
            }
            raw  = self._get(self.AIR_URL, params)
            data = self._normalise_aqi(raw)
            cache.set(key, data, TTL_AQI)
        return data

    def geocode(self, query: str, limit: int = 5) -> list:
        """Forward geocode — returns a list of location dicts."""
        cache_key = f'om:geo:{query.lower().strip()}:{limit}'
        cached    = cache.get(cache_key)
        if cached:
            return cached

        params = {'name': query, 'count': limit, 'language': 'en', 'format': 'json'}
        raw    = self._get(self.GEO_URL, params)
        results = [
            {
                'name':    r.get('name', ''),
                'lat':     r.get('latitude'),
                'lon':     r.get('longitude'),
                'country': r.get('country', ''),
                'state':   r.get('admin1', ''),
            }
            for r in raw.get('results', [])
        ]
        cache.set(cache_key, results, TTL_GEO)
        return results

    def reverse_geocode(self, lat: float, lon: float) -> dict:
        """
        Open-Meteo has no reverse geocoding endpoint.
        We fall back to the Nominatim public API (free, no key).
        """
        cache_key = f'om:revgeo:{lat:.4f}:{lon:.4f}'
        cached    = cache.get(cache_key)
        if cached:
            return cached

        url    = 'https://nominatim.openstreetmap.org/reverse'
        params = {'lat': lat, 'lon': lon, 'format': 'json'}
        headers = {'User-Agent': 'WeatherSenseApp/1.0'}
        try:
            with httpx.Client(timeout=httpx.Timeout(10.0, connect=5.0)) as client:
                resp = client.get(url, params=params, headers=headers)
                resp.raise_for_status()
                raw  = resp.json()
        except httpx.HTTPError as exc:
            logger.error('Nominatim error: %s', exc)
            return {}

        addr = raw.get('address', {})
        result = {
            'name':    (
                addr.get('city') or addr.get('town') or
                addr.get('village') or addr.get('county') or ''
            ),
            'country': addr.get('country', ''),
            'state':   addr.get('state', ''),
            'lat':     lat,
            'lon':     lon,
        }
        cache.set(cache_key, result, TTL_GEO)
        return result

    # ── Parsers (same signatures as OpenWeatherService) ───────────────────

    @staticmethod
    def parse_current(raw: dict) -> dict:
        """Extract current-conditions dict from a get_one_call() payload."""
        return raw.get('current', {})

    @staticmethod
    def parse_daily(raw: dict) -> list:
        """Extract list of daily-forecast dicts from a get_one_call() payload."""
        return raw.get('daily', [])

    @staticmethod
    def parse_hourly(raw: dict) -> list:
        """Extract list of hourly-forecast dicts from a get_one_call() payload."""
        return raw.get('hourly', [])

    @staticmethod
    def parse_alerts(raw: dict) -> list:
        """
        Open-Meteo does not supply weather alerts.
        Returns an empty list to keep callers unaffected.
        """
        return raw.get('alerts', [])

    @staticmethod
    def parse_aqi(raw: dict) -> dict:
        """Extract AQI dict from a get_aqi() payload."""
        return raw

    # ── Lifestyle advice (unchanged logic) ────────────────────────────────

    @staticmethod
    def lifestyle_advice(current: dict, first_day: dict) -> dict:
        temp  = current.get('temp', 20) or 20
        uvi   = current.get('uv_index', 0) or 0
        rain  = first_day.get('rain_prob', 0) or 0
        wind  = current.get('wind_speed', 0) or 0

        if temp < 0:
            clothing = ['Heavy winter coat', 'Thermal underlayers', 'Scarf, gloves & hat', 'Insulated boots']
        elif temp < 10:
            clothing = ['Warm jacket', 'Sweater or fleece', 'Long trousers']
        elif temp < 18:
            clothing = ['Light jacket or cardigan', 'Comfortable trousers']
        elif temp < 26:
            clothing = ['T-shirt or light top', 'Jeans or chinos']
        else:
            clothing = ['Light breathable clothing', 'Shorts or summer dress', 'Cap or hat']

        if rain > 0.4:
            clothing.append('Carry an umbrella or wear a raincoat')

        outdoor = []
        if rain > 0.7:
            outdoor.append('Heavy rain expected – indoor activities recommended')
        elif rain > 0.4:
            outdoor.append('Carry rain protection for outdoor plans')
        else:
            outdoor.append('Good conditions for outdoor activities')

        if wind > 15:
            outdoor.append('Strong winds – avoid exposed heights or cycling')
        elif wind > 8:
            outdoor.append('Moderate wind – secure loose items outdoors')

        if temp > 35:
            outdoor.append('Extreme heat – stay hydrated and avoid midday sun')

        if uvi <= 2:
            sun = 'Low UV (1-2) – No protection required'
        elif uvi <= 5:
            sun = f'Moderate UV ({uvi:.0f}) – Apply SPF 30+, wear sunglasses'
        elif uvi <= 7:
            sun = f'High UV ({uvi:.0f}) – SPF 50+, seek shade between 10am–4pm'
        elif uvi <= 10:
            sun = f'Very High UV ({uvi:.0f}) – SPF 50+, protective clothing essential'
        else:
            sun = f'Extreme UV ({uvi:.0f}) – Minimise outdoor exposure, maximum protection'

        return {'clothing': clothing, 'outdoor': outdoor, 'sun_protection': sun}

    # ── Internal normalisation helpers ────────────────────────────────────

    def _normalise_one_call(self, raw: dict) -> dict:
        """
        Convert Open-Meteo's response into the same shape that
        OpenWeatherService._get() used to produce, so all existing
        parse_* methods work unchanged.
        """
        tz_offset = int(raw.get('utc_offset_seconds', 0))

        current = self._build_current(raw, tz_offset)
        hourly  = self._build_hourly(raw)
        daily   = self._build_daily(raw)

        return {
            'current':          current,
            'hourly':           hourly,
            'daily':            daily,
            'alerts':           [],          # Open-Meteo has no alert feed
            'timezone_offset':  tz_offset,
        }

    @staticmethod
    def _safe(lst: list | None, i: int, default=None):
        """Return lst[i] if it exists, otherwise default. Handles None lists and short lists."""
        if lst and i < len(lst):
            return lst[i]
        return default

    @staticmethod
    def _wmo(code: int, is_day: int = 1) -> tuple[str, str]:
        """Return (description, icon) for a WMO weather code."""
        desc, icon = WMO_CODES.get(code, ('Unknown', '01d'))
        # Swap day ↔ night icon suffix
        if not is_day:
            icon = icon.replace('d', 'n')
        return desc, icon

    def _build_current(self, raw: dict, tz_offset: int) -> dict:
        c       = raw.get('current', {})
        daily0  = (raw.get('daily', {}).get('temperature_2m_min', [None]) or [None])
        code    = c.get('weather_code', 0)
        is_day  = c.get('is_day', 1)
        desc, icon = self._wmo(code, is_day)

        # Open-Meteo returns sunrise/sunset as ISO strings per day
        daily_raw = raw.get('daily', {})
        sunrise_str = (daily_raw.get('sunrise') or [''])[0]
        sunset_str  = (daily_raw.get('sunset')  or [''])[0]

        def iso_to_unix(s: str) -> int | None:
            try:
                return int(datetime.fromisoformat(s).replace(tzinfo=tz.utc).timestamp())
            except Exception:
                return None

        return {
            'temp':             c.get('temperature_2m'),
            'feels_like':       c.get('apparent_temperature'),
            'temp_min':         self._safe(daily_raw.get('temperature_2m_min'), 0),
            'temp_max':         self._safe(daily_raw.get('temperature_2m_max'), 0),
            'humidity':         c.get('relative_humidity_2m'),
            'dew_point':        c.get('dew_point_2m'),
            'pressure':         c.get('surface_pressure'),
            'visibility':       c.get('visibility', 10000),
            'uv_index':         c.get('uv_index', 0),
            'cloud_cover':      c.get('cloud_cover', 0),
            'wind_speed':       c.get('wind_speed_10m'),
            'wind_deg':         c.get('wind_direction_10m', 0),
            'wind_gust':        c.get('wind_gusts_10m', 0),
            'rain_1h':          c.get('precipitation', 0),
            'snow_1h':          c.get('snowfall', 0),
            'sunrise':          iso_to_unix(sunrise_str),
            'sunset':           iso_to_unix(sunset_str),
            'weather_code':     code,
            'description':      desc,
            'icon':             icon,
            'timezone_offset':  tz_offset,
        }

    def _build_hourly(self, raw: dict) -> list:
        h     = raw.get('hourly', {})
        times = h.get('time', [])
        s     = self._safe
        result = []
        for i, t in enumerate(times):
            code = s(h.get('weather_code'), i, 0)
            desc, icon = self._wmo(code)
            result.append({
                'dt':           int(datetime.fromisoformat(t).replace(tzinfo=tz.utc).timestamp()),
                'temp':         s(h.get('temperature_2m'),          i),
                'feels_like':   s(h.get('apparent_temperature'),    i),
                'humidity':     s(h.get('relative_humidity_2m'),    i),
                'wind_speed':   s(h.get('wind_speed_10m'),          i, 0),
                'wind_gust':    s(h.get('wind_gusts_10m'),          i, 0),
                'rain_1h':      s(h.get('precipitation'),           i, 0),
                'snow_1h':      s(h.get('snowfall'),                i, 0),
                'rain_prob':    s(h.get('precipitation_probability'),i, 0),
                'uv_index':     s(h.get('uv_index'),                i, 0),
                'weather_code': code,
                'description':  desc,
                'icon':         icon,
            })
        return result

    def _build_daily(self, raw: dict) -> list:
        d     = raw.get('daily', {})
        dates = d.get('time', [])
        s     = self._safe
        result = []

        def iso_to_unix(s_: str) -> int | None:
            try:
                return int(datetime.fromisoformat(s_).replace(tzinfo=tz.utc).timestamp())
            except Exception:
                return None

        for i, date_str in enumerate(dates):
            code = s(d.get('weather_code'), i, 0)
            desc, icon = self._wmo(code)
            result.append({
                'dt':             iso_to_unix(date_str),
                'temp_day':       s(d.get('temperature_2m_max'),             i),
                'temp_night':     s(d.get('temperature_2m_min'),             i),
                'temp_min':       s(d.get('temperature_2m_min'),             i),
                'temp_max':       s(d.get('temperature_2m_max'),             i),
                'feels_like_day': s(d.get('apparent_temperature_max'),       i),
                'humidity':       None,   # not available per-day in Open-Meteo
                'dew_point':      None,
                'pressure':       None,
                'wind_speed':     s(d.get('wind_speed_10m_max'),             i, 0),
                'wind_gust':      s(d.get('wind_gusts_10m_max'),             i, 0),
                'wind_direction': s(d.get('wind_direction_10m_dominant'),    i, 0),
                'rain_prob':      s(d.get('precipitation_probability_max'),  i, 0),
                'rain_amount':    s(d.get('rain_sum'),                       i, 0),
                'snow_amount':    s(d.get('snowfall_sum'),                   i, 0),
                'uv_index':       s(d.get('uv_index_max'),                   i, 0),
                'sunrise':        iso_to_unix(s(d.get('sunrise'), i, '')),
                'sunset':         iso_to_unix(s(d.get('sunset'),  i, '')),
                'weather_code':   code,
                'description':    desc,
                'icon':           icon,
            })
        return result

    @staticmethod
    def _normalise_aqi(raw: dict) -> dict:
        c = raw.get('current', {})
        raw_aqi = c.get('european_aqi', 1)
        # European AQI scale is 0–500; bucket into 1-5 bands to match OWM's 1-5
        if   raw_aqi <= 20:  aqi_band = 1
        elif raw_aqi <= 40:  aqi_band = 2
        elif raw_aqi <= 60:  aqi_band = 3
        elif raw_aqi <= 80:  aqi_band = 4
        else:                aqi_band = 5
        return {
            'aqi':       aqi_band,
            'aqi_raw':   raw_aqi,
            'aqi_label': AQI_LABEL.get(aqi_band, 'Unknown'),
            'co':        c.get('carbon_monoxide',  0),
            'no2':       c.get('nitrogen_dioxide', 0),
            'o3':        c.get('ozone',            0),
            'pm2_5':     c.get('pm2_5',            0),
            'pm10':      c.get('pm10',             0),
            'so2':       c.get('sulphur_dioxide',  0),
        }

    # ── HTTP helper ───────────────────────────────────────────────────────

    def _get(self, url: str, params: dict) -> dict | list:
        try:
            with httpx.Client(timeout=httpx.Timeout(10.0, connect=5.0)) as client:
                resp = client.get(url, params=params)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as exc:
            logger.error('Open-Meteo HTTP %s for %s', exc.response.status_code, url)
            raise
        except httpx.RequestError as exc:
            logger.error('Open-Meteo request error: %s', exc)
            raise


# ── Singleton ─────────────────────────────────────────────────────────────
weather_service = OpenMeteoService()