#!/bin/sh
set -eu

cd "$(dirname "$0")/.."

veryl build --check --quiet
uv run pytest --no-header --tb=short -q -n auto
