"""API routes for document upload, listing, and deletion."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.api.deps import get_document_service
from app.models.schemas import (
    DocumentDeleteResponse,
    DocumentListResponse,
    DocumentUploadResponse,
)
from app.services.document import DocumentService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    service: DocumentService = Depends(get_document_service),
) -> DocumentListResponse:
    """
    List all indexed documents in the vector store.

    Returns a list of documents with metadata including:
    - Document ID
    - Filename
    - Status
    - Indexed timestamp
    - Number of chunks
    """
    logger.info("Listing all documents")
    return service.list_documents()


@router.post("/", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    service: DocumentService = Depends(get_document_service),
) -> DocumentUploadResponse:
    """
    Upload and index a new document.

    Supports the following file formats:
    - JSON (.json)
    - CSV (.csv)
    - Excel (.xlsx, .xls)
    - Plain text (.txt)
    - PDF (.pdf, text-based)

    The document will be:
    1. Validated for format and size
    2. Processed and parsed
    3. Anonymized (PII removal)
    4. Chunked for optimal retrieval
    5. Embedded using sentence transformers
    6. Indexed in the vector store

    Returns:
    - Document ID
    - Status (success/error)
    - Message
    - Number of chunks created
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    logger.info(f"Uploading document: {file.filename}")

    # Read file content
    content = await file.read()

    # Process document
    result = await service.upload_document(filename=file.filename, content=content)

    # Return appropriate status code
    if result.status == "error":
        raise HTTPException(status_code=400, detail=result.message)

    return result


@router.delete("/{doc_id}", response_model=DocumentDeleteResponse)
async def delete_document(
    doc_id: str,
    service: DocumentService = Depends(get_document_service),
) -> DocumentDeleteResponse:
    """
    Delete a document and all its chunks from the vector store.

    Args:
        doc_id: The document ID to delete

    Returns:
    - Status (success/error)
    - Message with deletion details
    """
    logger.info(f"Deleting document: {doc_id}")

    result = service.delete_document(doc_id)

    if result.status == "error":
        raise HTTPException(status_code=404, detail=result.message)

    return result
