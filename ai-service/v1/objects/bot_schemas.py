from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class BotHandleRequest(BaseModel):
    qq_user_id: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)
    guild_id: Optional[str] = None


class BotHandleResponse(BaseModel):
    reply: str


class OutboxItem(BaseModel):
    id: int
    qq_user_id: str
    guild_id: Optional[str]
    content: str


class OutboxPendingResponse(BaseModel):
    items: List[OutboxItem]


class OutboxMarkRequest(BaseModel):
    ids: List[int]
    status: str = "sent"
    error: Optional[str] = None
