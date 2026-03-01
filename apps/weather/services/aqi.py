# ══════════════════════════════════════════════════════════════════════════
# apps/weather/services/aqi.py
# ══════════════════════════════════════════════════════════════════════════
"""
AQI health guidance labels and color codes per level.
"""

AQI_INFO = {
    1: {
        'label':       'Good',
        'color':       '#22c55e',
        'guidance':    'Air quality is satisfactory. No risk.',
        'who_level':   'Safe',
    },
    2: {
        'label':       'Fair',
        'color':       '#84cc16',
        'guidance':    'Acceptable quality. Sensitive groups may notice minor effects.',
        'who_level':   'Low risk',
    },
    3: {
        'label':       'Moderate',
        'color':       '#facc15',
        'guidance':    'Sensitive individuals (children, elderly, asthma) should reduce prolonged outdoor exertion.',
        'who_level':   'Moderate risk',
    },
    4: {
        'label':       'Poor',
        'color':       '#f97316',
        'guidance':    'Everyone may start to experience health effects. Sensitive groups: stay indoors.',
        'who_level':   'High risk',
    },
    5: {
        'label':       'Very Poor',
        'color':       '#ef4444',
        'guidance':    'Health warnings for emergency conditions. Entire population affected.',
        'who_level':   'Very high risk',
    },
}


def enrich_aqi(aqi_dict: dict) -> dict:
    """Attach display info to a parsed AQI dict."""
    level = aqi_dict.get('aqi', 1)
    info  = AQI_INFO.get(level, AQI_INFO[1])
    return {**aqi_dict, **info}