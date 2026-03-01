
# ══════════════════════════════════════════════════════════════════════════
# apps/weather/services/alerts.py
# ══════════════════════════════════════════════════════════════════════════
"""
Severity mapping and alert enrichment helpers.
"""
from django.utils import timezone

SEVERITY_MAP = {
    # keyword fragments → severity level
    'tornado':         'extreme',
    'hurricane':       'extreme',
    'typhoon':         'extreme',
    'cyclone':         'extreme',
    'blizzard':        'severe',
    'flood':           'severe',
    'flash flood':     'severe',
    'thunderstorm':    'moderate',
    'storm':           'moderate',
    'wind advisory':   'minor',
    'fog':             'minor',
    'freeze':          'moderate',
    'ice':             'moderate',
    'heat':            'moderate',
}


def infer_severity(event_name: str) -> str:
    """Infer severity level from alert event name string."""
    lower = event_name.lower()
    for keyword, level in SEVERITY_MAP.items():
        if keyword in lower:
            return level
    return 'minor'


def is_alert_active(alert: dict) -> bool:
    """Check if an OWM alert dict is still within its time window."""
    now = timezone.now().timestamp()
    return alert.get('start', 0) <= now <= alert.get('end', 0)


def enrich_alert(alert: dict) -> dict:
    """Add computed fields to a raw OWM alert dict."""
    alert['severity']  = infer_severity(alert.get('event', ''))
    alert['is_active'] = is_alert_active(alert)
    return alert