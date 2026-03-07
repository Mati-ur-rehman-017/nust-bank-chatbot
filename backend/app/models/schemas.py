"""Pydantic request/response schemas for the API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class MessageItem(BaseModel):
    """A single message in the conversation history."""

    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    """Incoming chat message from the user."""

    message: str = Field(..., min_length=1, max_length=4000)
    history: list[MessageItem] = Field(default_factory=list)


class Source(BaseModel):
    """A single retrieved source document reference."""

    doc_id: str
    score: float
    text: str


class ChatResponse(BaseModel):
    """Response returned by the chat endpoint."""

    response: str
    sources: list[Source] = Field(default_factory=list)
