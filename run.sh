#!/usr/bin/env bash
# One-command start: installs dependencies on first run, then
#   ./run.sh        → build the frontend and serve everything at http://localhost:8000
#   ./run.sh dev    → backend on :8000 + Vite dev server with hot reload on :5173
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"

[ -f "$ROOT/backend/.env" ] || cp "$ROOT/backend/.env.example" "$ROOT/backend/.env"
[ -f "$ROOT/frontend/.env" ] || cp "$ROOT/frontend/.env.example" "$ROOT/frontend/.env"

if [ ! -d "$ROOT/backend/.venv" ]; then
  python3 -m venv "$ROOT/backend/.venv"
  "$ROOT/backend/.venv/bin/pip" install -q -r "$ROOT/backend/requirements.txt"
fi
if [ ! -d "$ROOT/frontend/node_modules" ]; then
  (cd "$ROOT/frontend" && npm install --silent)
fi

# PostgreSQL: start the bundled container unless DATABASE_URL in backend/.env points elsewhere
if grep -q "^DATABASE_URL=.*@localhost:5433/" "$ROOT/backend/.env" 2>/dev/null || [ ! -f "$ROOT/backend/.env" ]; then
  (cd "$ROOT" && docker compose up -d --wait db)
fi

cd "$ROOT/backend"
if [ "${1:-}" = "dev" ]; then
  .venv/bin/uvicorn app.main:app --port 8000 --reload &
  BACK=$!
  trap 'kill $BACK' EXIT
  cd "$ROOT/frontend" && npm run dev
else
  (cd "$ROOT/frontend" && npm run build --silent)
  echo "SiteBrain running at http://localhost:8000"
  exec .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
fi
