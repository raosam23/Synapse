#!/usr/bin/env bash
# Runs only on first Postgres init (empty volume). Existing volumes: CREATE DATABASE
# synapse_test manually — see README.
set -euo pipefail

test_db="${POSTGRES_TEST_DB:-synapse_test}"

exists="$(psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  -tAc "SELECT 1 FROM pg_database WHERE datname = '${test_db}'")"

if [ "$exists" = "1" ]; then
  echo "Database ${test_db} already exists"
else
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
    -c "CREATE DATABASE ${test_db}"
fi
