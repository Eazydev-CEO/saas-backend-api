#!/usr/bin/env sh
set -e
exec gunicorn config.wsgi:application \
  --bind 0.0.0.0:8001 \
  --workers "${GUNICORN_WORKERS:-4}" \
  --threads "${GUNICORN_THREADS:-2}" \
  --worker-class gthread \
  --timeout 60 \
  --access-logfile - \
  --error-logfile - \
  --log-level info
