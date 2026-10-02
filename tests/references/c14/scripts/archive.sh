#!/bin/sh
# usage: archive.sh DEST FILE...
set -eu
dest=$1
shift
count=0
for f in "$@"; do
  cp -- "$f" "$dest/"
  count=$((count + 1))
done
echo "archived $count"
