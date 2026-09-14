#!/bin/sh
set -eu

wrapper=deploy/homelab/deploy-finanpy-release
unit=deploy/homelab/actions.runner.finanpy.service
sudoers=deploy/homelab/runner-finanpy.sudoers

test -x "$wrapper"
test -f "$unit"
test -f "$sudoers"
grep -Fq "FINANPY_ROOT='/srv/finanpy'" "$wrapper"
grep -Fq '/opt/actions-runner-finanpy/_work/finanpy_v2/finanpy_v2' "$wrapper"
grep -Fq 'validate_finanpy_image "$image"' "$wrapper"
grep -Fq 'tar -C "$checkout" -cf - deploy/swarm scripts/homelab' "$wrapper"
grep -Fq 'exec "$FINANPY_ROOT/bin/deploy-stack.sh" "$release_directory" "$image"' "$wrapper"
grep -Fq 'User=runner-finanpy' "$unit"
grep -Fq 'WorkingDirectory=/opt/actions-runner-finanpy' "$unit"
grep -Fq 'PrivateTmp=true' "$unit"
grep -Fxq 'runner-finanpy ALL=(root) NOPASSWD: /usr/local/sbin/deploy-finanpy-release /opt/actions-runner-finanpy/_work/finanpy_v2/finanpy_v2 *' "$sudoers"
! grep -Eq '(^|[^[:alnum:]_])docker([^[:alnum:]_]|$)' "$sudoers"
