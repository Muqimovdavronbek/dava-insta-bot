#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if [[ ! -x .venv/bin/python ]]; then
  echo 'Avval ishga tushiring: bash install.sh'
  exit 1
fi
exec .venv/bin/python bot.py
