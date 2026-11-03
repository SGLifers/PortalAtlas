#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
atlas_python="${ATLAS_PYTHON:-python3}"
if [[ ! -x .venv/bin/python ]]; then "$atlas_python" -m venv .venv; fi
.venv/bin/python -m pip install -r requirements.txt
exec .venv/bin/python tools/setup.py "$@"
