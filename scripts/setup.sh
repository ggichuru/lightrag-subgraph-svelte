#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

printf '\n=== Conversational Knowledge Graph Setup ===\n\n'

if ! command -v uv >/dev/null 2>&1; then
  echo "⚠️  uv is not installed. Install uv from https://docs.astral.sh/uv/ and re-run."
  exit 1
fi

if ! command -v node >/dev/null 2>&1; then
  echo "⚠️  Node.js is required (v18+ recommended)."
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "⚠️  npm is required.";
  exit 1
fi

printf '→ Setting up backend dependencies...\n'
(cd "$ROOT_DIR/backend" && uv sync)

printf '\n→ Ensuring corpus and storage directories...\n'
mkdir -p "$ROOT_DIR/backend/data/corpus" "$ROOT_DIR/backend/lightrag_storage"

if [ ! -f "$ROOT_DIR/backend/.env" ]; then
  cp "$ROOT_DIR/backend/.env.example" "$ROOT_DIR/backend/.env"
  echo "Created backend/.env – update it with your API credentials."
fi

printf '\n→ Installing frontend packages...\n'
(cd "$ROOT_DIR/frontend" && npm install)

printf '\n✅ Setup complete.\n'
printf '\nNext steps:\n'
printf '  1. Update backend/.env with valid LLM credentials.\n'
printf '  2. (Optional) Place documents in backend/data/corpus.\n'
printf '  3. Start backend: cd backend && uv run uvicorn src.main:app --reload\n'
printf '  4. Start frontend: cd frontend && npm run dev\n'
