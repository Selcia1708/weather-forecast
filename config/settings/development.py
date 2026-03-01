
# ── development.py ────────────────────────────────────────────────────────
from .base import *  # noqa

DEBUG = True
ALLOWED_HOSTS = ['*']

INSTALLED_APPS += ['debug_toolbar']  # noqa
MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')  # noqa
INTERNAL_IPS = ['127.0.0.1']

# SQLite db/ directory is created by manage.py or entrypoint — no extra config needed.
# Override to dummy cache in dev so every API call is live (no Redis required locally).
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'