.PHONY: help setup qdrant backend frontend test ingest eval

help:
	@echo "FinBot — Available Commands"
	@echo "=================================="
	@echo "  make setup     - Full first-time setup"
	@echo "  make qdrant    - Start Qdrant vector database"
	@echo "  make backend   - Start FastAPI backend (port 8000)"
	@echo "  make frontend  - Start Next.js frontend (port 3000)"
	@echo "  make test      - Run all backend tests"
	@echo "  make ingest    - Ingest all documents into Qdrant"
	@echo "  make eval      - Run RAGAs ablation evaluation"

setup:
	@echo ">>> Setting up FinBot..."
	cd backend && python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
	cd frontend && npm install
	@echo ">>> Setup complete. Edit backend/.env to add your OPENAI_API_KEY"

qdrant:
	docker compose up -d qdrant
	@echo ">>> Qdrant running at http://localhost:6333"

ingest:
	cd backend && .venv/bin/python3 -m ingestion.ingest --reset

backend:
	cd backend && .venv/bin/uvicorn main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

test:
	cd backend && .venv/bin/python3 run_tests.py

eval:
	cd backend && .venv/bin/python3 -m eval.ragas_eval --ablation --output-dir ./eval_results

