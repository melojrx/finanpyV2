#!/bin/sh
set -eu

manifest=deploy/swarm/finanpy.yml
edge=deploy/swarm/finanpy-edge.yml
grep -Fq 'finanpy_backend:' "$manifest"
grep -Fq 'finanpy_postgres_data:' "$manifest"
grep -Fq 'finanpy_media:' "$manifest"
grep -Fq 'failure_action: rollback' "$manifest"
grep -Fq 'finanpy_django_secret_key' "$manifest"
grep -Fq 'finanpy_cloudflared_tunnel_token' "$edge"
! grep -Eq '^\s+ports:' "$manifest"
! grep -Eq '^\s+ports:' "$edge"
