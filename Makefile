.PHONY: setup run stop nlp backend frontend

setup:
	@echo "Setting up backend..."
	cd backend && python3.11 -m venv venv && . venv/bin/activate && pip install -q -r requirements.txt
	@if [ ! -f backend/.env ]; then cp backend/.env.example backend/.env && echo "Created backend/.env — add your MISTRAL_API_KEY before running"; fi
	cd backend && . venv/bin/activate && python3.11 seed.py
	@echo ""
	@echo "Setting up NLP service..."
	cd nlp && python3.11 -m venv venv && . venv/bin/activate && pip install -q fastapi uvicorn transformers torch
	@echo ""
	@echo "Setting up frontend..."
	cd frontend && npm install --silent
	@echo ""
	@echo "Done. Run 'make run' to start all three services."

run:
	@echo "Starting NLP service (wait for 'models ready')..."
	cd nlp && . venv/bin/activate && python3.11 server.py &
	@echo "Starting backend..."
	cd backend && . venv/bin/activate && python3.11 app.py &
	@echo "Starting frontend..."
	cd frontend && npm run dev

nlp:
	cd nlp && . venv/bin/activate && python3.11 server.py

backend:
	cd backend && . venv/bin/activate && python3.11 app.py

frontend:
	cd frontend && npm run dev

stop:
	@pkill -f "python3.11 server.py" 2>/dev/null || true
	@pkill -f "python3.11 app.py" 2>/dev/null || true
	@pkill -f "vite" 2>/dev/null || true
	@echo "All services stopped."
