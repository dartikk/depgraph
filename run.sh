#!/usr/bin/env bash
cd "$(dirname "$0")" || exit 1
PY="${PYTHON:-python3}"
if [ "${1:-}" = "test" ]; then
    exec "$PY" -m unittest discover -s tests -t . -v
fi
exec "$PY" src/main.py "$@"
