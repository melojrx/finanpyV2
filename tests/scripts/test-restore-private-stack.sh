#!/bin/sh
set -eu

script=scripts/homelab/restore-private-stack.sh

test -x "$script"
grep -Fq 'Media volume is not empty.' "$script"
grep -Fq 'pg_restore -U' "$script"
grep -Fq 'verify-rehearsal.sh' "$script"
grep -Fq 'finanpy-bootstrap.yml' "$script"
! grep -Eiq '(token|password|secret).*printf' "$script"
