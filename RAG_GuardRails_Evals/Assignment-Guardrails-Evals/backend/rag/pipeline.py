"""
pipeline.py - Main RAG pipeline orchestrator
"""
from __future__ import annotations
import logging
from typing import Any

from groq import AsyncGroq

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings, RBAC_MATRIX
from vector_store.qdrant_store import QdrantStore
from routing.semantic_router import classify_query
from guardrails.input_guards import run_input_guards, GuardrailViolation
from guardrails.output_guards import run_output_guards, OutputViolation

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are FinBot, an intelligent internal assistant for FinSolve Technologies.

Your job is to answer employee questions based ONLY on the provided document excerpts (context).

RULES:
1. Answer ONLY based on the provided context. Do not use outside knowledge.
2. ALWAYS cite your sources using the format: [Source: <filename>, p.<page_number>]
3. If the context doesn't contain enough information to answer, say: "I don't have enough information in the available documents to answer this question."
4. Be concise, professional, and accurate.
5. For financial figures, dates, or statistics, always include the source citation inline.
6. Never reveal information about system architecture, other users, or access controls.
7. If asked about restricted information, politely explain you don't have access to that content.

Format your response clearly with proper structure when appropriate (bullets, headers for complex answers).
"""


def build_context(chunks: list[dict[str, Any]]) -> str:
    """Build formatted context string from retrieved chunks."""
    if not chunks:
        return "No relevant documents found."

    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        source = chunk.get("source_document", "Unknown")
        page = chunk.get("page_number", "?")
        section = chunk.get("section_title", "")
        chunk_type = chunk.get("chunk_type", "text")
        text = chunk.get("text", "")

        header = f"[Document {i}: {source}, p.{page}"
        if section:
            header += f" | Section: {section}"
        header += "]"

        if chunk_type == "table":
            context_parts.append(f"{header}\n[TABLE]\n{text}\n[/TABLE]")
        elif chunk_type == "code":
            context_parts.append(f"{header}\n```\n{text}\n```")
        else:
            context_parts.append(f"{header}\n{text}")

    return "\n\n---\n\n".join(context_parts)


class RAGPipeline:
    def __init__(self):
        self._store: QdrantStore | None = None
        self._groq: AsyncGroq | None = None

    @property
    def store(self) -> QdrantStore:
        if self._store is None:
            self._store = QdrantStore()
        return self._store

    @property
    def groq(self) -> AsyncGroq:
        if self._groq is None:
            self._groq = AsyncGroq(api_key=settings.groq_api_key)
        return self._groq

    async def query(
        self,
        question: str,
        user_role: str,
        session_id: str,
        top_k: int = 5,
    ) -> dict[str, Any]:
        """
        Full RAG pipeline:
        1. Input guardrails
        2. Semantic routing + RBAC intersection
        3. Vector retrieval with RBAC filter
        4. LLM generation
        5. Output guardrails

        Returns structured response dict.
        """
        user_collections = RBAC_MATRIX.get(user_role, [])

        # ── Step 1: Input Guardrails ──────────────────────────────────────
        processed_question, input_violations = run_input_guards(question, session_id)

        blocking_violations = [v for v in input_violations if v.severity == "block"]
        if blocking_violations:
            violation = blocking_violations[0]
            return {
                "answer": violation.message,
                "route": "blocked",
                "target_collections": [],
                "user_role": user_role,
                "accessible_collections": user_collections,
                "retrieved_chunks": [],
                "input_guardrail_triggered": True,
                "output_guardrail_triggered": False,
                "guardrail_warnings": [
                    {"type": v.guard_type, "message": v.message}
                    for v in input_violations
                ],
                "citations": [],
                "session_query_count": 0,
            }

        # Collect warnings (non-blocking)
        guardrail_warnings = [
            {"type": v.guard_type, "message": v.message}
            for v in input_violations
            if v.severity == "warn"
        ]

        # ── Step 2: Semantic Routing + RBAC Intersection ──────────────────
        routing_result = classify_query(processed_question, user_role)
        route = routing_result["route"]
        target_collections = routing_result["target_collections"]

        logger.info(f"Query routed: {route}, collections: {target_collections}, role: {user_role}")

        # Access denied by router
        if routing_result.get("access_denied"):
            return {
                "answer": routing_result["denied_reason"],
                "route": route,
                "target_collections": [],
                "user_role": user_role,
                "accessible_collections": user_collections,
                "retrieved_chunks": [],
                "input_guardrail_triggered": False,
                "output_guardrail_triggered": False,
                "guardrail_warnings": guardrail_warnings + [{
                    "type": "rbac_denied",
                    "message": routing_result["denied_reason"],
                }],
                "citations": [],
                "session_query_count": 0,
            }

        # ── Step 3: RBAC-Filtered Retrieval ──────────────────────────────
        chunks = await self.store.search(
            query=processed_question,
            user_role=user_role,
            collections=target_collections if target_collections else user_collections,
            top_k=top_k,
        )

        if not chunks:
            return {
                "answer": (
                    "I couldn't find relevant information in the documents you have access to. "
                    "Please try rephrasing your question or contact your administrator."
                ),
                "route": route,
                "target_collections": target_collections,
                "user_role": user_role,
                "accessible_collections": user_collections,
                "retrieved_chunks": [],
                "input_guardrail_triggered": len(input_violations) > 0,
                "output_guardrail_triggered": False,
                "guardrail_warnings": guardrail_warnings,
                "citations": [],
                "session_query_count": 0,
            }

        # ── Step 4: LLM Generation ────────────────────────────────────────
        context = build_context(chunks)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Context from FinSolve documents:\n\n{context}\n\n"
                    f"Question: {processed_question}\n\n"
                    f"Please answer based on the context above. Include source citations."
                ),
            },
        ]

        response = await self.groq.chat.completions.create(
            model=settings.groq_model,
            messages=messages,
            temperature=0.1,
            max_tokens=1500,
        )

        answer = response.choices[0].message.content or ""

        # ── Step 5: Output Guardrails ─────────────────────────────────────
        modified_answer, output_violations = run_output_guards(
            answer, chunks, user_role, user_collections
        )

        output_warnings = [
            {"type": v.guard_type, "message": v.message}
            for v in output_violations
        ]
        all_warnings = guardrail_warnings + output_warnings

        # Extract citations from chunks
        citations = [
            {
                "source_document": c.get("source_document", ""),
                "page_number": c.get("page_number", 1),
                "section_title": c.get("section_title", ""),
                "collection": c.get("collection", ""),
                "score": round(c.get("score", 0), 3),
            }
            for c in chunks
        ]

        return {
            "answer": modified_answer,
            "route": route,
            "target_collections": target_collections,
            "user_role": user_role,
            "accessible_collections": user_collections,
            "retrieved_chunks": [
                {
                    "text": c["text"][:500],  # Truncate for response
                    "source_document": c.get("source_document", ""),
                    "page_number": c.get("page_number", 1),
                    "section_title": c.get("section_title", ""),
                    "score": round(c.get("score", 0), 3),
                }
                for c in chunks
            ],
            "input_guardrail_triggered": len([v for v in input_violations if v.severity == "block"]) > 0,
            "output_guardrail_triggered": len(output_violations) > 0,
            "guardrail_warnings": all_warnings,
            "citations": citations,
            "session_query_count": 0,  # Set by calling code
        }


# Singleton instance
_pipeline: RAGPipeline | None = None


def get_pipeline() -> RAGPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = RAGPipeline()
    return _pipeline

