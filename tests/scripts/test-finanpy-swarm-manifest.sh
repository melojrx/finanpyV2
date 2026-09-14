#!/bin/sh
set -eu

manifest=deploy/swarm/finanpy.yml
edge=deploy/swarm/finanpy-edge.yml
grep -Fq 'finanpy_backend:' "$manifest"
grep -Fq 'finanpy_postgres_data:' "$manifest"
grep -Fq 'finanpy_media:' "$manifest"
! grep -Fq 'finanpy_staticfiles' "$manifest"
grep -Fq 'failure_action: rollback' "$manifest"
grep -Fq 'finanpy_django_secret_key' "$manifest"
grep -Fq 'finanpy_cloudflared_tunnel_token' "$edge"
grep -Fq "'X-Forwarded-Proto': 'https'" "$manifest"
grep -Fq "'X-Forwarded-Proto': 'https'" scripts/homelab/deploy-stack.sh
grep -Fq 'traefik.http.middlewares.finanpy-forwarded-https.headers.customrequestheaders.X-Forwarded-Proto=https' "$manifest"
grep -Fq 'traefik.http.routers.finanpy.middlewares=finanpy-forwarded-https' "$manifest"
! grep -Eq '^\s+ports:' "$manifest"
! grep -Eq '^\s+ports:' "$edge"

grep -Fxq 'ALLOWED_HOSTS=finanpy.com.br,www.finanpy.com.br,127.0.0.1,localhost' deploy/swarm/finanpy.env.example
grep -Fxq 'WHITENOISE_MAX_AGE=31536000' deploy/swarm/finanpy.env.example
grep -Fxq 'SERVE_MEDIA_FILES=true' deploy/swarm/finanpy.env.example

bootstrap=deploy/swarm/finanpy-bootstrap.yml
test -f "$bootstrap"
grep -Fq 'web:' "$bootstrap"
grep -Fq 'migrate:' "$bootstrap"
grep -Fq 'replicas: 0' "$bootstrap"
! grep -Eq '^\s+ports:' "$bootstrap"

grep -Fq 'whitenoise==6.11.0' requirements.txt
grep -Fq 'whitenoise.middleware.WhiteNoiseMiddleware' core/settings_production.py
grep -Fq 'whitenoise.storage.CompressedManifestStaticFilesStorage' core/settings_production.py
grep -Fq 'WHITENOISE_MAX_AGE' core/settings_production.py
grep -Fq 'SERVE_MEDIA_FILES' core/settings_production.py
grep -Fq "getattr(settings, 'SERVE_MEDIA_FILES', False)" core/urls.py
grep -Fq 'python manage.py collectstatic --noinput' Dockerfile
! grep -Fq 'collectstatic' docker/entrypoint-migrate.sh
