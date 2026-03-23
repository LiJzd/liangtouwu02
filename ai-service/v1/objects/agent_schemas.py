from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AgentMessage(BaseModel):
    role: str = Field(..., description="system/user/assistant")
    content: str


class AgentChatRequest(BaseModel):
    user_id: str
    messages: List[AgentMessage]
    metadata: Optional[Dict[str, Any]] = None


class AgentChatResponse(BaseModel):
    reply: str
    image: Optional[str] = Field(None, description="Base64 编码的图片（可选）")
    metadata: Optional[Dict[str, Any]] = Field(None, description="额外的元数据")
