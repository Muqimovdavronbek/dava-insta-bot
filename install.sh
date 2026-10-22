#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
umask 077
if ! command -v python3 >/dev/null; then
  echo 'Python kerak: sudo apt install python3 python3-venv'
  exit 1
fi
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' || {
  echo 'Python 3.10 yoki undan yangisi kerak.'; exit 1;
}
if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv || {
    echo 'Venv o‘rnatish uchun: sudo apt install python3-venv'
    echo 'Keyin yana: bash install.sh'
    exit 1
  }
fi
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install --upgrade -r requirements.txt
.venv/bin/python setup_bot.py
exec bash start.sh
