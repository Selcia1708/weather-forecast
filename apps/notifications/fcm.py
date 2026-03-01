# ══════════════════════════════════════════════════════════════════════════
# apps/notifications/fcm.py
# ══════════════════════════════════════════════════════════════════════════
"""
Firebase Cloud Messaging helper.
Initialises the Firebase Admin SDK once and exposes send_push().
"""
import logging
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)
_firebase_initialised = False


def _init_firebase():
    global _firebase_initialised
    if _firebase_initialised:
        return
    try:
        import firebase_admin
        from firebase_admin import credentials
        cred_path = Path(settings.FIREBASE_CREDENTIALS_PATH)
        if cred_path.exists():
            cred = credentials.Certificate(str(cred_path))
            firebase_admin.initialize_app(cred)
            _firebase_initialised = True
            logger.info('Firebase Admin SDK initialised')
        else:
            logger.warning('Firebase credentials file not found at %s', cred_path)
    except Exception as exc:
        logger.error('Firebase init failed: %s', exc)


def send_push(token: str, title: str, body: str, data: dict = None) -> bool:
    """
    Send a single FCM push notification.
    Returns True on success, False on failure.
    """
    _init_firebase()
    if not _firebase_initialised:
        logger.warning('Firebase not initialised – push skipped')
        return False
    try:
        from firebase_admin import messaging
        msg = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data={str(k): str(v) for k, v in (data or {}).items()},
            token=token,
            android=messaging.AndroidConfig(priority='high'),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(sound='default')
                )
            ),
        )
        messaging.send(msg)
        return True
    except Exception as exc:
        logger.error('FCM send failed: %s', exc)
        return False