#!/bin/sh

load_env_file() {
  [ "$#" -eq 1 ] || return 1
  file=$1
  [ -r "$file" ] || return 1
  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in ''|'#'*) continue ;; *=*) ;; *) return 1 ;; esac
    key=${line%%=*}
    value=${line#*=}
    printf '%s\n' "$key" | grep -Eq '^[A-Za-z_][A-Za-z0-9_]*$' || return 1
    export "$key=$value"
  done < "$file"
}

validate_finanpy_image() {
  [ "$#" -eq 1 ] || return 1
  prefix='ghcr.io/melojrx/finanpyv2@sha256:'
  case "$1" in "$prefix"*) digest=${1#"$prefix"} ;; *) return 1 ;; esac
  case "$digest" in ''|*[!0123456789abcdef]*) return 1 ;; esac
  [ "${#digest}" -eq 64 ]
}
