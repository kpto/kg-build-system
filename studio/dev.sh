#!/usr/bin/env bash
# Run the studio: backend API on :8700, frontend on :3000.
#
#   ./dev.sh [project-directory]
#
# Defaults to ../studio_test_project. Ctrl-C stops both.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo="$(cd "$here/.." && pwd)"
project="${1:-$repo/studio_test_project}"

if [[ ! -d "$project" ]]; then
  echo "project directory does not exist: $project" >&2
  exit 1
fi

if [[ ! -d "$here/backend/.venv" ]]; then
  echo "installing the backend environment…"
  (cd "$here/backend" && uv sync --python 3.12)
fi

if [[ ! -d "$here/frontend/node_modules" ]]; then
  echo "installing the frontend environment…"
  (cd "$here/frontend" && npm install --no-audit --no-fund)
fi

cleanup() { kill 0 2>/dev/null || true; }
trap cleanup EXIT INT TERM

(
  cd "$here/backend"
  echo "backend  → http://127.0.0.1:8700  (project: $project)"
  .venv/bin/python -m studio_backend.cli serve --project "$project"
) &

(
  cd "$here/frontend"
  echo "frontend → http://127.0.0.1:3000"
  npm run dev
) &

wait
