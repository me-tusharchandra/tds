#!/usr/bin/env bash
# TDS - single-command startup script for VM / CI / AI agents
# Usage: bash start.sh [--dev]
#
# Prerequisites:
#   - Python 3.12+ with pip (or uv)
#   - Node.js 18+ with npm (or bun)
#   - backend/.env file with API keys
#
# Environment variables (optional):
#   BACKEND_PORT  (default: 8000)
#   FRONTEND_PORT (default: 3000)
#   NEXT_PUBLIC_API_URL (default: http://localhost:$BACKEND_PORT)

set -euo pipefail

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
DEV_MODE="${1:-}"
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== TDS Startup ==="
echo "Backend port:  $BACKEND_PORT"
echo "Frontend port: $FRONTEND_PORT"
echo "Root dir:      $ROOT_DIR"
echo ""

# ── 1. Kill anything on our ports ────────────────────────────────────
echo "[1/5] Cleaning ports..."
lsof -ti:"$BACKEND_PORT" | xargs kill -9 2>/dev/null || true
lsof -ti:"$FRONTEND_PORT" | xargs kill -9 2>/dev/null || true
sleep 1

# ── 2. Install backend deps ─────────────────────────────────────────
echo "[2/5] Installing backend dependencies..."
cd "$ROOT_DIR/backend"
if command -v uv &>/dev/null; then
  uv sync
elif [ -f "pyproject.toml" ]; then
  pip install -e . 2>/dev/null || pip install fastapi uvicorn httpx openai exa-py supabase pydantic pydantic-settings python-dotenv
else
  pip install fastapi uvicorn httpx openai exa-py supabase pydantic pydantic-settings python-dotenv
fi

# ── 3. Install frontend deps + build ────────────────────────────────
echo "[3/5] Installing frontend dependencies..."
cd "$ROOT_DIR/frontend"
if command -v bun &>/dev/null; then
  bun install
else
  npm install
fi

if [ "$DEV_MODE" != "--dev" ]; then
  echo "[3/5] Building frontend..."
  NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-http://localhost:$BACKEND_PORT}" \
    npx next build
fi

# ── 4. Start backend ────────────────────────────────────────────────
echo "[4/5] Starting backend..."
cd "$ROOT_DIR/backend"
if [ "$DEV_MODE" = "--dev" ]; then
  nohup python -m uvicorn app.main:app --host 0.0.0.0 --port "$BACKEND_PORT" --reload \
    > "$ROOT_DIR/backend.log" 2>&1 &
else
  nohup python -m uvicorn app.main:app --host 0.0.0.0 --port "$BACKEND_PORT" \
    > "$ROOT_DIR/backend.log" 2>&1 &
fi
BACKEND_PID=$!
echo "  Backend PID: $BACKEND_PID"

# Wait for backend to be ready
for i in $(seq 1 15); do
  if curl -sf http://localhost:"$BACKEND_PORT"/api/health > /dev/null 2>&1; then
    echo "  Backend ready."
    break
  fi
  sleep 1
done

# ── 5. Start frontend ───────────────────────────────────────────────
echo "[5/5] Starting frontend..."
cd "$ROOT_DIR/frontend"
if [ "$DEV_MODE" = "--dev" ]; then
  NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-http://localhost:$BACKEND_PORT}" \
    nohup npx next dev --port "$FRONTEND_PORT" -H 0.0.0.0 \
    > "$ROOT_DIR/frontend.log" 2>&1 &
else
  NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-http://localhost:$BACKEND_PORT}" \
    nohup npx next start --port "$FRONTEND_PORT" -H 0.0.0.0 \
    > "$ROOT_DIR/frontend.log" 2>&1 &
fi
FRONTEND_PID=$!
echo "  Frontend PID: $FRONTEND_PID"
sleep 3

echo ""
echo "=== TDS Running ==="
echo "Backend:  http://localhost:$BACKEND_PORT  (PID $BACKEND_PID)"
echo "Frontend: http://localhost:$FRONTEND_PORT (PID $FRONTEND_PID)"
echo "Logs:     $ROOT_DIR/backend.log, $ROOT_DIR/frontend.log"
echo ""
echo "To stop:  make stop  (or: kill $BACKEND_PID $FRONTEND_PID)"
