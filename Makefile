.PHONY: setup run stop backend frontend reset reborn test

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
	@echo "Starting backend..."
	cd backend && . venv/bin/activate && python3.11 app.py &
	@echo "Starting frontend... (Ctrl+C then 'make stop' to kill all)"
	cd frontend && npm run dev; make stop

backend:
	cd backend && . venv/bin/activate && python3.11 app.py

frontend:
	cd frontend && npm run dev

test:
	cd backend && . venv/bin/activate && pytest tests/ -v

reset:
	@echo "Nuking database..."
	rm -f backend/instance/lab.db
	@echo "Done. Run 'make run' and create a new run at /runs."

stop:
	@pkill -f "python3.11 app.py" 2>/dev/null || true
	@pkill -f "vite" 2>/dev/null || true
	@lsof -ti :8080 | xargs kill -9 2>/dev/null || true
	@echo "All services stopped."

reborn:
	@echo "Stopping services..."
	@pkill -f "python3.11 app.py" 2>/dev/null || true
	@pkill -f "vite" 2>/dev/null || true
	@lsof -ti :8080 | xargs kill -9 2>/dev/null || true
	@echo "Resetting database..."
	@rm -f backend/instance/lab.db
	@echo "Starting backend..."
	@cd backend && . venv/bin/activate && python3.11 app.py &
	@sleep 2
	@echo "Starting frontend..."
	cd frontend && npm run dev; make stop
