#!/usr/bin/env sh
# Wait for Postgres and Redis, then run migrations and exec the given command.
set -e

echo ">> Waiting for Postgres at ${POSTGRES_HOST}:${POSTGRES_PORT}..."
until pg_isready -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" >/dev/null 2>&1; do
  sleep 1
done
echo ">> Postgres is up."

# Only the web container should run migrations to avoid races on cold start.
if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
  echo ">> Running migrations..."
  python manage.py migrate --noinput
  echo ">> Seeding subscription plans..."
  python manage.py seed_plans
fi

if [ "${COLLECT_STATIC:-false}" = "true" ]; then
  echo ">> Collecting static..."
  python manage.py collectstatic --noinput
fi

exec "$@"
