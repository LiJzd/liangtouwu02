"""
多智能体控制器 - 使用 Supervisor-Worker 架构
"""
from __future__ import annotations

import logging

from fastapi import APIRouter

from v1.logic.multi_agent_core import AgentContext, MultiAgentOrchestrator
from v1.objects.agent_schemas import AgentChatRequest, AgentChatResponse

router = APIRouter()
logger = logging.getLogger("multi_agent_controller")

# 全局协调器实例（单例）
_orchestrator: MultiAgentOrchestrator | None = None


def get_orchestrator() -> MultiAgentOrchestrator:
    """获取协调器单例"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = MultiAgentOrchestrator()
    return _orchestrator


@router.post("/chat/v2", response_model=AgentChatResponse)
async def chat_v2(payload: AgentChatRequest) -> AgentChatResponse:
    """
    多智能体对话接口（V2 版本）
    
    使用 Supervisor-Worker 架构：
    1. Supervisor 路由意图
    2. Worker 执行任务
    3. 返回结果
    """
    logger.info(
        "multi_agent_chat hit user_id=%s messages=%d",
        payload.user_id,
        len(payload.messages)
    )
    
    # 构建上下文
    context = AgentContext(
        user_id=payload.user_id,
        user_input=payload.messages[-1].content if payload.messages else "",
        chat_history=[m.model_dump() for m in payload.messages[:-1]],
        metadata=payload.metadata or {},
        client_id=f"user_{payload.user_id}"
    )
    
    # 执行多智能体协作
    orchestrator = get_orchestrator()
    result = await orchestrator.execute(context)
    
    # 记录调试信息
    if result.thoughts:
        logger.debug(f"Worker {result.worker_name} 思考过程: {result.thoughts}")
    
    if result.error:
        logger.error(f"Worker {result.worker_name} 执行失败: {result.error}")
    
    if result.image:
        logger.info(f"返回图片给前端，长度: {len(result.image)}")
    else:
        logger.warning("未返回图片给前端")
    
    return AgentChatResponse(
        reply=result.answer,
        image=result.image,
        metadata=result.metadata
    )
