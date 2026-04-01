"""
多智能体控制器 - 使用 Supervisor-Worker 架构
"""
from __future__ import annotations

import logging

import os
import httpx
import tempfile
from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse
from v1.common.config import get_settings

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
    
    # 提取用户输入文本（兼容多模态 content 为列表的情况）
    last_content = payload.messages[-1].content if payload.messages else ""
    if isinstance(last_content, list):
        # 多模态格式：从 content 数组中提取文本部分
        text_parts = [item.get("text", "") for item in last_content if isinstance(item, dict) and item.get("type") == "text"]
        user_input_text = " ".join(text_parts) if text_parts else ""
    else:
        user_input_text = last_content or ""
    
    # 构建上下文（包含多模态图片URL）
    context = AgentContext(
        user_id=payload.user_id,
        user_input=user_input_text,
        chat_history=[m.model_dump() for m in payload.messages[:-1]],
        metadata=payload.metadata or {},
        client_id=f"user_{payload.user_id}",
        image_urls=payload.image_urls,
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


@router.post("/voice/transcribe")
async def transcribe_voice(file: UploadFile = File(...)):
    """接收基于网页录制的 Blob 音频上传，自动转文本"""
    settings = get_settings()
    api_key = os.environ.get("DASHSCOPE_API_KEY") or settings.dashscope_api_key
    if not api_key:
        logger.error("No DASHSCOPE_API_KEY found")
        return {"text": ""}
    
    suffix = ".webm"
    if file.filename and "." in file.filename:
        suffix = f".{file.filename.split('.')[-1]}"
        
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name
        
        base_url = (
            os.environ.get("DASHSCOPE_BASE_URL")
            or settings.dashscope_base_url
            or "https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        
        async with httpx.AsyncClient(timeout=30) as client:
            with open(tmp_path, "rb") as f:
                content_type = "audio/webm" if "webm" in suffix else ("audio/wav" if "wav" in suffix else "application/octet-stream")
                resp = await client.post(
                    f"{base_url}/audio/transcriptions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    files={"file": (f"audio{suffix}", f, content_type)},
                    data={"model": "paraformer-v2"},
                )
                
            if resp.status_code == 200:
                data = resp.json()
                text = data.get("text", "")
                logger.info(f"网页语音识别完成: {text}")
                return {"text": text}
            else:
                logger.error(f"Voice Transcribe Error: {resp.text}")
                return JSONResponse({"text": ""}, status_code=resp.status_code)
    except Exception as e:
        logger.error(f"Voice transcribe exception: {e}")
        return JSONResponse({"text": ""}, status_code=500)
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
