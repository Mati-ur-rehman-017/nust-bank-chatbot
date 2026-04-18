"""Document processing service for uploading, indexing, and managing documents."""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import BinaryIO

from app.data.preprocessing import (
    anonymize_pii,
    chunk_document,
    load_documents_from_path,
)
from app.data.vectorstore import VectorStore
from app.models.schemas import (
    DocumentDeleteResponse,
    DocumentListResponse,
    DocumentResponse,
    DocumentUploadResponse,
)
from app.services.embedding import EmbeddingService

logger = logging.getLogger(__name__)

# Allowed file extensions for upload
ALLOWED_EXTENSIONS = {".json", ".csv", ".xlsx", ".xls", ".txt", ".pdf"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10MB


class DocumentService:
    """Service for managing document uploads and indexing."""

    def __init__(
        self, vector_store: VectorStore, embedding_service: EmbeddingService
    ) -> None:
        self.vector_store = vector_store
        self.embedding_service = embedding_service
        self.upload_dir = Path("./data/uploads")
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    async def upload_document(
        self, filename: str, content: bytes
    ) -> DocumentUploadResponse:
        """
        Process and index an uploaded document.

        Flow:
        1. Validate file format and size
        2. Save file to upload directory
        3. Load using preprocessing functions
        4. Anonymize PII
        5. Chunk documents
        6. Generate embeddings
        7. Store in vector store
        """
        try:
            # Validate file extension
            file_path = Path(filename)
            if file_path.suffix.lower() not in ALLOWED_EXTENSIONS:
                return DocumentUploadResponse(
                    id="",
                    status="error",
                    message=f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
                )

            # Validate file size
            if len(content) > MAX_FILE_SIZE_BYTES:
                return DocumentUploadResponse(
                    id="",
                    status="error",
                    message=f"File too large. Maximum size: {MAX_FILE_SIZE_BYTES // 1024 // 1024}MB",
                )

            # Save file to uploads directory
            upload_path = self.upload_dir / filename
            upload_path.write_bytes(content)
            logger.info(f"Saved uploaded file to {upload_path}")

            # Load documents using preprocessing
            documents = load_documents_from_path(upload_path)
            if not documents:
                return DocumentUploadResponse(
                    id="",
                    status="error",
                    message="No valid documents found in uploaded file",
                )

            total_chunks = 0
            indexed_at = datetime.now().isoformat()

            # Process each document
            for document in documents:
                # Anonymize PII
                anonymized_text = anonymize_pii(document.text)
                document_with_anon = type(document)(
                    id=document.id, text=anonymized_text, metadata=document.metadata
                )

                # Chunk the document
                chunks = chunk_document(document_with_anon)

                # Generate embeddings and store
                for chunk in chunks:
                    # Generate embedding
                    embedding = self.embedding_service.embed(chunk.text)

                    # Add document metadata
                    metadata = {
                        **chunk.metadata,
                        "document_id": document.id,
                        "filename": filename,
                        "indexed_at": indexed_at,
                    }

                    # Store in vector database
                    self.vector_store.add_document(
                        doc_id=chunk.id,
                        text=chunk.text,
                        embedding=embedding,
                        metadata=metadata,
                    )
                    total_chunks += 1

            logger.info(
                f"Successfully indexed {len(documents)} documents "
                f"with {total_chunks} chunks from {filename}"
            )

            return DocumentUploadResponse(
                id=documents[0].id if documents else "",
                status="success",
                message=f"Successfully indexed {len(documents)} documents",
                chunks_created=total_chunks,
            )

        except Exception as e:
            logger.error(f"Error processing document {filename}: {e}", exc_info=True)
            return DocumentUploadResponse(
                id="", status="error", message=f"Failed to process document: {str(e)}"
            )

    def list_documents(self) -> DocumentListResponse:
        """
        List all indexed documents.

        Since ChromaDB doesn't natively track documents (only chunks),
        we query all items and group by document_id in metadata.
        """
        try:
            # Get all documents from the collection
            # ChromaDB doesn't have a direct "get all" method, so we use a workaround
            collection = self.vector_store._collection
            all_items = collection.get(include=["metadatas"])

            if not all_items["ids"]:
                return DocumentListResponse(documents=[], total=0)

            # Group chunks by document_id
            doc_map: dict[str, dict] = {}
            for idx, item_id in enumerate(all_items["ids"]):
                metadata = all_items["metadatas"][idx] if all_items["metadatas"] else {}
                doc_id = metadata.get("document_id", item_id.split(":")[0])
                filename = metadata.get("filename", "unknown")
                indexed_at = metadata.get("indexed_at", datetime.now().isoformat())

                if doc_id not in doc_map:
                    doc_map[doc_id] = {
                        "id": doc_id,
                        "filename": filename,
                        "indexed_at": indexed_at,
                        "chunk_count": 0,
                        "metadata": {},
                    }

                doc_map[doc_id]["chunk_count"] += 1

                # Store additional metadata (excluding internal fields)
                for key, value in metadata.items():
                    if key not in (
                        "document_id",
                        "filename",
                        "indexed_at",
                        "chunk_index",
                    ):
                        doc_map[doc_id]["metadata"][key] = str(value)

            # Convert to DocumentResponse objects
            documents = [
                DocumentResponse(
                    id=doc["id"],
                    filename=doc["filename"],
                    status="indexed",
                    indexed_at=datetime.fromisoformat(doc["indexed_at"]),
                    chunk_count=doc["chunk_count"],
                    metadata=doc["metadata"],
                )
                for doc in doc_map.values()
            ]

            # Sort by indexed_at (newest first)
            documents.sort(key=lambda x: x.indexed_at, reverse=True)

            return DocumentListResponse(documents=documents, total=len(documents))

        except Exception as e:
            logger.error(f"Error listing documents: {e}", exc_info=True)
            return DocumentListResponse(documents=[], total=0)

    def delete_document(self, doc_id: str) -> DocumentDeleteResponse:
        """
        Delete a document and all its chunks from the vector store.

        Also removes the uploaded file if it exists.
        """
        try:
            # Get all items to find chunks belonging to this document
            collection = self.vector_store._collection
            all_items = collection.get(include=["metadatas"])

            if not all_items["ids"]:
                return DocumentDeleteResponse(
                    status="error", message=f"Document {doc_id} not found"
                )

            # Find all chunk IDs for this document
            chunks_to_delete = []
            filename = None

            for idx, item_id in enumerate(all_items["ids"]):
                metadata = all_items["metadatas"][idx] if all_items["metadatas"] else {}
                item_doc_id = metadata.get("document_id", item_id.split(":")[0])

                if item_doc_id == doc_id or item_id.startswith(f"{doc_id}:"):
                    chunks_to_delete.append(item_id)
                    if not filename:
                        filename = metadata.get("filename")

            if not chunks_to_delete:
                return DocumentDeleteResponse(
                    status="error", message=f"Document {doc_id} not found"
                )

            # Delete all chunks
            for chunk_id in chunks_to_delete:
                self.vector_store.delete_document(chunk_id)

            # Try to delete the uploaded file
            if filename:
                upload_path = self.upload_dir / filename
                if upload_path.exists():
                    upload_path.unlink()
                    logger.info(f"Deleted uploaded file: {upload_path}")

            logger.info(
                f"Deleted document {doc_id} with {len(chunks_to_delete)} chunks"
            )

            return DocumentDeleteResponse(
                status="success",
                message=f"Successfully deleted document and {len(chunks_to_delete)} chunks",
            )

        except Exception as e:
            logger.error(f"Error deleting document {doc_id}: {e}", exc_info=True)
            return DocumentDeleteResponse(
                status="error", message=f"Failed to delete document: {str(e)}"
            )
