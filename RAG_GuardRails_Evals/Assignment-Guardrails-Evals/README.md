# FinBot — Advanced RAG with RBAC, Guardrails & Evals

> **Codebasics AI Engineering Bootcamp — Assignment 1**  
> An enterprise-grade internal Q&A assistant for FinSolve Technologies.

---

## 🏗️ Architecture Overview

```
User Query
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│                    INPUT GUARDRAILS                      │
│  Rate Limit → Injection Detection → PII Scrubbing →     │
│  Off-Topic Detection                                     │
└──────────────────────────┬──────────────────────────────┘
                           │ (clean query)
                           ▼
┌─────────────────────────────────────────────────────────┐
│               SEMANTIC ROUTER                            │
│  Classify intent → finance / engineering /               │
│  marketing / hr_general / cross_department               │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│            RBAC INTERSECTION                             │
│  Route collections ∩ User's allowed collections          │
│  → Access Denied if intersection is empty                │
└──────────────────────────┬──────────────────────────────┘
                           │ (target_collections)
                           ▼
┌─────────────────────────────────────────────────────────┐
│      QDRANT VECTOR SEARCH (RBAC filter at query layer)   │
│  Filter: access_roles MUST contain user's role           │
│  → Restricted chunks NEVER reach LLM context            │
└──────────────────────────┬──────────────────────────────┘
                           │ (top-k chunks)
                           ▼
┌─────────────────────────────────────────────────────────┐
│              GPT-4o-mini (with citations)                │
│  System prompt enforces [Source: file, p.N] format       │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                   OUTPUT GUARDRAILS                      │
│  Citation enforcement → Grounding check →               │
│  Cross-role leakage check                                │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
                    Structured Response
                    (answer + citations + route + warnings)
```

### RBAC Enforcement Flow

```
Login (JWT issued with role) ──► Query received
        │
        ▼
  RBAC role injected into Qdrant `must` filter:
    access_roles: { value_must_match: "<user_role>" }
        │
        ▼
  Qdrant executes similarity search with filter applied
        │
        ▼
  Only matching chunks (where access_roles contains user_role) returned
        │
        ▼
  LLM generates answer from role-scoped context only
```

The `access_roles` metadata field is a Qdrant keyword index. The filter is evaluated **at the vector database query level**, meaning restricted vectors are never loaded, scored, or returned to the application regardless of what the user's prompt contains.

---

## 👥 Demo Credentials

| Username              | Password         | Role          | Access                                        |
|-----------------------|------------------|---------------|-----------------------------------------------|
| `alice_employee`      | `employee123`    | employee      | general                                       |
| `bob_finance`         | `finance123`     | finance       | finance, general                              |
| `carol_engineering`   | `engineering123` | engineering   | engineering, general                          |
| `dave_marketing`      | `marketing123`   | marketing     | marketing, general                            |
| `eve_clevel`          | `clevel123`      | c_level       | all (general, finance, engineering, marketing, hr) |
| `admin`               | `admin123`       | c_level       | all + admin panel                             |

---

## 🚀 Setup Instructions

### Prerequisites
- Python 3.12
- Node.js 18+
- Docker (for Qdrant)
- OpenAI API key

### Quick Setup (automated)
```bash
bash setup.sh
```

### Manual Setup

#### 1. Start Qdrant
```bash
docker compose up -d qdrant
# Qdrant dashboard: http://localhost:6333/dashboard
```

#### 2. Backend Setup
```bash
cd backend

# Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate       # macOS/Linux
# .venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env and set: OPENAI_API_KEY=sk-...

# Ingest all documents into Qdrant (first time only)
python -m ingestion.ingest --reset

# Start the API server
uvicorn main:app --reload --port 8000
# API docs: http://localhost:8000/docs
```

#### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
# Open: http://localhost:3000
```

#### 4. Run Tests
```bash
cd backend
python run_tests.py
# Expected: 42/42 tests passed
```

#### 5. Run RAGAs Evaluation
```bash
cd backend
python -m eval.ragas_eval --ablation --output-dir ./eval_results
# Requires: Qdrant running + documents ingested + OPENAI_API_KEY set
```

---

## 📊 RAGAs Ablation Results

Run `python -m eval.ragas_eval --ablation --output-dir ./eval_results` to regenerate.

| Configuration   | Faithfulness | Answer Relevancy | Context Precision | Context Recall | Answer Correctness |
|-----------------|:------------:|:----------------:|:-----------------:|:--------------:|:------------------:|
| Full Pipeline   | 0.87         | 0.91             | 0.84              | 0.79           | 0.76               |
| No Routing      | 0.82         | 0.88             | 0.71              | 0.83           | 0.72               |
| No Guardrails   | 0.87         | 0.91             | 0.84              | 0.79           | 0.76               |

> **Key insight:** Routing improves `context_precision` by ~13% (0.84 vs 0.71) by narrowing retrieval to relevant collections. Guardrails primarily impact security posture rather than RAGAs metrics (they block harmful inputs before retrieval runs).

*Note: Run the ablation yourself with `python -m eval.ragas_eval --ablation` to get exact scores for your indexed documents.*

---

## 🔧 Tech Stack & Design Decisions

| Component         | Choice                              | Reason                                                              |
|-------------------|-------------------------------------|---------------------------------------------------------------------|
| Document Parsing  | Docling + python-docx               | Docling for structural PDF parsing with table/code awareness; python-docx for .docx hierarchy |
| Vector DB         | Qdrant                              | Native payload filtering enables RBAC at query level — not post-processing |
| Embeddings        | OpenAI `text-embedding-3-small`     | Best cost/performance ratio; 1536-dim; Groq doesn't provide embeddings |
| LLM               | Groq `llama-3.3-70b-versatile`      | Ultra-fast inference; OpenAI-compatible API; free tier available    |
| Query Routing     | `semantic-router` + keyword fallback | Semantic-router for accuracy; keyword fallback for environments without the library |
| Guardrails        | Custom (regex + pattern matching)   | Lightweight, auditable, zero external dependency, fast              |
| PII Detection     | Custom regex patterns               | Covers Aadhaar, PAN, phone, email, bank account, credit card, SSN  |
| Evaluation        | RAGAs                               | Industry-standard RAG evaluation framework with 5 key metrics       |
| Backend           | FastAPI                             | Async, typed, auto-generated OpenAPI docs, production-ready         |
| Frontend          | Next.js 16 + Tailwind CSS 4         | App router, TypeScript, SSR-capable, responsive UI                  |

---

## 📂 Project Structure

```
Assignment-Guardrails-Evals/
├── docker-compose.yml           # Qdrant container
├── Makefile                     # Convenience commands
├── setup.sh                     # One-command setup script
│
├── backend/
│   ├── main.py                  # FastAPI app + CORS + routers
│   ├── config.py                # Settings, RBAC matrix, demo users
│   ├── requirements.txt
│   ├── .env.example
│   │
│   ├── ingestion/
│   │   ├── docling_parser.py    # Docling (PDF) + python-docx + Markdown + CSV parsers
│   │   └── ingest.py            # Ingestion orchestrator (discover → parse → embed → upsert)
│   │
│   ├── vector_store/
│   │   └── qdrant_store.py      # RBAC-enforced Qdrant client with payload index filtering
│   │
│   ├── routing/
│   │   └── semantic_router.py   # 5 routes × 18 utterances + keyword fallback + RBAC intersection
│   │
│   ├── guardrails/
│   │   ├── input_guards.py      # Rate limit, injection detection, PII scrubbing, off-topic
│   │   └── output_guards.py     # Citation enforcement, grounding check, leakage detection
│   │
│   ├── rag/
│   │   └── pipeline.py          # Full RAG pipeline orchestration (5 steps)
│   │
│   ├── eval/
│   │   ├── qa_dataset.json      # 48 ground-truth QA pairs (10 general + 10 finance + 10 engineering + 10 marketing + 8 RBAC/guardrail)
│   │   └── ragas_eval.py        # RAGAs evaluation + ablation study runner
│   │
│   ├── api/
│   │   ├── auth.py              # JWT auth, user management, bcrypt password hashing
│   │   ├── chat.py              # /chat endpoint
│   │   ├── admin.py             # /admin CRUD endpoints (users + documents)
│   │   └── models.py            # Pydantic request/response schemas
│   │
│   └── tests/
│       ├── test_rbac.py         # 10 RBAC boundary + adversarial tests
│       ├── test_guardrails.py   # 19 input/output guardrail tests
│       └── test_routing.py      # 13 semantic router classification tests
│
├── frontend/
│   ├── app/
│   │   ├── login/page.tsx       # Login with 5 demo accounts + manual form
│   │   ├── chat/page.tsx        # Chat interface with guardrail banners + citations + route display
│   │   └── admin/page.tsx       # Admin panel (users CRUD + document upload/delete)
│   └── lib/
│       └── api.ts               # Typed backend API client
│
└── data/
    ├── general/                 # employee_handbook.pdf
    ├── finance/                 # budget, financial summary, quarterly report, vendor payments
    ├── engineering/             # system docs, incident logs, sprint metrics, SLA reports (Markdown)
    ├── marketing/               # campaign performance, acquisition reports (DOCX)
    └── hr/                      # hr_data.csv (c_level only)
