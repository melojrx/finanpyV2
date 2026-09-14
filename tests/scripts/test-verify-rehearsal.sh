#!/bin/sh
set -eu

script=scripts/homelab/verify-rehearsal.sh
test -x "$script"
grep -Fq 'Aggregate inventories differ.' "$script"
grep -Fq 'Media file manifests differ.' "$script"
grep -Fq 'Media byte totals differ.' "$script"
! grep -Eiq '(password|token|secret|email|balance|amount)' "$script"
