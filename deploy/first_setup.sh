#!/bin/bash
# Run ONCE, inside the container, as a Cloud Run job (see deploy/DEPLOY.md): loads the empty database and creates the demo accounts.
#
# It needs the database settings as environment variables, the same ones the app uses:
#   DB_HOST   the Cloud SQL socket directory, /cloudsql/PROJECT:REGION:INSTANCE   (or a host name when run elsewhere)
#   DB_USER, DB_PASSWORD, DB_NAME, and optionally DB_PORT
# It is NOT safe to run twice on the same database: the base schema files create tables without IF NOT EXISTS.
set -euo pipefail
: "${DB_HOST:?DB_HOST is not set}" "${DB_USER:?DB_USER is not set}" "${DB_PASSWORD:?DB_PASSWORD is not set}" "${DB_NAME:?DB_NAME is not set}"

# psql reads these; a host starting with / is a socket directory
export PGHOST="$DB_HOST" PGUSER="$DB_USER" PGPASSWORD="$DB_PASSWORD" PGDATABASE="$DB_NAME" PGPORT="${DB_PORT:-5432}"
PYTHON="${PYTHON:-python}"
cd "$(dirname "$0")/.."                       # the repository root: /srv in the container

YESTERDAY="$($PYTHON -c 'from datetime import datetime, timedelta, timezone; print((datetime.now(timezone(timedelta(hours=5, minutes=30))).date() - timedelta(days=1)).isoformat())')"

echo "=== 1/4  Database schema and seed data (db/setup.sh) ==="
bash db/setup.sh "postgresql:///${DB_NAME}"

echo "=== 2/4  Five test teachers, each with a class ==="
$PYTHON scripts/create_test_teachers.py create --count 5

echo "=== 3/4  Demo accounts and their PINs ==="
$PYTHON scripts/auth_admin.py demo-setup

echo "=== 4/4  Demo progress up to ${YESTERDAY} ==="
$PYTHON scripts/demo_progress.py seed --end-date "$YESTERDAY" --yes

echo "=== Done. Sign in with the accounts printed in step 3. ==="
