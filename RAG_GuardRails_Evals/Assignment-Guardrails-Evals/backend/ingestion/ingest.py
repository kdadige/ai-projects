"""
ingest.py - Orchestrates document ingestion: parse → embed → upsert to Qdrant
"""
from __future__ import annotations
import os
import sys
import logging
import asyncio
from pathlib import Path
from typing import Any

# Add parent to path when run as script
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings, COLLECTION_DEFINITIONS, RBAC_MATRIX
from ingestion.docling_parser import parse_document
from vector_store.qdrant_store import QdrantStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Document-to-collection mapping
DOCUMENT_COLLECTIONS = {
    # General
    "employee_handbook.pdf": "general",
    # Finance
    "department_budget_2024.docx": "finance",
    "financial_summary.docx": "finance",
    "quarterly_financial_report.docx": "finance",
    "vendor_payments_summary.docx": "finance",
    # Engineering
    "engineering_master_doc.md": "engineering",
    "incident_report_log.md": "engineering",
    "sprint_metrics_2024.md": "engineering",
    "system_sla_report_2024.md": "engineering",
    # Marketing
    "campaign_performance_data.docx": "marketing",
    "customer_acquisition_report.docx": "marketing",
    "marketing_report_2024.docx": "marketing",
    "marketing_report_q1_2024.docx": "marketing",
    "marketing_report_q2_2024.docx": "marketing",
    "marketing_report_q3_2024.docx": "marketing",
    "marketing_report_q4_2024.docx": "marketing",
    # HR (c_level only)
    "hr_data.csv": "hr",
}


def get_data_directory() -> Path:
    """Find the data directory relative to this file."""
    base = Path(__file__).parent.parent.parent / "data"
    if base.exists():
        return base
    # Try env variable
    env_data = os.getenv("DATA_DIR", "")
    if env_data and Path(env_data).exists():
        return Path(env_data)
    raise FileNotFoundError(f"Data directory not found at {base}")


def discover_documents(data_dir: Path) -> list[tuple[Path, str]]:
    """Discover all documents in the data directory and map to collections."""
    docs = []
    for file_path in data_dir.rglob("*"):
        if file_path.is_file() and file_path.suffix.lower() in {".pdf", ".docx", ".doc", ".md", ".csv"}:
            filename = file_path.name
            collection = DOCUMENT_COLLECTIONS.get(filename)
            if collection is None:
                # Try to infer from parent directory
                parent = file_path.parent.name.lower()
                if parent in COLLECTION_DEFINITIONS:
                    collection = parent
                else:
                    logger.warning(f"Cannot determine collection for {filename}, skipping")
                    continue
            docs.append((file_path, collection))
            logger.info(f"Found: {filename} → collection={collection}")
    return docs


def enrich_chunks(chunks: list[dict], collection: str, file_path: Path) -> list[dict]:
    """Add collection and access_roles to all chunks."""
    access_roles = COLLECTION_DEFINITIONS[collection]["access_roles"]
    for chunk in chunks:
        chunk["collection"] = collection
        chunk["access_roles"] = access_roles
        if not chunk.get("source_document"):
            chunk["source_document"] = file_path.name
    return chunks


async def ingest_all(reset: bool = False):
    """Main ingestion pipeline: discover → parse → embed → upsert."""
    data_dir = get_data_directory()
    logger.info(f"Data directory: {data_dir}")

    store = QdrantStore()
    await store.initialize(reset=reset)

    documents = discover_documents(data_dir)
    logger.info(f"Found {len(documents)} documents to ingest")

    total_chunks = 0
    for file_path, collection in documents:
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing: {file_path.name} (collection={collection})")

        try:
            # Parse document
            chunks = parse_document(str(file_path))
            logger.info(f"  Parsed {len(chunks)} chunks")

            # Enrich with metadata
            chunks = enrich_chunks(chunks, collection, file_path)

            # Upsert to Qdrant
            await store.upsert_chunks(chunks)
            total_chunks += len(chunks)
            logger.info(f"  Upserted {len(chunks)} chunks to Qdrant")

        except Exception as e:
            logger.error(f"  Failed to process {file_path.name}: {e}", exc_info=True)

    logger.info(f"\n{'='*60}")
    logger.info(f"Ingestion complete! Total chunks: {total_chunks}")

    # Print stats per collection
    stats = await store.get_collection_stats()
    logger.info(f"Collection stats: {stats}")


async def ingest_single_document(file_path: str, collection: str):
    """Ingest a single document (used by admin API)."""
    path = Path(file_path)
    if collection not in COLLECTION_DEFINITIONS:
        raise ValueError(f"Unknown collection: {collection}")

    store = QdrantStore()
    await store.initialize(reset=False)

    chunks = parse_document(file_path)
    chunks = enrich_chunks(chunks, collection, path)
    await store.upsert_chunks(chunks)

    return len(chunks)


async def remove_document(source_document: str):
    """Remove all chunks for a specific document."""
    store = QdrantStore()
    await store.initialize(reset=False)
    await store.delete_by_source(source_document)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ingest documents into Qdrant")
    parser.add_argument("--reset", action="store_true", help="Reset the collection before ingestion")
    args = parser.parse_args()
    asyncio.run(ingest_all(reset=args.reset))

