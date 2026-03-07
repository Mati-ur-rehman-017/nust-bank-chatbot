"""Chat route definitions — POST /api/chat and POST /api/chat/stream."""

import json
import logging
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.api.deps import get_chat_service
from app.models.schemas import ChatRequest, ChatResponse
from app.services.chat import ChatService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    service: ChatService = Depends(get_chat_service),
) -> ChatResponse:
    """Accept a user message and return a complete RAG-powered response."""

    logger.info(
        "Chat request: %s (history: %d messages)",
        request.message[:80],
        len(request.history),
    )

    try:
        return await service.chat(request.message, request.history)
    except Exception as exc:
        logger.exception("Chat generation failed")
        raise HTTPException(
            status_code=502,
            detail=f"LLM service error: {exc}",
        ) from exc


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    service: ChatService = Depends(get_chat_service),
) -> StreamingResponse:
    """Accept a user message and stream back tokens via SSE."""

    logger.info(
        "Stream request: %s (history: %d messages)",
        request.message[:80],
        len(request.history),
    )

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            async for token in service.chat_stream(request.message, request.history):
                payload = json.dumps({"token": token})
                yield f"data: {payload}\n\n"
            yield "data: [DONE]\n\n"
        except Exception:
            logger.exception("Stream generation failed")
            error = json.dumps({"error": "LLM service error"})
            yield f"data: {error}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
