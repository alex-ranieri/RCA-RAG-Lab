#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 -c 'from pypdf import PdfReader' 2>/dev/null || python3 -m pip install -r requirements.txt
python3 app.py
