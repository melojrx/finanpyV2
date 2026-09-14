#!/bin/sh
set -eu

workflow=.github/workflows/deploy.yml
grep -Fq 'docker/build-push-action' "$workflow"
grep -Fq 'makemigrations --check --dry-run' "$workflow"
grep -Fq 'python manage.py test' "$workflow"
grep -Fq 'python manage.py check --deploy' "$workflow"
grep -Fq 'type=sha,format=long,prefix=sha-' "$workflow"
grep -Fq 'mkdir -p logs' "$workflow"
grep -Fq 'npm run build' "$workflow"
grep -Fq 'outputs:' "$workflow"
grep -Fq 'image: ${{ steps.image.outputs.digest }}' "$workflow"
grep -Fq 'needs: publish' "$workflow"
grep -Fq 'runs-on: [self-hosted, homelab-finanpy-deploy]' "$workflow"
grep -Fq 'group: deploy-finanpy-production' "$workflow"
grep -Fq 'sudo /usr/local/sbin/deploy-finanpy-release' "$workflow"
grep -Fq 'ghcr.io/melojrx/finanpyv2@${{ needs.publish.outputs.image }}' "$workflow"
! grep -Fq 'appleboy/ssh-action' "$workflow"
! grep -Eq 'finanpyv2:latest|type=raw,value=latest' "$workflow"
! grep -Fq 'ssh ' "$workflow"
