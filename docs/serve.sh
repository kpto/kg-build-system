#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
. ./_node.sh
exec npx quartz build --serve -d content "$@"
