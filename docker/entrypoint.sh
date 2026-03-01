# ══════════════════════════════════════════════════════════════════════════
# docker/entrypoint.sh
# ══════════════════════════════════════════════════════════════════════════
!/bin/sh
set -e
#
# # Create the db directory if it doesn't exist (SQLite lives here)
mkdir -p /app/db

echo "==> Running DB migrations"
python manage.py migrate --noinput

echo "==> Starting Daphne ASGI server"
exec daphne -b 0.0.0.0 -p 8000 config.asgi:application