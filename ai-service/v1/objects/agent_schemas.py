from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AgentMessage(BaseModel):
    """
    咱聊天的一句词儿。
    包含了谁说的（role）以及说了啥（content）。
    """
    role: str = Field(..., description="谁说的（system/user/assistant）")
    content: Any = Field(..., description="说的话，可以是字儿，也可以是带着图的数组")


class AgentChatRequest(BaseModel):
    """
    找 AI 聊天的“邀请函”。
    把你想说的话、历史记录，要是带了图也一并带上。
    """
    user_id: str
    messages: List[AgentMessage]
    metadata: Optional[Dict[str, Any]] = None
    image_urls: Optional[List[str]] = Field(None, description="用户发送的图片URL列表（多模态问诊）")


class AgentChatResponse(BaseModel):
    reply: str
    image: Optional[str] = Field(None, description="Base64 编码的图片（可选）")
    metadata: Optional[Dict[str, Any]] = Field(None, description="额外的元数据")
