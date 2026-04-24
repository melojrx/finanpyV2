#!/bin/sh
set -eu

echo "Waiting for PostgreSQL at ${POSTGRES_HOST:-db}:${POSTGRES_PORT:-5432}..."

python <<'PY'
import os
import time

import psycopg

deadline = time.time() + int(os.getenv("DB_WAIT_TIMEOUT", "60"))
last_error = None

while time.time() < deadline:
    try:
        with psycopg.connect(
            dbname=os.getenv("POSTGRES_DB", "finanpy"),
            user=os.getenv("POSTGRES_USER", "finanpy"),
            password=os.getenv("POSTGRES_PASSWORD", ""),
            host=os.getenv("POSTGRES_HOST", "db"),
            port=os.getenv("POSTGRES_PORT", "5432"),
            connect_timeout=3,
        ):
            print("PostgreSQL is available.")
            break
    except psycopg.OperationalError as exc:
        last_error = exc
        time.sleep(2)
else:
    raise SystemExit(f"PostgreSQL was not available in time: {last_error}")
PY

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec "$@"
