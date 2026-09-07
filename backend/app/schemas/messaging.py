"""Direct-message DTOs."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SendMessageRequest(BaseModel):
    recipient_id: str
    text: str = Field(..., min_length=1, max_length=2000)


class MessageDTO(BaseModel):
    id: str
    sender_id: str
    recipient_id: str
    text: str
    is_read: bool
    when: str
    mine: bool = False  # set per-viewer: did the current user send this?


class ConversationDTO(BaseModel):
    other_id: str
    other_name: str
    last_text: str
    last_when: str
    last_mine: bool  # was the latest message sent by the viewer?
    unread: int


class ThreadDTO(BaseModel):
    other_id: str
    other_name: str
    messages: list[MessageDTO] = []
