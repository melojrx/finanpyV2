#!/bin/sh
set -eu

workflow=.github/workflows/deploy.yml
grep -Fq 'docker/build-push-action' "$workflow"
grep -Fq 'makemigrations --check --dry-run' "$workflow"
grep -Fq 'python manage.py test' "$workflow"
grep -Fq 'python manage.py check --deploy' "$workflow"
grep -Fq 'type=sha,format=long,prefix=sha-' "$workflow"
! grep -Fq 'appleboy/ssh-action' "$workflow"
! grep -Eq 'finanpyv2:latest|type=raw,value=latest' "$workflow"
