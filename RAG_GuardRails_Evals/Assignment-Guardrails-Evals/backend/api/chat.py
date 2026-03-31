"""
chat.py - Chat API endpoint
"""
from __future__ import annotations
import logging
from fastapi import APIRouter, Depends, HTTPException

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.models import ChatRequest, ChatResponse, GuardrailWarning, CitationInfo, RetrievedChunk
from api.auth import get_current_user
from rag.pipeline import get_pipeline
from guardrails.input_guards import get_session_count

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Main chat endpoint. Runs the full RAG pipeline with guardrails.
    """
    pipeline = get_pipeline()

    result = await pipeline.query(
        question=request.question,
        user_role=current_user["role"],
        session_id=current_user["username"],
        top_k=request.top_k,
    )

    # Get current session count
    session_count = get_session_count(current_user["username"])
    result["session_query_count"] = session_count

    return ChatResponse(
        answer=result["answer"],
        route=result["route"],
        target_collections=result["target_collections"],
        user_role=result["user_role"],
        accessible_collections=result["accessible_collections"],
        retrieved_chunks=[
            RetrievedChunk(**c) for c in result["retrieved_chunks"]
        ],
        input_guardrail_triggered=result["input_guardrail_triggered"],
        output_guardrail_triggered=result["output_guardrail_triggered"],
        guardrail_warnings=[
            GuardrailWarning(**w) for w in result["guardrail_warnings"]
        ],
        citations=[
            CitationInfo(**c) for c in result["citations"]
        ],
        session_query_count=session_count,
    )

