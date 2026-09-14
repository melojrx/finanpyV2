#!/bin/sh
set -eu

SCRIPT_DIRECTORY=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
FINANPY_ROOT='/srv/finanpy'
CONFIGURATION_FILE="$FINANPY_ROOT/finanpy.env"
POSTGRES_SERVICE='finanpy_postgres'
MEDIA_VOLUME='finanpy_finanpy_media'

. "$SCRIPT_DIRECTORY/load-env.sh"

[ "$#" -eq 3 ] || {
  echo 'Usage: restore-private-stack.sh <release-directory> <backup-directory> <digest>' >&2
  exit 1
}

release_directory=$1
backup_directory=$2
FINANPY_IMAGE=$3

validate_finanpy_image "$FINANPY_IMAGE" || {
  echo 'Invalid image digest.' >&2
  exit 1
}
case "$release_directory" in
  "$FINANPY_ROOT"/releases/*) ;;
  *) echo 'Invalid release directory.' >&2; exit 1 ;;
esac
case "$backup_directory" in
  "$FINANPY_ROOT"/backups/*) ;;
  *) echo 'Invalid backup directory.' >&2; exit 1 ;;
esac

load_env_file "$CONFIGURATION_FILE" || {
  echo 'FinanPy environment file is invalid or unreadable.' >&2
  exit 1
}
export FINANPY_IMAGE

stack_file="$release_directory/deploy/swarm/finanpy.yml"
bootstrap_file="$release_directory/deploy/swarm/finanpy-bootstrap.yml"
database_dump="$backup_directory/database.dump"
media_archive="$backup_directory/media.tar.gz"
source_inventory="$backup_directory/source.inventory"
target_inventory="$backup_directory/target.inventory"
source_media="$backup_directory/source-media"

for required_file in "$stack_file" "$bootstrap_file" "$database_dump" "$media_archive" "$source_inventory"; do
  [ -r "$required_file" ] || {
    echo "Required file is not readable: $required_file" >&2
    exit 1
  }
done

[ "$(docker info --format '{{.Swarm.LocalNodeState}}')" = active ] || {
  echo 'Docker Swarm is not active.' >&2
  exit 1
}
docker network inspect edge >/dev/null 2>&1 || {
  echo 'Required network is missing: edge' >&2
  exit 1
}
for required_secret in finanpy_django_secret_key finanpy_postgres_password finanpy_cloudflared_tunnel_token; do
  docker secret inspect "$required_secret" >/dev/null 2>&1 || {
    echo "Required secret is missing: $required_secret" >&2
    exit 1
  }
done

docker stack deploy --with-registry-auth --resolve-image always \
  -c "$stack_file" -c "$bootstrap_file" finanpy

for volume in finanpy_finanpy_postgres_data finanpy_finanpy_staticfiles finanpy_finanpy_media; do
  docker volume inspect "$volume" >/dev/null 2>&1 || docker volume create "$volume" >/dev/null
done

attempt=1
while [ "$attempt" -le 60 ]; do
  postgres_container=$(docker ps --filter "label=com.docker.swarm.service.name=$POSTGRES_SERVICE" \
    --filter status=running --format '{{.ID}}' | sed -n '1p')
  if [ -n "$postgres_container" ]; then
    health=$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$postgres_container")
    if [ "$health" = healthy ]; then
      break
    fi
  fi
  sleep 2
  attempt=$((attempt + 1))
done
[ "$attempt" -le 60 ] || {
  docker service ps --no-trunc "$POSTGRES_SERVICE" >&2
  docker service logs --tail 100 "$POSTGRES_SERVICE" >&2 || true
  echo 'Postgres did not become healthy.' >&2
  exit 1
}

media_path=$(docker volume inspect "$MEDIA_VOLUME" --format '{{.Mountpoint}}')
[ -d "$media_path" ] || {
  echo 'Media volume mountpoint is unavailable.' >&2
  exit 1
}
[ -z "$(find "$media_path" -mindepth 1 -print -quit)" ] || {
  echo 'Media volume is not empty.' >&2
  exit 1
}

docker exec -i "$postgres_container" pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  --clean --if-exists --no-owner --no-privileges < "$database_dump"
tar -xzf "$media_archive" -C "$media_path"

[ ! -e "$source_media" ] || {
  echo "Source media directory already exists: $source_media" >&2
  exit 1
}
install -d -m 0700 "$source_media"
tar -xzf "$media_archive" -C "$source_media"

docker exec -i "$postgres_container" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At <<'SQL' > "$target_inventory"
SELECT 'users=' || count(*) FROM auth_user
UNION ALL SELECT 'accounts=' || count(*) FROM accounts_account
UNION ALL SELECT 'categories=' || count(*) FROM categories_category
UNION ALL SELECT 'transactions=' || count(*) FROM transactions_transaction
UNION ALL SELECT 'budgets=' || count(*) FROM budgets_budget
UNION ALL SELECT 'monthly_plans=' || count(*) FROM budgets_monthlyplan
UNION ALL SELECT 'goals=' || count(*) FROM goals_goal
UNION ALL SELECT 'profiles=' || count(*) FROM profiles_profile
UNION ALL SELECT 'tags=' || count(*) FROM tags_tag
ORDER BY 1;
SQL

"$release_directory/scripts/homelab/verify-rehearsal.sh" \
  "$source_inventory" "$target_inventory" "$source_media" "$media_path"

"$release_directory/scripts/homelab/deploy-stack.sh" "$release_directory" "$FINANPY_IMAGE"
