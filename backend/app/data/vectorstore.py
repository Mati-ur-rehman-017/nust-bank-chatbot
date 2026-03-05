"""ChromaDB wrapper for storing and retrieving embeddings."""

from __future__ import annotations

from dataclasses import dataclass

import chromadb
from chromadb.config import Settings as ChromaSettings


@dataclass
class VectorSearchResult:
    doc_id: str
    score: float
    text: str
    metadata: dict[str, str]


class VectorStore:
    def __init__(self, path: str, dimension: int = 384) -> None:
        self._client = chromadb.PersistentClient(
            path=path,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name="bank_documents",
            metadata={"hnsw:space": "cosine"},
        )
        self._dimension = dimension

    def add_document(
        self,
        doc_id: str,
        text: str,
        embedding: list[float],
        metadata: dict[str, str | int],
    ) -> None:
        # ChromaDB requires metadata values to be str, int, float, or bool
        clean_metadata = {k: str(v) for k, v in metadata.items()}
        self._collection.upsert(
            ids=[doc_id],
            embeddings=[embedding],
            documents=[text],
            metadatas=[clean_metadata],
        )

    def delete_document(self, doc_id: str) -> None:
        self._collection.delete(ids=[doc_id])

    def search(
        self, query_embedding: list[float], top_k: int = 5
    ) -> list[VectorSearchResult]:
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        search_results: list[VectorSearchResult] = []
        if not results["ids"] or not results["ids"][0]:
            return search_results

        for i, doc_id in enumerate(results["ids"][0]):
            # ChromaDB returns distances, convert to similarity score (1 - distance for cosine)
            distance = results["distances"][0][i] if results["distances"] else 0.0
            score = 1.0 - distance
            text = results["documents"][0][i] if results["documents"] else ""
            metadata = results["metadatas"][0][i] if results["metadatas"] else {}
            search_results.append(
                VectorSearchResult(
                    doc_id=doc_id,
                    score=score,
                    text=text,
                    metadata={k: str(v) for k, v in metadata.items()},
                )
            )

        return search_results

    def count(self) -> int:
        """Return the number of documents in the collection."""
        return self._collection.count()
