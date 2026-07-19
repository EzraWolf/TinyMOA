#!/bin/sh
set -eu

cd "$(dirname "$0")/.."

veryl build --quiet
uv run pytest --no-header --tb=short -q -n auto
