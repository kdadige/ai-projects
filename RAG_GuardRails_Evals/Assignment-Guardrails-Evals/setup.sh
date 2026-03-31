#!/usr/bin/env bash
# FinBot Setup Script
# Usage: bash setup.sh

set -e

echo "╔══════════════════════════════════════════╗"
echo "║       FinBot Setup Script                ║"
echo "║  Advanced RAG + RBAC + Guardrails        ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# ─── Check prerequisites ──────────────────────────────────────────────────────
echo ">>> Checking prerequisites..."

if ! command -v python3.12 &>/dev/null && ! command -v python3 &>/dev/null; then
  echo "ERROR: Python 3.12+ required. Install from https://python.org"
  exit 1
fi

PYTHON=$(command -v python3.12 || command -v python3)
echo "    Python: $($PYTHON --version)"

if ! command -v node &>/dev/null; then
  echo "ERROR: Node.js 18+ required. Install from https://nodejs.org"
  exit 1
fi
echo "    Node:   $(node --version)"

if ! command -v docker &>/dev/null; then
  echo "WARNING: Docker not found. You'll need to start Qdrant manually."
fi

echo ""

# ─── Backend Setup ────────────────────────────────────────────────────────────
echo ">>> Setting up Python backend..."
cd "$(dirname "$0")/backend"

if [ ! -d ".venv" ]; then
  $PYTHON -m venv .venv
  echo "    Created .venv"
fi

.venv/bin/pip install --upgrade pip --quiet
.venv/bin/pip install -r requirements.txt --quiet
echo "    Installed Python dependencies"

# Create .env from example if not present
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "    Created backend/.env from example"
  echo "    ⚠️  IMPORTANT: Edit backend/.env and set your OPENAI_API_KEY"
fi

echo ""

# ─── Frontend Setup ───────────────────────────────────────────────────────────
echo ">>> Setting up Next.js frontend..."
cd ../frontend

npm install --silent
echo "    Installed Node dependencies"

if [ ! -f ".env.local" ]; then
  echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
  echo "    Created frontend/.env.local"
fi

echo ""

# ─── Qdrant ───────────────────────────────────────────────────────────────────
cd ..
if command -v docker &>/dev/null; then
  echo ">>> Starting Qdrant with Docker..."
  docker compose up -d qdrant
  echo "    Qdrant running at http://localhost:6333"
else
  echo ">>> Skipping Qdrant (Docker not available)"
  echo "    Start Qdrant manually: docker run -p 6333:6333 qdrant/qdrant"
fi

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║           Setup Complete! ✓              ║"
echo "╚══════════════════════════════════════════╝"
echo ""
echo "Next steps:"
echo "  1. Edit backend/.env and add your OPENAI_API_KEY"
echo "  2. Ingest documents:  cd backend && .venv/bin/python3 -m ingestion.ingest --reset"
echo "  3. Start backend:     cd backend && .venv/bin/uvicorn main:app --reload --port 8000"
echo "  4. Start frontend:    cd frontend && npm run dev"
echo "  5. Open:              http://localhost:3000"
echo ""
echo "Demo credentials:"
echo "  alice_employee / employee123"
echo "  bob_finance    / finance123"
echo "  carol_engineering / engineering123"
echo "  dave_marketing / marketing123"
echo "  eve_clevel     / clevel123"
echo "  admin          / admin123"

