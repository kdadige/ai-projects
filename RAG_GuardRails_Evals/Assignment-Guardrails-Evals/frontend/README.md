# Frontend (Next.js)

Minimal UI for FinBot login, chat, and admin pages.

## Prerequisites

- Node.js and npm installed
- Backend API running at `http://localhost:8000` (or set `NEXT_PUBLIC_API_URL`)

## Run locally

```powershell
cd C:\Users\kdadige\OneDrive\git_repos\ai-projects\RAG_GuardRails_Evals\Assignment-Guardrails-Evals\frontend
npm install
npm run dev
```

Open `http://localhost:3000`.

## Build / production check

```powershell
cd C:\Users\kdadige\OneDrive\git_repos\ai-projects\RAG_GuardRails_Evals\Assignment-Guardrails-Evals\frontend
npm run build
npm run start
```

## Quick debug notes

- If API requests fail, check backend is reachable at `http://localhost:8000`.
- To target another backend URL, set `NEXT_PUBLIC_API_URL` before `npm run dev`.
- If `npm` is not recognized, reopen terminal after Node.js install and re-run.

