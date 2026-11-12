#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
if [ -s "$NVM_DIR/nvm.sh" ]; then
  # shellcheck disable=SC1090
  . "$NVM_DIR/nvm.sh"
fi
if [ ! -d node_modules ]; then
  npm install --no-audit --no-fund
fi
