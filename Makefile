# TDS - AI Search Visibility Analytics
# Ports
BACKEND_PORT ?= 8000
FRONTEND_PORT ?= 3000

.PHONY: install install-backend install-frontend clean start stop dev logs health

# ── Install ──────────────────────────────────────────────────────────
install: install-backend install-frontend

install-backend:
	cd backend && pip install -e . 2>/dev/null || pip install -r <(cd backend && python -c "import tomllib; f=open('pyproject.toml','rb'); d=tomllib.load(f); print('\n'.join(d['project']['dependencies']))") 2>/dev/null || (cd backend && uv sync) 2>/dev/null || true

install-frontend:
	cd frontend && (bun install 2>/dev/null || npm install 2>/dev/null)

# ── Port cleanup ─────────────────────────────────────────────────────
clean:
	@echo "Killing processes on ports $(BACKEND_PORT) and $(FRONTEND_PORT)..."
	-lsof -ti:$(BACKEND_PORT) | xargs kill -9 2>/dev/null || true
	-lsof -ti:$(FRONTEND_PORT) | xargs kill -9 2>/dev/null || true
	@sleep 1
	@echo "Ports cleaned."

# ── Start (production) ──────────────────────────────────────────────
start: clean
	@echo "Building frontend..."
	cd frontend && (bun run build 2>/dev/null || npm run build)
	@echo "Starting backend on :$(BACKEND_PORT)..."
	cd backend && nohup python -m uvicorn app.main:app --host 0.0.0.0 --port $(BACKEND_PORT) > ../backend.log 2>&1 &
	@sleep 2
	@echo "Starting frontend on :$(FRONTEND_PORT)..."
	cd frontend && nohup npx next start --port $(FRONTEND_PORT) -H 0.0.0.0 > ../frontend.log 2>&1 &
	@sleep 2
	@echo "Both services started. Logs: backend.log, frontend.log"

# ── Dev (with hot reload) ────────────────────────────────────────────
dev: clean
	@echo "Starting backend (dev) on :$(BACKEND_PORT)..."
	cd backend && nohup python -m uvicorn app.main:app --host 0.0.0.0 --port $(BACKEND_PORT) --reload > ../backend.log 2>&1 &
	@sleep 2
	@echo "Starting frontend (dev) on :$(FRONTEND_PORT)..."
	cd frontend && nohup npx next dev --port $(FRONTEND_PORT) -H 0.0.0.0 > ../frontend.log 2>&1 &
	@sleep 2
	@echo "Both services started in dev mode."

# ── Stop ─────────────────────────────────────────────────────────────
stop: clean

# ── Logs ─────────────────────────────────────────────────────────────
logs:
	@echo "=== BACKEND ===" && tail -30 backend.log 2>/dev/null || echo "(no log)" && echo "" && echo "=== FRONTEND ===" && tail -30 frontend.log 2>/dev/null || echo "(no log)"

# ── Health check ─────────────────────────────────────────────────────
health:
	@echo "Backend:" && curl -sf http://localhost:$(BACKEND_PORT)/api/health && echo "" || echo "  NOT RUNNING"
	@echo "Frontend:" && curl -sf -o /dev/null -w "  HTTP %{http_code}" http://localhost:$(FRONTEND_PORT) && echo "" || echo "  NOT RUNNING"
