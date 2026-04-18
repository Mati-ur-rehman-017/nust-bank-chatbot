"""Chat orchestration — ties retrieval, prompt building, and LLM together."""

from __future__ import annotations

import logging
from typing import AsyncGenerator

from app.core.guardrails import GuardRails
from app.core.prompts import OUT_OF_DOMAIN_RESPONSE
from app.core.prompts import build_prompt
from app.models.schemas import ChatResponse, MessageItem, Source
from app.services.llm import LLMService
from app.services.retrieval import RetrievalService

logger = logging.getLogger(__name__)


class ChatService:
    """High-level service that handles the full RAG chat flow."""

    def __init__(
        self,
        retrieval_service: RetrievalService,
        llm_service: LLMService,
    ) -> None:
        self.retrieval = retrieval_service
        self.llm = llm_service
        self.guard = GuardRails()

    async def chat(
        self,
        message: str,
        history: list[MessageItem] | None = None,
    ) -> ChatResponse:
        """Run the full RAG pipeline and return a complete response."""

        if self.guard.detect_jailbreak(message) or self.guard.detect_prompt_injection(
            message
        ):
            return ChatResponse(response=OUT_OF_DOMAIN_RESPONSE, sources=[])

        results = await self.retrieval.retrieve(message)
        if not results:
            return ChatResponse(response=OUT_OF_DOMAIN_RESPONSE, sources=[])

        context_texts = [r.text for r in results]
        system, user_query = build_prompt(message, context_texts, history)

        logger.info(
            "Generating response with %d context chunks and %d history messages",
            len(context_texts),
            len(history) if history else 0,
        )

        llm_response = await self.llm.generate(prompt=user_query, system=system)

        sources = [
            Source(doc_id=r.doc_id, score=round(r.score, 4), text=r.text)
            for r in results
        ]

        return ChatResponse(response=llm_response, sources=sources)

    async def chat_stream(
        self,
        message: str,
        history: list[MessageItem] | None = None,
    ) -> AsyncGenerator[str, None]:
        """Run retrieval + prompt building, then stream LLM tokens."""

        if self.guard.detect_jailbreak(message) or self.guard.detect_prompt_injection(
            message
        ):
            yield OUT_OF_DOMAIN_RESPONSE
            return

        results = await self.retrieval.retrieve(message)
        if not results:
            yield OUT_OF_DOMAIN_RESPONSE
            return

        context_texts = [r.text for r in results]
        print(f"[DEBUG] Retrieved {len(context_texts)} context chunks:")
        for i, ctx in enumerate(context_texts):
            print(f"[DEBUG] Context {i + 1}:\n{ctx[:200]}...")
        system, user_query = build_prompt(message, context_texts, history)

        logger.info(
            "Streaming response with %d context chunks and %d history messages",
            len(context_texts),
            len(history) if history else 0,
        )

        async for token in self.llm.stream_generate(prompt=user_query, system=system):
            yield token
