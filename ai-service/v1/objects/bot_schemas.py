from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class BotHandleRequest(BaseModel):
    """
    机器人收到的“传话单”。
    包含了老乡的 QQ、说的话，还有可能发过来的图。
    """
    qq_user_id: str = Field(..., min_length=1)
    message: str = Field("", description="用户说的话，纯发图的时候可以不写字")
    guild_id: Optional[str] = None
    image_urls: Optional[List[str]] = Field(None, description="老乡发来的图片地址（多模态问诊）")


class BotHandleResponse(BaseModel):
    """
    机器人给老乡的回信。
    可能是几句贴心话，也可能是一张分析图（封装成 Base64 字符串）。
    """


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
