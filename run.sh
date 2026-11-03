#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
if [[ ! -x .venv/bin/python ]]; then
  printf '%s\n' 'Run ./setup.sh first to prepare the local Python environment.' >&2
  exit 1
fi
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 DOTNET_PROCESSOR_COUNT=2
exec .venv/bin/python -m server "$@"
