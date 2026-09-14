#!/bin/sh
set -eu

SCRIPT_DIRECTORY=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
FINANPY_ROOT='/srv/finanpy'
CONFIGURATION_FILE="$FINANPY_ROOT/finanpy.env"
WEB_SERVICE='finanpy_web'
MIGRATE_SERVICE='finanpy_migrate'

. "$SCRIPT_DIRECTORY/load-env.sh"

[ "$#" -eq 2 ] || { echo 'Usage: deploy-stack.sh <release-directory> <digest>' >&2; exit 1; }
release_directory=$1
FINANPY_IMAGE=$2
validate_finanpy_image "$FINANPY_IMAGE" || { echo 'Invalid image digest.' >&2; exit 1; }
case "$release_directory" in "$FINANPY_ROOT"/releases/*) ;; *) echo 'Invalid release directory.' >&2; exit 1 ;; esac

load_env_file "$CONFIGURATION_FILE"
export FINANPY_IMAGE
stack_file="$release_directory/deploy/swarm/finanpy.yml"
edge_file="$release_directory/deploy/swarm/finanpy-edge.yml"
[ -r "$stack_file" ] && [ -r "$edge_file" ] || { echo 'Release manifests are not readable.' >&2; exit 1; }

[ "$(docker info --format '{{.Swarm.LocalNodeState}}')" = active ] || { echo 'Docker Swarm is not active.' >&2; exit 1; }
docker network inspect edge >/dev/null 2>&1 || { echo 'Required network is missing: edge' >&2; exit 1; }
for secret in finanpy_django_secret_key finanpy_postgres_password finanpy_cloudflared_tunnel_token; do
  docker secret inspect "$secret" >/dev/null 2>&1 || { echo "Required secret is missing: $secret" >&2; exit 1; }
done

docker stack deploy --with-registry-auth --resolve-image always -c "$edge_file" finanpy-edge
if ! docker service inspect "$WEB_SERVICE" >/dev/null 2>&1; then
  docker stack deploy --with-registry-auth --resolve-image always -c "$stack_file" finanpy
  docker service scale --detach=true "$WEB_SERVICE=0"
fi

docker service update --image "$FINANPY_IMAGE" --force --update-monitor 0s --detach=true "$MIGRATE_SERVICE"
docker service scale --detach=true "$MIGRATE_SERVICE=1"

attempt=1
while [ "$attempt" -le 60 ]; do
  states=$(docker service ps --no-trunc --format '{{.CurrentState}}|{{.Error}}' "$MIGRATE_SERVICE")
  if printf '%s\n' "$states" | grep -q '^Complete'; then
    break
  fi
  if printf '%s\n' "$states" | grep -Eq '^(Failed|Rejected)'; then
    docker service ps --no-trunc "$MIGRATE_SERVICE" >&2
    docker service logs --tail 100 "$MIGRATE_SERVICE" >&2 || true
    docker service scale --detach=true "$MIGRATE_SERVICE=0" || true
    echo 'FinanPy migration did not complete.' >&2
    exit 1
  fi
  sleep 2
  attempt=$((attempt + 1))
done
[ "$attempt" -le 60 ] || { echo 'FinanPy migration timed out.' >&2; exit 1; }
docker service scale --detach=true "$MIGRATE_SERVICE=0"

docker stack deploy --with-registry-auth --resolve-image always -c "$stack_file" finanpy

attempt=1
while [ "$attempt" -le 60 ]; do
  container_id=$(docker ps --filter "label=com.docker.swarm.service.name=$WEB_SERVICE" --filter status=running --format '{{.ID}}' | sed -n '1p')
  if [ -n "$container_id" ]; then
    health=$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$container_id")
    if [ "$health" = healthy ]; then
      break
    fi
  fi
  sleep 2
  attempt=$((attempt + 1))
done
[ "$attempt" -le 60 ] || { docker service ps --no-trunc "$WEB_SERVICE" >&2; docker service logs --tail 100 "$WEB_SERVICE" >&2 || true; exit 1; }

container_id=$(docker ps --filter "label=com.docker.swarm.service.name=$WEB_SERVICE" --filter status=running --format '{{.ID}}' | sed -n '1p')
docker exec "$container_id" python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/readiness/', timeout=5)"
echo "FinanPy release is ready: $FINANPY_IMAGE"
