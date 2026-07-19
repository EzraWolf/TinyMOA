#!/bin/sh
set -eu

cd "$(dirname "$0")/.."

if [ "${1:-}" = "--clean" ] || [ "${1:-}" = "-c" ]; then
    veryl clean --quiet
    find . -path './.venv' -prune -o -type d \( \
        -name __pycache__ -o \
        -name .ruff_cache -o \
        -name .pytest_cache -o \
        -name sim_build \
    \) -prune -exec rm -rf {} +
    rm -rf dependencies .build
elif [ "$#" -ne 0 ]; then
    echo "usage: $0 [-c|--clean]" >&2
    exit 2
fi

uv run ruff format --quiet
