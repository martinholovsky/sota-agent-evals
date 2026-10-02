#!/bin/sh
set -eu
die() { echo "rotate.sh: $*" >&2; exit 2; }
dry=0
if [ "${1:-}" = "--dry-run" ]; then dry=1; shift; fi
[ $# -eq 2 ] || die "usage: rotate.sh [--dry-run] DIR KEEP"
dir=$1; keep=$2
case $keep in ''|*[!0-9]*) die "KEEP must be a non-negative integer" ;; esac
[ -d "$dir" ] || die "no such directory: $dir"
n=0
ls -t "$dir" | while IFS= read -r f; do
  case $f in *.tar) ;; *) continue ;; esac
  [ -f "$dir/$f" ] || continue
  n=$((n + 1))
  [ "$n" -le "$keep" ] && continue
  if [ "$dry" -eq 1 ]; then echo "would remove $dir/$f"; else rm -- "$dir/$f"; echo "removed $dir/$f"; fi
done
