# -*- coding: utf-8 -*-
from __future__ import annotations

import logging

from fastapi import APIRouter

from v1.logic.central_agent_core import generate_reply
from v1.objects.agent_schemas import AgentChatRequest, AgentChatResponse

router = APIRouter()
logger = logging.getLogger("central_agent")


@router.post("/chat", response_model=AgentChatResponse)
async def chat(payload: AgentChatRequest) -> AgentChatResponse:
    logger.info("central_agent_chat hit user_id=%s messages=%d", payload.user_id, len(payload.messages))
    # 使用 user_id 作为 client_id，实现用户级别的调试流隔离
    client_id = f"user_{payload.user_id}"
    reply = generate_reply([m.model_dump() for m in payload.messages], client_id=client_id)
    return AgentChatResponse(reply=reply)
