#!/bin/sh
set -eu

cd "$(dirname "$0")/.."

check_log="$(mktemp)"
trap 'rm -f "$check_log"' EXIT

check_status=0
veryl check >"$check_log" 2>&1 || check_status=$?
sed '/^\[INFO \]/d' "$check_log"
[ "$check_status" -eq 0 ] || exit "$check_status"

veryl build --quiet
uv run pytest --no-header --tb=short -q -n auto
