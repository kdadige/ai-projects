"""
qdrant_store.py - Qdrant vector store with RBAC enforcement at retrieval layer
"""
from __future__ import annotations
import logging
import uuid
from typing import Any

from openai import AsyncOpenAI
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchAny,
    MatchValue,
    PayloadSchemaType,
)

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import settings

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 1536  # text-embedding-3-small dimension


class QdrantStore:
    def __init__(self):
        self._client: AsyncQdrantClient | None = None
        self._openai: AsyncOpenAI | None = None
        self._collection = settings.qdrant_collection

    @property
    def client(self) -> AsyncQdrantClient:
        if self._client is None:
            kwargs = {"url": settings.qdrant_url}
            if settings.qdrant_api_key:
                kwargs["api_key"] = settings.qdrant_api_key
            self._client = AsyncQdrantClient(**kwargs)
        return self._client

    @property
    def openai(self) -> AsyncOpenAI:
        if self._openai is None:
            self._openai = AsyncOpenAI(api_key=settings.openai_api_key)
        return self._openai

    async def initialize(self, reset: bool = False):
        """Create or verify the Qdrant collection exists."""
        existing = await self.client.get_collections()
        collection_names = [c.name for c in existing.collections]

        if reset and self._collection in collection_names:
            await self.client.delete_collection(self._collection)
            logger.info(f"Deleted collection {self._collection}")
            collection_names.remove(self._collection)

        if self._collection not in collection_names:
            await self.client.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(
                    size=EMBEDDING_DIM,
                    distance=Distance.COSINE,
                ),
            )
            # Create payload indexes for fast filtering
            await self.client.create_payload_index(
                collection_name=self._collection,
                field_name="access_roles",
                field_schema=PayloadSchemaType.KEYWORD,
            )
            await self.client.create_payload_index(
                collection_name=self._collection,
                field_name="collection",
                field_schema=PayloadSchemaType.KEYWORD,
            )
            await self.client.create_payload_index(
                collection_name=self._collection,
                field_name="source_document",
                field_schema=PayloadSchemaType.KEYWORD,
            )
            logger.info(f"Created collection {self._collection} with payload indexes")
        else:
            logger.info(f"Collection {self._collection} already exists")

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts using OpenAI."""
        # Process in batches of 100
        all_embeddings = []
        batch_size = 100
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            # Clean texts
            batch = [t.replace("\n", " ").strip() for t in batch]
            batch = [t if t else "empty" for t in batch]

            response = await self.openai.embeddings.create(
                model=settings.embedding_model,
                input=batch,
            )
            batch_embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(batch_embeddings)
        return all_embeddings

    async def upsert_chunks(self, chunks: list[dict[str, Any]]):
        """Embed and upsert a list of chunks into Qdrant."""
        if not chunks:
            return

        texts = [c["text"] for c in chunks]
        embeddings = await self.embed_texts(texts)

        points = []
        for chunk, embedding in zip(chunks, embeddings):
            chunk_id = chunk.get("chunk_id") or str(uuid.uuid4())
            # Qdrant requires UUID or integer IDs
            try:
                point_id = chunk_id  # Use string UUID directly
            except Exception:
                point_id = str(uuid.uuid4())

            payload = {
                "chunk_id": chunk_id,
                "parent_chunk_id": chunk.get("parent_chunk_id"),
                "text": chunk["text"],
                "chunk_type": chunk.get("chunk_type", "text"),
                "section_title": chunk.get("section_title", ""),
                "page_number": chunk.get("page_number", 1),
                "source_document": chunk.get("source_document", ""),
                "collection": chunk.get("collection", ""),
                "access_roles": chunk.get("access_roles", []),
                "level": chunk.get("level", 1),
            }

            points.append(PointStruct(id=point_id, vector=embedding, payload=payload))

        # Upsert in batches
        batch_size = 50
        for i in range(0, len(points), batch_size):
            batch = points[i:i+batch_size]
            await self.client.upsert(
                collection_name=self._collection,
                points=batch,
            )
        logger.info(f"Upserted {len(points)} points to Qdrant")

    async def search(
        self,
        query: str,
        user_role: str,
        collections: list[str] | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """
        RBAC-enforced semantic search.

        The RBAC filter is applied at the Qdrant query level — restricted chunks
        are never surfaced to the application even if the query bypasses other filters.
        """
        # Embed query
        query_embedding = await self.embed_texts([query])
        query_vector = query_embedding[0]

        # Build RBAC filter — user's role must be in the chunk's access_roles
        # This is the core RBAC enforcement mechanism
        rbac_filter = Filter(
            must=[
                FieldCondition(
                    key="access_roles",
                    match=MatchValue(value=user_role),
                )
            ]
        )

        # Optionally restrict to specific collections
        if collections:
            collection_filter = Filter(
                must=[
                    FieldCondition(
                        key="collection",
                        match=MatchAny(any=collections),
                    )
                ]
            )
            # Combine filters
            final_filter = Filter(
                must=[
                    rbac_filter,
                    collection_filter,
                ]
            )
        else:
            final_filter = rbac_filter

        results = await self.client.search(
            collection_name=self._collection,
            query_vector=query_vector,
            query_filter=final_filter,
            limit=top_k,
            with_payload=True,
        )

        return [
            {
                "score": r.score,
                "text": r.payload.get("text", ""),
                "chunk_id": r.payload.get("chunk_id", ""),
                "parent_chunk_id": r.payload.get("parent_chunk_id"),
                "chunk_type": r.payload.get("chunk_type", "text"),
                "section_title": r.payload.get("section_title", ""),
                "page_number": r.payload.get("page_number", 1),
                "source_document": r.payload.get("source_document", ""),
                "collection": r.payload.get("collection", ""),
                "access_roles": r.payload.get("access_roles", []),
            }
            for r in results
        ]

    async def get_collection_stats(self) -> dict:
        """Get statistics about indexed documents."""
        try:
            info = await self.client.get_collection(self._collection)
            count_result = await self.client.count(self._collection)
            return {
                "total_points": count_result.count,
                "collection_name": self._collection,
                "status": str(info.status),
            }
        except Exception as e:
            return {"error": str(e)}

    async def delete_by_source(self, source_document: str):
        """Delete all chunks from a specific source document."""
        from qdrant_client.models import FilterSelector

        await self.client.delete(
            collection_name=self._collection,
            points_selector=FilterSelector(
                filter=Filter(
                    must=[
                        FieldCondition(
                            key="source_document",
                            match=MatchValue(value=source_document),
                        )
                    ]
                )
            ),
        )
        logger.info(f"Deleted chunks for source document: {source_document}")

    async def list_documents(self) -> list[dict]:
        """List all unique source documents in the store."""
        # Scroll through all points and collect unique documents
        docs: dict[str, dict] = {}
        offset = None

        while True:
            result, next_offset = await self.client.scroll(
                collection_name=self._collection,
                limit=100,
                offset=offset,
                with_payload=["source_document", "collection", "access_roles"],
                with_vectors=False,
            )

            for point in result:
                src = point.payload.get("source_document", "")
                if src and src not in docs:
                    docs[src] = {
                        "source_document": src,
                        "collection": point.payload.get("collection", ""),
                        "access_roles": point.payload.get("access_roles", []),
                    }

            if next_offset is None:
                break
            offset = next_offset

        return list(docs.values())

