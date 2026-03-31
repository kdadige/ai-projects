"""
config.py - Configuration, RBAC matrix, and demo users for FinBot
"""
from __future__ import annotations
import os

# Load .env file if present (before reading env vars)
from pathlib import Path
_env_file = Path(__file__).parent / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _key, _, _val = _line.partition("=")
            os.environ.setdefault(_key.strip(), _val.strip())

try:
    from pydantic_settings import BaseSettings

    class Settings(BaseSettings):
        model_config = {
            "env_file": ".env",
            "env_file_encoding": "utf-8",
            "extra": "ignore",
        }

        # ── Groq LLM ─────────────────────────────────────────────
        groq_api_key: str = ""
        groq_model: str = "llama-3.3-70b-versatile"

        # ── OpenAI (embeddings only) ──────────────────────────────
        openai_api_key: str = ""
        embedding_model: str = "text-embedding-3-small"

        # ── Qdrant ────────────────────────────────────────────────
        qdrant_url: str = "http://localhost:6333"
        qdrant_api_key: str = ""
        qdrant_collection: str = "finbot_docs"

        # ── Auth ──────────────────────────────────────────────────
        secret_key: str = "finbot-secret-key-change-in-production-2024"
        algorithm: str = "HS256"
        access_token_expire_minutes: int = 60 * 24  # 24 hours

        # ── Rate limiting ─────────────────────────────────────────
        max_queries_per_session: int = 20

        # ── Data paths ────────────────────────────────────────────
        data_dir: str = "../data"

    settings = Settings()

except ImportError:
    # Fallback: simple settings object from environment variables
    class _SimpleSettings:  # type: ignore
        groq_api_key: str = os.getenv("GROQ_API_KEY", "")
        groq_model: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
        embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        qdrant_url: str = os.getenv("QDRANT_URL", "http://localhost:6333")
        qdrant_api_key: str = os.getenv("QDRANT_API_KEY", "")
        qdrant_collection: str = os.getenv("QDRANT_COLLECTION", "finbot_docs")
        secret_key: str = os.getenv("SECRET_KEY", "finbot-secret-key-change-in-production-2024")
        algorithm: str = "HS256"
        access_token_expire_minutes: int = 60 * 24
        max_queries_per_session: int = 20
        data_dir: str = os.getenv("DATA_DIR", "../data")

    settings = _SimpleSettings()

# ─────────────────────────────────────────────
# RBAC Matrix
# ─────────────────────────────────────────────
RBAC_MATRIX: dict[str, list[str]] = {
    "employee": ["general"],
    "finance": ["finance", "general"],
    "engineering": ["engineering", "general"],
    "marketing": ["marketing", "general"],
    "c_level": ["general", "finance", "engineering", "marketing", "hr"],
}

# Collections that exist in the system
ALL_COLLECTIONS = ["general", "finance", "engineering", "marketing", "hr"]

# ─────────────────────────────────────────────
# Document Collection Definitions
# ─────────────────────────────────────────────
COLLECTION_DEFINITIONS = {
    "general": {
        "access_roles": ["employee", "finance", "engineering", "marketing", "c_level"],
        "description": "Company policies, HR handbook, general FAQs",
    },
    "finance": {
        "access_roles": ["finance", "c_level"],
        "description": "Financial reports, budgets, investor documents",
    },
    "engineering": {
        "access_roles": ["engineering", "c_level"],
        "description": "Technical specs, architecture docs, runbooks",
    },
    "marketing": {
        "access_roles": ["marketing", "c_level"],
        "description": "Campaign reports, brand guidelines, market research",
    },
    "hr": {
        "access_roles": ["c_level"],
        "description": "Employee records, HR data (confidential)",
    },
}

# ─────────────────────────────────────────────
# Demo Users
# ─────────────────────────────────────────────
# Passwords are bcrypt-hashed versions of simple demo passwords
# Plain text: employee123, finance123, engineering123, marketing123, clevel123
DEMO_USERS = {
    "alice_employee": {
        "username": "alice_employee",
        "full_name": "Alice Johnson",
        "role": "employee",
        "department": "General",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # employee123 - will be replaced at startup
        "plain_password": "employee123",
    },
    "bob_finance": {
        "username": "bob_finance",
        "full_name": "Bob Smith",
        "role": "finance",
        "department": "Finance",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
        "plain_password": "finance123",
    },
    "carol_engineering": {
        "username": "carol_engineering",
        "full_name": "Carol Davis",
        "role": "engineering",
        "department": "Engineering",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
        "plain_password": "engineering123",
    },
    "dave_marketing": {
        "username": "dave_marketing",
        "full_name": "Dave Wilson",
        "role": "marketing",
        "department": "Marketing",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
        "plain_password": "marketing123",
    },
    "eve_clevel": {
        "username": "eve_clevel",
        "full_name": "Eve Thompson",
        "role": "c_level",
        "department": "Executive",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
        "plain_password": "clevel123",
    },
}

# Admin user
ADMIN_USER = {
    "username": "admin",
    "full_name": "System Administrator",
    "role": "c_level",
    "department": "IT",
    "plain_password": "admin123",
}

