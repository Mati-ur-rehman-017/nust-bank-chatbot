"""Script that loads documents, preprocesses them, and writes to zvec."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable

# Add parent directory (where 'app' package lives) to sys.path
_SCRIPT_DIR = Path(__file__).resolve().parent
_BACKEND_ROOT = _SCRIPT_DIR.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from app.data.preprocessing import Document, chunk_document, load_documents_from_path

ALLOWED_EXTENSIONS = {".json", ".csv", ".xlsx", ".xls", ".txt"}


def should_ingest_file(path: Path) -> bool:
    name = path.name.strip()
    if not name:
        return False
    if name.startswith(".~lock.") or name.endswith("#"):
        return False
    if name.startswith("."):
        return False
    return path.suffix.lower() in ALLOWED_EXTENSIONS


def _collect_documents(
    paths: Iterable[Path],
) -> list[Document]:
    documents: list[Document] = []
    for source in paths:
        if not source.exists():
            continue
        for candidate in sorted(source.glob("*")):
            if not candidate.is_file():
                continue
            if not should_ingest_file(candidate):
                continue
            documents.extend(load_documents_from_path(candidate))
    return documents


def main() -> None:
    from app.config import settings
    from app.data.vectorstore import VectorStore
    from app.services.embedding import EmbeddingService

    document_roots = (Path("./data"), Path("./rag_data"))
    documents = _collect_documents(document_roots)
    embedding_service = EmbeddingService(model_name=settings.embedding_model)
    vector_store = VectorStore(str(settings.chroma_path))

    for doc in documents:
        chunks = list(chunk_document(doc))
        embeddings = embedding_service.embed_batch([chunk.text for chunk in chunks])
        for chunk, embedding in zip(chunks, embeddings):
            vector_store.add_document(
                doc_id=chunk.id,
                text=chunk.text,
                embedding=embedding,
                metadata=chunk.metadata,
            )


if __name__ == "__main__":
    main()
