#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
.venv/bin/python -m pip install --upgrade -r requirements.txt
echo 'Yangilandi. Botni qayta ishga tushiring.'
