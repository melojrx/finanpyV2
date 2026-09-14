#!/bin/sh
set -eu

if [ "$#" -ne 4 ]; then
  echo 'Usage: verify-rehearsal.sh <source-inventory> <target-inventory> <source-media> <target-media>' >&2
  exit 1
fi

source_inventory=$1
target_inventory=$2
source_media=$3
target_media=$4

for inventory in "$source_inventory" "$target_inventory"; do
  [ -r "$inventory" ] || { echo "Inventory is not readable: $inventory" >&2; exit 1; }
  while IFS='=' read -r key value || [ -n "$key" ]; do
    case "$key" in ''|'#'*) continue ;; esac
    printf '%s\n' "$key" | grep -Eq '^(users|accounts|categories|transactions|budgets|monthly_plans|goals|profiles|tags)$' || { echo "Invalid inventory key: $key" >&2; exit 1; }
    printf '%s\n' "$value" | grep -Eq '^[0-9]+$' || { echo "Inventory value must be numeric: $key" >&2; exit 1; }
  done < "$inventory"
done

diff -u "$source_inventory" "$target_inventory" >/dev/null || {
  echo 'Aggregate inventories differ.' >&2
  exit 1
}

for directory in "$source_media" "$target_media"; do
  [ -d "$directory" ] || { echo "Media directory is not readable: $directory" >&2; exit 1; }
done

source_files=$(find "$source_media" -type f -printf '%P\n' | sort | sha256sum | cut -d' ' -f1)
target_files=$(find "$target_media" -type f -printf '%P\n' | sort | sha256sum | cut -d' ' -f1)
source_bytes=$(find "$source_media" -type f -printf '%s\n' | awk '{total += $1} END {print total + 0}')
target_bytes=$(find "$target_media" -type f -printf '%s\n' | awk '{total += $1} END {print total + 0}')
[ "$source_files" = "$target_files" ] || { echo 'Media file manifests differ.' >&2; exit 1; }
[ "$source_bytes" = "$target_bytes" ] || { echo 'Media byte totals differ.' >&2; exit 1; }

printf 'Rehearsal verified: inventory matches; media manifest %s; bytes %s.\n' "$source_files" "$source_bytes"
