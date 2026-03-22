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
