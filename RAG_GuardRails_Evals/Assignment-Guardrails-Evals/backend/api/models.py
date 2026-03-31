"""
models.py - Pydantic request/response schemas
"""
from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field


# ─── Auth ────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    full_name: str
    role: str
    department: str
    accessible_collections: list[str]


class UserInfo(BaseModel):
    username: str
    full_name: str
    role: str
    department: str
    accessible_collections: list[str]


# ─── Chat ────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)


class CitationInfo(BaseModel):
    source_document: str
    page_number: int
    section_title: str
    collection: str
    score: float


class RetrievedChunk(BaseModel):
    text: str
    source_document: str
    page_number: int
    section_title: str
    score: float


class GuardrailWarning(BaseModel):
    type: str
    message: str


class ChatResponse(BaseModel):
    answer: str
    route: str
    target_collections: list[str]
    user_role: str
    accessible_collections: list[str]
    retrieved_chunks: list[RetrievedChunk]
    input_guardrail_triggered: bool
    output_guardrail_triggered: bool
    guardrail_warnings: list[GuardrailWarning]
    citations: list[CitationInfo]
    session_query_count: int


# ─── Admin ───────────────────────────────────────────────────────────────────

class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    full_name: str = Field(..., min_length=2, max_length=100)
    role: str = Field(..., pattern="^(employee|finance|engineering|marketing|c_level)$")
    department: str = Field(..., min_length=2, max_length=100)
    password: str = Field(..., min_length=6, max_length=100)


class UpdateUserRequest(BaseModel):
    full_name: str | None = None
    role: str | None = None
    department: str | None = None
    password: str | None = None


class UserRecord(BaseModel):
    username: str
    full_name: str
    role: str
    department: str
    accessible_collections: list[str]


class DocumentRecord(BaseModel):
    source_document: str
    collection: str
    access_roles: list[str]


class IngestDocumentRequest(BaseModel):
    collection: str = Field(..., pattern="^(general|finance|engineering|marketing|hr)$")


class CollectionStats(BaseModel):
    total_points: int
    collection_name: str
    status: str

