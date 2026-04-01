from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class BotHandleRequest(BaseModel):
    qq_user_id: str = Field(..., min_length=1)
    message: str = Field("", description="用户消息文本，纯图片消息时可为空")
    guild_id: Optional[str] = None
    image_urls: Optional[List[str]] = Field(None, description="用户发送的图片URL列表（多模态问诊）")


class BotHandleResponse(BaseModel):
    reply: str
    image: Optional[str] = Field(None, description="Base64 编码的图片（可选）")


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
