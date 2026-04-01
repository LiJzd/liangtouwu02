from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AgentMessage(BaseModel):
    role: str = Field(..., description="system/user/assistant")
    content: Any = Field(..., description="文本字符串或多模态内容数组")


class AgentChatRequest(BaseModel):
    user_id: str
    messages: List[AgentMessage]
    metadata: Optional[Dict[str, Any]] = None
    image_urls: Optional[List[str]] = Field(None, description="用户发送的图片URL列表（多模态问诊）")


class AgentChatResponse(BaseModel):
    reply: str
    image: Optional[str] = Field(None, description="Base64 编码的图片（可选）")
    metadata: Optional[Dict[str, Any]] = Field(None, description="额外的元数据")
