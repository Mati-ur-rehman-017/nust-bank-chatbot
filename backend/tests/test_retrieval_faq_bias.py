"""Tests for FAQ-aware retrieval tie-break ordering."""

from __future__ import annotations

import os
import sys
import types
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Stub vectorstore module to avoid importing chromadb in tests.
fake_vectorstore_module = types.ModuleType("app.data.vectorstore")


@dataclass
class FakeVectorSearchResult:
    doc_id: str
    score: float
    text: str
    metadata: dict[str, str]


class FakeVectorStoreType:
    pass


fake_vectorstore_module.VectorSearchResult = FakeVectorSearchResult
fake_vectorstore_module.VectorStore = FakeVectorStoreType
sys.modules["app.data.vectorstore"] = fake_vectorstore_module

# Stub embedding module to avoid sentence_transformers import in tests.
fake_embedding_module = types.ModuleType("app.services.embedding")


class FakeEmbeddingServiceType:
    pass


fake_embedding_module.EmbeddingService = FakeEmbeddingServiceType
sys.modules["app.services.embedding"] = fake_embedding_module

from app.services.retrieval import RetrievalService


class FakeEmbeddingService:
    def embed(self, query: str) -> list[float]:
        return [0.1, 0.2, 0.3]


class FakeVectorStore:
    def search(self, query_embedding, top_k: int = 5):
        return [
            FakeVectorSearchResult(
                doc_id="nonfaq-1",
                score=0.62,
                text="not faq",
                metadata={"is_faq": "false"},
            ),
            FakeVectorSearchResult(
                doc_id="faq-1",
                score=0.60,
                text="faq",
                metadata={"is_faq": "true"},
            ),
        ]


def test_retrieval_prefers_faq_when_scores_are_close() -> None:
    service = RetrievalService(FakeVectorStore(), FakeEmbeddingService())
    results = __import__("asyncio").run(service.retrieve("How do I reset MPIN?"))
    assert results[0].doc_id == "faq-1"
