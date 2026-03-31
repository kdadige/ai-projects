"""
admin.py - Admin API endpoints for user and document management
"""
from __future__ import annotations
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.models import (
    CreateUserRequest, UpdateUserRequest, UserRecord, DocumentRecord,
    IngestDocumentRequest, CollectionStats
)
from api.auth import (
    get_current_user, require_admin, create_user, update_user,
    delete_user, list_users,
)
from vector_store.qdrant_store import QdrantStore
from ingestion.ingest import ingest_single_document, remove_document
from config import RBAC_MATRIX as RBAC

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])


# ─── User Management ──────────────────────────────────────────────────────────

@router.get("/users", response_model=list[UserRecord])
async def get_users(current_user: dict = Depends(require_admin)):
    """List all users (admin only)."""
    users = list_users()
    return [
        UserRecord(
            username=u["username"],
            full_name=u["full_name"],
            role=u["role"],
            department=u["department"],
            accessible_collections=RBAC.get(u["role"], []),
        )
        for u in users
    ]


@router.post("/users", response_model=UserRecord, status_code=status.HTTP_201_CREATED)
async def add_user(
    request: CreateUserRequest,
    current_user: dict = Depends(require_admin),
):
    """Create a new user (admin only)."""
    try:
        user = create_user(
            username=request.username,
            full_name=request.full_name,
            role=request.role,
            department=request.department,
            password=request.password,
        )
        return UserRecord(
            username=user["username"],
            full_name=user["full_name"],
            role=user["role"],
            department=user["department"],
            accessible_collections=RBAC.get(user["role"], []),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch("/users/{username}", response_model=UserRecord)
async def edit_user(
    username: str,
    request: UpdateUserRequest,
    current_user: dict = Depends(require_admin),
):
    """Update a user (admin only)."""
    try:
        updates = request.model_dump(exclude_none=True)
        user = update_user(username, updates)
        return UserRecord(
            username=user["username"],
            full_name=user["full_name"],
            role=user["role"],
            department=user["department"],
            accessible_collections=RBAC.get(user["role"], []),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/users/{username}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_user(
    username: str,
    current_user: dict = Depends(require_admin),
):
    """Delete a user (admin only)."""
    if username == current_user["username"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )
    try:
        delete_user(username)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ─── Document Management ──────────────────────────────────────────────────────

@router.get("/documents", response_model=list[DocumentRecord])
async def get_documents(current_user: dict = Depends(require_admin)):
    """List all indexed documents (admin only)."""
    store = QdrantStore()
    docs = await store.list_documents()
    return [DocumentRecord(**d) for d in docs]


@router.post("/documents/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    collection: str = Form(...),
    current_user: dict = Depends(require_admin),
):
    """Upload and index a new document (admin only)."""
    from config import COLLECTION_DEFINITIONS

    if collection not in COLLECTION_DEFINITIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid collection. Must be one of: {list(COLLECTION_DEFINITIONS.keys())}",
        )

    # Validate file type
    allowed_extensions = {".pdf", ".docx", ".doc", ".md", ".csv", ".txt"}
    suffix = Path(file.filename).suffix.lower()
    if suffix not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {suffix}. Allowed: {allowed_extensions}",
        )

    # Save file to temp location
    upload_dir = Path("/tmp/finbot_uploads")
    upload_dir.mkdir(exist_ok=True)
    file_path = upload_dir / file.filename

    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    try:
        chunk_count = await ingest_single_document(str(file_path), collection)
        return {
            "message": f"Successfully ingested {file.filename} into {collection} collection",
            "chunks_created": chunk_count,
            "source_document": file.filename,
            "collection": collection,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest document: {str(e)}",
        )
    finally:
        # Clean up temp file
        if file_path.exists():
            file_path.unlink()


@router.delete("/documents/{source_document}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    source_document: str,
    current_user: dict = Depends(require_admin),
):
    """Remove a document from the index (admin only)."""
    try:
        await remove_document(source_document)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {str(e)}",
        )


@router.get("/stats", response_model=CollectionStats)
async def get_stats(current_user: dict = Depends(require_admin)):
    """Get vector store statistics (admin only)."""
    store = QdrantStore()
    stats = await store.get_collection_stats()
    if "error" in stats:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=stats["error"],
        )
    return CollectionStats(**stats)

