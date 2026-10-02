#!/bin/sh
# usage: rotate.sh [--dry-run] DIR KEEP
# Keep the KEEP newest *.tar files directly in DIR (by modification time) and delete the
# rest. Other files are never touched. Prints one line per file: "removed PATH", or
# "would remove PATH" with --dry-run. KEEP must be a non-negative integer.
# Exit 0 on success; exit 2 with a message on stderr for bad usage, a non-integer KEEP,
# or a DIR that does not exist. File names may contain spaces.
echo "not implemented" >&2
exit 1
