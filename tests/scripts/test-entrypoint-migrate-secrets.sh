#!/bin/sh
set -eu

script=docker/entrypoint-migrate.sh
grep -Fq 'POSTGRES_PASSWORD_FILE' "$script"
grep -Fq 'read_text' "$script"
