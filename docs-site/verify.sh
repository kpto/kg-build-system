#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 scripts/diagrams.py
python3 scripts/kb.py generate
python3 scripts/kb.py check
./build.sh
