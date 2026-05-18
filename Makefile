.PHONY: setup run stop backend frontend reset reborn test logs screenshot auto-debug coop-debug

TIMESTAMP := $(shell date +%Y%m%d_%H%M%S)
LOG_DIR   := logs

setup:
	@echo "Setting up backend..."
	cd backend && python3.11 -m venv venv && . venv/bin/activate && pip install -q -r requirements.txt -r requirements-dev.txt
	@if [ ! -f backend/.env ]; then cp backend/.env.example backend/.env && echo "Created backend/.env — add your MISTRAL_API_KEY before running"; fi
	@echo ""
	@echo "Setting up frontend..."
	cd frontend && npm install --silent
	@echo ""
	@echo "Done. Run 'make run' to start, then create a run at /runs."

run:
	@mkdir -p $(LOG_DIR)
	@echo "Starting backend... (logging to $(LOG_DIR)/backend_$(TIMESTAMP).log)"
	cd backend && . venv/bin/activate && python3.11 app.py >> ../$(LOG_DIR)/backend_$(TIMESTAMP).log 2>&1 &
	@echo "Starting frontend... (Ctrl+C then 'make stop' to kill all)"
	cd frontend && npm run dev; make stop

backend:
	@mkdir -p $(LOG_DIR)
	@echo "Logging to $(LOG_DIR)/backend_$(TIMESTAMP).log"
	cd backend && . venv/bin/activate && python3.11 app.py 2>&1 | tee ../$(LOG_DIR)/backend_$(TIMESTAMP).log

frontend:
	cd frontend && npm run dev

test:
	cd backend && . venv/bin/activate && pytest tests/ -v

reset:
	@echo "Nuking database..."
	@psql -U aliceott -d spl -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;" -q
	@cd backend && . venv/bin/activate && python3.11 -c "from app import create_app; from database import db; app = create_app(); app.app_context().push(); db.create_all(); print('Database reset.')"
	@echo "Done. Run 'make run' and create a new run at /runs."

stop:
	@pkill -f "python3.11 app.py" 2>/dev/null || true
	@pkill -f "vite" 2>/dev/null || true
	@lsof -ti :8080 | xargs kill -9 2>/dev/null || true
	@echo "All services stopped."

screenshot:
	npx playwright install chromium --quiet 2>/dev/null; node screenshot.js

auto-debug:
	@echo "→ stopping any running services..."
	@pkill -f "python3.11 app.py" 2>/dev/null || true
	@pkill -f "vite" 2>/dev/null || true
	@lsof -ti :8080 | xargs kill -9 2>/dev/null || true
	@echo "→ running backend tests..."
	@mkdir -p reports
	@cd backend && . venv/bin/activate && pytest tests/ -q --tb=short 2>&1 | tee ../reports/tests_$(TIMESTAMP).txt || true
	@echo "→ starting services..."
	@mkdir -p $(LOG_DIR)
	@cd backend && . venv/bin/activate && NO_RESUME=1 python3.11 app.py >> ../$(LOG_DIR)/backend_$(TIMESTAMP).log 2>&1 &
	@cd frontend && npm run dev >> ../$(LOG_DIR)/frontend_$(TIMESTAMP).log 2>&1 &
	@echo "→ generating report (polls until ready)..."
	@npx playwright install chromium --quiet 2>/dev/null; node report.js || (pkill -f "python3.11 app.py" 2>/dev/null; pkill -f "vite" 2>/dev/null; exit 1)
	@echo "→ stopping services..."
	@pkill -f "python3.11 app.py" 2>/dev/null || true
	@pkill -f "vite" 2>/dev/null || true

coop-debug:
	@echo "→ stopping any running services..."
	@pkill -f "python3.11 app.py" 2>/dev/null || true
	@pkill -f "vite" 2>/dev/null || true
	@lsof -ti :8080 | xargs kill -9 2>/dev/null || true
	@echo "→ running backend tests..."
	@mkdir -p reports
	@cd backend && . venv/bin/activate && pytest tests/ -q --tb=short 2>&1 | tee ../reports/tests_$(TIMESTAMP).txt || true
	@echo "→ starting services..."
	@mkdir -p $(LOG_DIR)
	@cd backend && . venv/bin/activate && NO_RESUME=1 python3.11 app.py >> ../$(LOG_DIR)/backend_$(TIMESTAMP).log 2>&1 &
	@cd frontend && npm run dev >> ../$(LOG_DIR)/frontend_$(TIMESTAMP).log 2>&1 &
	@echo "→ generating report (polls until ready)..."
	@npx playwright install chromium --quiet 2>/dev/null; node report.js
	@echo "→ services still running — open http://localhost:5173 to poke around"
	@echo "→ run 'make logs' to tail the backend, 'make stop' when done"

logs:
	@tail -f $(shell ls -t $(LOG_DIR)/*.log 2>/dev/null | head -1) 2>/dev/null || echo "No logs found. Run 'make run' or 'make backend' first."

reborn:
	@echo "Stopping services..."
	@pkill -f "python3.11 app.py" 2>/dev/null || true
	@pkill -f "vite" 2>/dev/null || true
	@lsof -ti :8080 | xargs kill -9 2>/dev/null || true
	@echo "Resetting database..."
	@psql -U aliceott -d spl -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;" -q
	@cd backend && . venv/bin/activate && python3.11 -c "from app import create_app; from database import db; app = create_app(); app.app_context().push(); db.create_all()"
	@mkdir -p $(LOG_DIR)
	@echo "Starting backend... (logging to $(LOG_DIR)/backend_$(TIMESTAMP).log)"
	@cd backend && . venv/bin/activate && python3.11 app.py >> ../$(LOG_DIR)/backend_$(TIMESTAMP).log 2>&1 &
	@echo "Seeding simulation..."
	@sleep 3
	@cd backend && . venv/bin/activate && python3.11 seed_simulation.py >> ../$(LOG_DIR)/backend_$(TIMESTAMP).log 2>&1
	@echo "Starting frontend..."
	cd frontend && npm run dev; make stop