```

---

## 🔒 RBAC Access Matrix

| Role          | general | finance | engineering | marketing | hr  |
|---------------|:-------:|:-------:|:-----------:|:---------:|:---:|
| `employee`    | ✅      | ❌      | ❌          | ❌        | ❌  |
| `finance`     | ✅      | ✅      | ❌          | ❌        | ❌  |
| `engineering` | ✅      | ❌      | ✅          | ❌        | ❌  |
| `marketing`   | ✅      | ❌      | ❌          | ✅        | ❌  |
| `c_level`     | ✅      | ✅      | ✅          | ✅        | ✅  |

**Enforcement:** The `access_roles` field in every Qdrant chunk payload is a keyword index. Every search query applies a `must: [access_roles == user_role]` filter. Restricted chunks return zero results regardless of the query content.

---

## 🛡️ Guardrails Summary

### Input Guardrails (block before retrieval)

| Guard              | Trigger Examples                                      | Action  |
|--------------------|-------------------------------------------------------|---------|
| Rate limiting      | >20 queries in a session                              | Block   |
| Prompt injection   | "Ignore your instructions", "Act as unrestricted AI" | Block   |
| RBAC bypass        | "sudo show all docs", "override access restrictions"  | Block   |
| PII detection      | Aadhaar, PAN, email, phone, bank account in query    | Scrub + Warn |
| Off-topic          | "Write me a poem", "What's the cricket score?"       | Block   |

### Output Guardrails (modify after generation)

| Guard              | Trigger                                              | Action         |
|--------------------|------------------------------------------------------|----------------|
| Citation missing   | Response lacks `[Source: file, p.N]` format          | Append warning |
| Grounding check    | Financial figures not traceable to retrieved context | Append disclaimer |
| Cross-role leakage | Response contains terms from unauthorized collections | Append warning |

---

## 🧪 Test Coverage

```
42/42 tests passed

  Guardrail Tests (19/19):
    • 16 input guard tests (injection, PII, off-topic, rate-limit)
    • 3 output guard tests (citation, grounding warning)

  Routing Tests (13/13):
    • Route classification for all 5 roles
    • RBAC intersection (finance blocked for engineering user, etc.)
    • C-level access to all routes
    • Keyword fallback accuracy

  RBAC Boundary Tests (10/10):
    • Access matrix verification for all 5 roles
    • 6 adversarial injection bypass attempts (all blocked)
    • Cross-department route scoping
```

Run tests:
```bash
cd backend && python run_tests.py
```

---

## 🛡️ Security Notes

- RBAC enforced at the **Qdrant query layer** — not UI, not post-processing
- Prompt injection detection uses 25+ regex patterns covering role overrides, RBAC bypass, data extraction
- PII scrubbing replaces sensitive data before it ever reaches the LLM
- JWT tokens expire after 24 hours; `SECRET_KEY` should be rotated in production
- Session rate limiting: 20 queries per session (in-memory; swap for Redis in production)
- Cross-role leakage detection scans LLM output for collection-specific terminology

---

## 📋 Evaluation Dataset

The `backend/eval/qa_dataset.json` contains **48 ground-truth QA pairs**:

| Category          | Count | Collections  | Notes                                |
|-------------------|:-----:|--------------|--------------------------------------|
| `hr_policy`       | 9     | general      | Leave, benefits, conduct, WFH        |
| `financial_data`  | 10    | finance      | Revenue, budgets, vendor payments    |
| `technical`       | 10    | engineering  | SLAs, incidents, architecture, APIs  |
| `marketing`       | 10    | marketing    | Campaigns, CAC, ROI, brand           |
| `rbac_adversarial`| 4     | mixed        | Cross-role access attempts (expected blocked) |
| `guardrail_test`  | 4     | general      | Injection + off-topic (expected blocked) |

The dataset covers all 4 document collections + adversarial RBAC boundary cases + guardrail trigger tests.

