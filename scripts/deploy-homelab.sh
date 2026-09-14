#!/bin/sh
set -eu

REPOSITORY_ROOT=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
HOMELAB_HOST='melojr@100.93.170.120'
FINANPY_ROOT='/srv/finanpy'

. "$REPOSITORY_ROOT/scripts/homelab/load-env.sh"

stage_only=false
case "$#" in
  1) FINANPY_IMAGE=$1 ;;
  2) [ "$1" = '--stage-only' ] || { echo 'Usage: scripts/deploy-homelab.sh [--stage-only] <digest>' >&2; exit 1; }; stage_only=true; FINANPY_IMAGE=$2 ;;
  *) echo 'Usage: scripts/deploy-homelab.sh [--stage-only] <digest>' >&2; exit 1 ;;
esac
validate_finanpy_image "$FINANPY_IMAGE" || { echo 'Invalid FinanPy image digest.' >&2; exit 1; }

for file in deploy/swarm/finanpy.yml deploy/swarm/finanpy-edge.yml deploy/swarm/finanpy.env.example scripts/homelab/load-env.sh scripts/homelab/deploy-stack.sh; do
  [ -r "$REPOSITORY_ROOT/$file" ] || { echo "Required release file is missing: $file" >&2; exit 1; }
done

digest=${FINANPY_IMAGE#ghcr.io/melojrx/finanpyv2@sha256:}
release_directory="$FINANPY_ROOT/releases/sha256-$digest"
ssh -o BatchMode=yes "$HOMELAB_HOST" "sudo install -d -m 0750 -o root -g root '$release_directory'"
tar -C "$REPOSITORY_ROOT" -cf - deploy/swarm scripts/homelab | ssh -o BatchMode=yes "$HOMELAB_HOST" "sudo tar -xf - -C '$release_directory'"

if [ "$stage_only" = true ]; then
  echo "Release staged at $release_directory"
  exit 0
fi

ssh -o BatchMode=yes "$HOMELAB_HOST" "sudo install -m 0755 '$release_directory/scripts/homelab/load-env.sh' '$FINANPY_ROOT/bin/load-env.sh' && sudo install -m 0755 '$release_directory/scripts/homelab/deploy-stack.sh' '$FINANPY_ROOT/bin/deploy-stack.sh' && sudo '$FINANPY_ROOT/bin/deploy-stack.sh' '$release_directory' '$FINANPY_IMAGE'"
