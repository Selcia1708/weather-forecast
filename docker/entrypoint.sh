#!/bin/bash
# ══════════════════════════════════════════════════════════════════════════
# docker/entrypoint.sh  —  Railway start command: bash docker/entrypoint.sh
# ══════════════════════════════════════════════════════════════════════════

export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1
export DJANGO_SETTINGS_MODULE=config.settings.production

# ── Normalise variable names ───────────────────────────────────────────────
# Railway shared variables may be named SECRET_KEY instead of DJANGO_SECRET_KEY
# Accept either form and normalise to what Django expects.
if [ -z "$DJANGO_SECRET_KEY" ] && [ -n "$SECRET_KEY" ]; then
    export DJANGO_SECRET_KEY="$SECRET_KEY"
fi

echo "========================================"
echo " Weather Platform — Startup"
echo " DJANGO_SETTINGS_MODULE: $DJANGO_SETTINGS_MODULE"
echo " PORT: ${PORT:-8000}"
echo "========================================"

# ── Validate required env vars ─────────────────────────────────────────────
MISSING=""

if [ -z "$DJANGO_SECRET_KEY" ]; then
    MISSING="$MISSING\n  - DJANGO_SECRET_KEY  (or SECRET_KEY)"
fi
if [ -z "$DATABASE_URL" ]; then
    MISSING="$MISSING\n  - DATABASE_URL  (add a PostgreSQL plugin in Railway)"
fi
if [ -z "$REDIS_URL" ]; then
    MISSING="$MISSING\n  - REDIS_URL  (add a Redis plugin in Railway)"
fi

if [ -n "$MISSING" ]; then
    echo ""
    echo "ERROR: Missing required environment variables:"
    printf "$MISSING\n"
    echo ""
    echo "Go to Railway dashboard → your service → Variables tab and add them."
    exit 1
fi

echo "✓ Environment variables present"
echo "  DATABASE_URL prefix: $(echo $DATABASE_URL | cut -c1-20)..."
echo "  REDIS_URL prefix:    $(echo $REDIS_URL | cut -c1-20)..."
echo ""

# ── Django system check ────────────────────────────────────────────────────
echo ">>> Running Django system check..."
python manage.py check 2>&1
CHECK_EXIT=$?
if [ $CHECK_EXIT -ne 0 ]; then
    echo "ERROR: Django check failed (exit $CHECK_EXIT). Fix errors above and redeploy."
    exit $CHECK_EXIT
fi
echo "✓ Django check passed"
echo ""

# ── Migrations ─────────────────────────────────────────────────────────────
echo ">>> Running migrations..."
python manage.py migrate --noinput 2>&1
MIGRATE_EXIT=$?
if [ $MIGRATE_EXIT -ne 0 ]; then
    echo "ERROR: migrate failed (exit $MIGRATE_EXIT)"
    exit $MIGRATE_EXIT
fi
echo "✓ Migrations complete"
echo ""

# ── Static files ───────────────────────────────────────────────────────────
echo ">>> Collecting static files..."
python manage.py collectstatic --noinput --clear 2>&1
echo "✓ Static files collected"
echo ""

# ── Start server ───────────────────────────────────────────────────────────
echo ">>> Starting Gunicorn on port ${PORT:-8000}..."
exec gunicorn config.asgi:application \
    -k uvicorn.workers.UvicornWorker \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers 2 \
    --timeout 120 \
    --log-level info \
    --access-logfile "-" \
    --error-logfile "-"