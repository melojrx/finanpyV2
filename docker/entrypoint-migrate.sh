#!/bin/sh
set -eu

python - <<'PY'
import os
import time
from pathlib import Path

import psycopg

deadline = time.monotonic() + int(os.getenv("DB_WAIT_TIMEOUT", "60"))
last_error = None
password = os.getenv("POSTGRES_PASSWORD", "")
password_file = os.getenv("POSTGRES_PASSWORD_FILE")
if password_file:
    password = Path(password_file).read_text(encoding="utf-8").strip()
while time.monotonic() < deadline:
    try:
        with psycopg.connect(
            dbname=os.getenv("POSTGRES_DB", "finanpy"),
            user=os.getenv("POSTGRES_USER", "finanpy"),
            password=password,
            host=os.getenv("POSTGRES_HOST", "postgres"),
            port=os.getenv("POSTGRES_PORT", "5432"),
            connect_timeout=3,
        ):
            break
    except psycopg.OperationalError as exc:
        last_error = exc
        time.sleep(2)
else:
    raise SystemExit(f"PostgreSQL was not available in time: {last_error}")
PY

python manage.py migrate --noinput
