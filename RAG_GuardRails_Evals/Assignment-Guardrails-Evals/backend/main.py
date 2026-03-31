"""
main.py - FastAPI application entrypoint for FinBot
"""
from __future__ import annotations
import logging
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from api.auth import router as auth_router
from api.chat import router as chat_router
from api.admin import router as admin_router
from config import settings, RBAC_MATRIX, COLLECTION_DEFINITIONS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="FinBot API",
    description="Advanced RAG with RBAC, Guardrails & Evals for FinSolve Technologies",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS - allow the NextJS frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(admin_router)


@app.get("/")
async def root():
    return {
        "name": "FinBot API",
        "version": "1.0.0",
        "description": "Advanced RAG assistant for FinSolve Technologies",
        "status": "running",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/rbac-matrix")
async def rbac_matrix():
    """Public endpoint showing the RBAC matrix."""
    return {
        "rbac_matrix": RBAC_MATRIX,
        "collections": {
            name: {
                "description": config["description"],
                "access_roles": config["access_roles"],
            }
            for name, config in COLLECTION_DEFINITIONS.items()
        },
    }

