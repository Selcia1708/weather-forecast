# ══════════════════════════════════════════════════════════════════════════
# apps/core/exceptions.py
# ══════════════════════════════════════════════════════════════════════════
"""Custom DRF exception handler for consistent error envelopes."""
import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        return Response(
            {
                'success': False,
                'errors':  response.data,
                'status':  response.status_code,
            },
            status=response.status_code,
        )

    # Unhandled exception → 500
    logger.exception('Unhandled exception in view: %s', exc)
    return Response(
        {'success': False, 'errors': 'Internal server error.', 'status': 500},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )