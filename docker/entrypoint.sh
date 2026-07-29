#!/usr/bin/env sh
# Bring the database up to date, load the reference data, then hand over to
# whatever CMD asked for.
#
# Both steps are safe to repeat, so restarting the container is fine. Alembic
# skips migrations it has already applied, and the seed loader matches on
# primary key.
set -eu

echo "Applying migrations..."
alembic upgrade head

if [ "${SEED_ON_START:-true}" = "true" ]; then
  echo "Loading reference data..."
  python -m app.seed
else
  echo "Skipping reference data (SEED_ON_START=${SEED_ON_START})."
fi

echo "Starting: $*"
exec "$@"
