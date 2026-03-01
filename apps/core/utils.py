
# ══════════════════════════════════════════════════════════════════════════
# apps/core/utils.py
# ══════════════════════════════════════════════════════════════════════════
"""Reusable utility functions shared across all apps."""
import math
from datetime import datetime, timezone as tz


COMPASS_DIRS = ['N','NNE','NE','ENE','E','ESE','SE','SSE','S','SSW','SW','WSW','W','WNW','NW','NNW']


def bearing_to_compass(degrees: float) -> str:
    """Convert a wind direction in degrees to a compass label."""
    idx = round(degrees / 22.5) % 16
    return COMPASS_DIRS[idx]


def unix_to_datetime(ts: int | None) -> datetime | None:
    """Convert a Unix timestamp integer to a UTC-aware datetime."""
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=tz.utc)


def meters_to_km(m: int) -> float:
    return round(m / 1000, 1)


def uvi_label(uvi: float) -> str:
    if uvi <= 2:   return f'{uvi:.0f} – Low'
    if uvi <= 5:   return f'{uvi:.0f} – Moderate'
    if uvi <= 7:   return f'{uvi:.0f} – High'
    if uvi <= 10:  return f'{uvi:.0f} – Very High'
    return f'{uvi:.0f} – Extreme'


def dew_point_comfort(dew_point: float) -> str:
    """Return a human-readable comfort label for the dew point temperature (°C)."""
    if dew_point < 10: return 'Dry & comfortable'
    if dew_point < 16: return 'Comfortable'
    if dew_point < 18: return 'Slightly humid'
    if dew_point < 21: return 'Humid'
    if dew_point < 24: return 'Very humid'
    return 'Oppressively humid'


def celsius_to_fahrenheit(c: float) -> float:
    return round(c * 9 / 5 + 32, 1)


def ms_to_kmh(ms: float) -> float:
    return round(ms * 3.6, 1)


def ms_to_mph(ms: float) -> float:
    return round(ms * 2.23694, 1)


def haversine_distance(lat1, lon1, lat2, lon2) -> float:
    """Great-circle distance between two lat/lon points in km."""
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return round(2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a)), 2)
