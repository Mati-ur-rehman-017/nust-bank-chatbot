"""RAG retrieval service — embeds a query and searches the vector store."""

from __future__ import annotations

import logging

from app.data.vectorstore import VectorSearchResult, VectorStore
from app.services.embedding import EmbeddingService

logger = logging.getLogger(__name__)

_DEFAULT_TOP_K = 5
_RELEVANCE_THRESHOLD = 0.3
_FAQ_TIE_BREAK_DELTA = 0.03
_QUESTION_PREFIXES = (
    "what",
    "how",
    "why",
    "when",
    "where",
    "who",
    "can",
    "do",
    "does",
    "is",
    "are",
)


def _is_question_query(query: str) -> bool:
    normalized = query.strip().lower()
    if not normalized:
        return False
    if "?" in normalized:
        return True
    return normalized.startswith(_QUESTION_PREFIXES)


def _faq_tie_break_sort_key(
    result: VectorSearchResult, query: str
) -> tuple[int, float]:
    is_faq = str(result.metadata.get("is_faq", "false")).lower() == "true"
    if _is_question_query(query):
        return (1 if is_faq else 0, result.score)
    return (0, result.score)


def _sort_with_faq_tie_break(
    results: list[VectorSearchResult], query: str
) -> list[VectorSearchResult]:
    if not results:
        return results

    sorted_by_score = sorted(results, key=lambda r: r.score, reverse=True)
    if not _is_question_query(query):
        return sorted_by_score

    grouped: list[list[VectorSearchResult]] = []
    for result in sorted_by_score:
        if not grouped:
            grouped.append([result])
            continue
        current_group = grouped[-1]
        if abs(current_group[0].score - result.score) <= _FAQ_TIE_BREAK_DELTA:
            current_group.append(result)
        else:
            grouped.append([result])

    reranked: list[VectorSearchResult] = []
    for group in grouped:
        reranked.extend(
            sorted(group, key=lambda r: _faq_tie_break_sort_key(r, query), reverse=True)
        )
    return reranked


class RetrievalService:
    """Retrieve the most relevant document chunks for a user query."""

    def __init__(
        self,
        vector_store: VectorStore,
        embedding_service: EmbeddingService,
    ) -> None:
        self.vector_store = vector_store
        self.embedding_service = embedding_service

    async def retrieve(
        self,
        query: str,
        top_k: int = _DEFAULT_TOP_K,
    ) -> list[VectorSearchResult]:
        """Embed *query*, search ChromaDB, and filter by relevance score."""

        query_embedding = self.embedding_service.embed(query)
        results = self.vector_store.search(query_embedding, top_k)

        filtered = [r for r in results if r.score > _RELEVANCE_THRESHOLD]
        filtered = _sort_with_faq_tie_break(filtered, query)

        logger.info(
            "Retrieved %d/%d chunks above threshold %.2f for query: %s",
            len(filtered),
            len(results),
            _RELEVANCE_THRESHOLD,
            query[:80],
        )

        return filtered
