# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class BotHandleRequest(BaseModel):
    """
    机器人交互请求协议。
    包含用户标识、原始消息内容（可选）及多模态输入 URL。
    """
    qq_user_id: str = Field(..., min_length=1)
    message: str = Field("", description="用户文本输入内容")
    guild_id: Optional[str] = None
    image_urls: Optional[List[str]] = Field(None, description="用于视觉分析的图片 URL 列表")


class BotHandleResponse(BaseModel):
    """
    机器人交互响应协议。
    """


class OutboxItem(BaseModel):
    """
    待发送消息项定义。
    """
    id: int
    qq_user_id: str
    guild_id: Optional[str]
    content: str


class OutboxPendingResponse(BaseModel):
    """
    待发送消息队列响应。
    """
    items: List[OutboxItem]


class OutboxMarkRequest(BaseModel):
    """
    消息状态标记请求。
    用于更新消息发送状态或记录发送错误信息。
    """
    ids: List[int]
    status: str = "sent"
    error: Optional[str] = None


class AsrResponse(BaseModel):
    """
    语音转文字响应协议。
    """
    text: str = Field(..., description="识别出的文本内容")
    code: int = 200
    message: str = "success"
