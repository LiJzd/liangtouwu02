# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AgentMessage(BaseModel):
    """
    表示对话中的单条消息。
    包含角色定义（role）及消息内容（content）。
    """
    role: str = Field(..., description="发送者角色：system, user 或 assistant")
    content: Any = Field(..., description="消息内容：支持纯文本或复合多模态数组")


class AgentChatRequest(BaseModel):
    """
    智能体对话请求协议。
    包含用户标识、历史消息、图片 URL 等多模态上下文信息。
    """
    user_id: str
    messages: List[AgentMessage]
    metadata: Optional[Dict[str, Any]] = None
    image_urls: Optional[List[str]] = Field(None, description="多模态输入所需的图片 URL 列表")


class AgentChatResponse(BaseModel):
    """
    智能体对话响应协议。
    """
    reply: str
    image: Optional[str] = Field(None, description="可选：Base64 编码的图像数据")
    metadata: Optional[Dict[str, Any]] = Field(None, description="可选：附加元数据")
