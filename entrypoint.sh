#!/bin/bash
set -e

echo "Running database migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Setting up users..."
if [ "${RUN_INIT_PROJECT:-false}" = "true" ]; then
    echo "Seeding admin and system prompts..."
    python manage.py init_project
fi

echo "Starting application..."

if [ $# -eq 0 ]; then
    exec gunicorn storyfinder.wsgi:application \
        --chdir /app \
        --bind 0.0.0.0:8000 \
        --workers "${GUNICORN_WORKERS:-3}" \
        --worker-class gthread \
        --threads "${GUNICORN_THREADS:-8}" \
        --timeout "${GUNICORN_TIMEOUT:-1800}" \
        --graceful-timeout 30 \
        --access-logfile - \
        --error-logfile -
else
    exec "$@"
fi