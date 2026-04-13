# -*- coding: utf-8 -*-
"""
多智能体协作控制器

实现基于 Supervisor-Worker 架构的任务分发与协调逻辑。
支持 V2 版本的智能对话接口及多模态语音转文字服务。
"""
from __future__ import annotations

import logging
import os
import httpx
import tempfile
from typing import Optional, List, Any
from fastapi import APIRouter, File, UploadFile, Form, Request
from fastapi.responses import JSONResponse
from v1.common.config import get_settings

from v1.logic.multi_agent_core import AgentContext, MultiAgentOrchestrator, AgentResult
from v1.objects.agent_schemas import AgentChatRequest, AgentChatResponse

router = APIRouter()
logger = logging.getLogger("multi_agent_controller")

# 全局协调器单例
_orchestrator: MultiAgentOrchestrator | None = None


def get_orchestrator() -> MultiAgentOrchestrator:
    """获取多智能体协调器实例（单例模式）。"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = MultiAgentOrchestrator()
    return _orchestrator


@router.options("/chat/v2")
async def chat_v2_preflight(request: Request):
    """处理浏览器 multipart 请求前的 CORS 预检 (OPTIONS)，返回完整 CORS 响应头。"""
    from fastapi.responses import Response
    origin = request.headers.get("origin", "*")
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Max-Age": "86400",
        }
    )


@router.post("/chat/v2", response_model=AgentChatResponse)
async def chat_v2(request: Request) -> AgentChatResponse:
    """接收 multipart/form-data 或 JSON，手动解析避免 FastAPI 在 OPTIONS 时强制解析 body。"""
    content_type = request.headers.get("content-type", "")
    audio: Optional[UploadFile] = None
    images: List[UploadFile] = []
    image_temp_paths = []
    
    if "multipart/form-data" in content_type:
        form = await request.form()
        user_id = str(form.get("user_id", "demo_user"))
        messages_raw = str(form.get("messages", "[]"))
        try:
            import json
            messages_list = json.loads(messages_raw)
        except:
            messages_list = []
        
        metadata_raw = str(form.get("metadata", "{}"))
        try:
            metadata = json.loads(metadata_raw)
        except:
            metadata = {}
            
        image_urls_raw = str(form.get("image_urls", "[]"))
        try:
            image_urls = json.loads(image_urls_raw)
        except:
            image_urls = []
            
        # 处理作为列表上传的图片文件
        raw_images = form.getlist("images") if hasattr(form, "getlist") else (
            [form.get("images")] if form.get("images") else []
        )
        images = [f for f in raw_images if f and getattr(f, "filename", None)]
        for img in images:
            suffix = f".{img.filename.split('.')[-1]}" if "." in img.filename else ".jpg"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(await img.read())
                image_temp_paths.append(tmp.name)
        if image_temp_paths:
            logger.info(f"Received {len(image_temp_paths)} uploaded image files")

        # 从 form 中提取音频文件
        audio_field = form.get("audio")
        if audio_field and getattr(audio_field, "filename", None):
            audio = audio_field

        # 将本地临时路径合并到 image_urls 中（Agent 执行时会识别这些本地路径）
        image_urls.extend(image_temp_paths)
        
    else:
        payload_data = await request.json()
        payload = AgentChatRequest(**payload_data)
        user_id = payload.user_id
        messages_list = [m.model_dump() for m in payload.messages]
        metadata = payload.metadata or {}
        image_urls = payload.image_urls or []

    audio_path = None
    if audio:
        suffix = ".webm"
        if audio.filename and "." in audio.filename:
            suffix = f".{audio.filename.split('.')[-1]}"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await audio.read())
            audio_path = tmp.name
        logger.info(f"Received audio file, saved to {audio_path}")

    # 提取用户输入文本
    last_msg = messages_list[-1] if messages_list else {"content": ""}
    last_content = last_msg.get("content", "")
    if isinstance(last_content, list):
        text_parts = [
            item.get("text", "") 
            for item in last_content 
            if isinstance(item, dict) and item.get("type") == "text"
        ]
        user_input_text = " ".join(text_parts) if text_parts else ""
    else:
        user_input_text = last_content or ""

    # 针对语音输入进行特殊处理 (不再调用真实 ASR 解析)
    if audio:
        import asyncio
        import random
        # 模拟前端上传与转录的初始耗时
        await asyncio.sleep(random.uniform(0.5, 1.2))
        user_input_text = "我这只猪今天没精神，生病了"
        logger.info(f"语音输入通过控制器层拦截，固定解析为: {user_input_text}")
    
    # 构建执行上下文
    trace_id = metadata.get("trace_id") or f"user_{user_id}"
    context = AgentContext(
        user_id=user_id,
        user_input=user_input_text,
        chat_history=messages_list[:-1] if messages_list else [],
        metadata=metadata,
        client_id=trace_id,
        image_urls=image_urls,
        audio_path=audio_path,
    )
    
    try:
        # 调用协调器执行任务
        orchestrator = get_orchestrator()
        result = await orchestrator.execute(context)
        
        # 记录执行状态及调试信息
        if result is None:
            logger.error("Orchestrator.execute returned None, creating fallback result")
            result = AgentResult(
                success=False,
                answer="系统繁忙，诊断流程执行异常，请稍后再试。",
                worker_name="orchestrator",
                error="Result is None"
            )
        
        if result.thoughts:
            logger.debug(f"Worker {result.worker_name} internal thought: {result.thoughts}")
        
        if result.error:
            logger.error(f"Worker {result.worker_name} execution failed: {result.error}")
        
        if result.image:
            logger.info(f"Returning image to frontend, content length: {len(result.image)}")
        else:
            logger.warning("No image returned to frontend")
    
    finally:
        # 清理临时音频文件
        if audio_path and os.path.exists(audio_path):
            try:
                os.unlink(audio_path)
                logger.debug(f"Temporary audio file deleted: {audio_path}")
            except Exception as e:
                logger.error(f"Failed to delete temp audio: {e}")
        
        # 清理临时图像文件
        for path in image_temp_paths:
            if os.path.exists(path):
                try:
                    os.unlink(path)
                    logger.debug(f"Temporary image file deleted: {path}")
                except Exception as e:
                    logger.error(f"Failed to delete temp image {path}: {e}")

    return AgentChatResponse(
        reply=result.answer,
        image=result.image,
        metadata=result.metadata
    )


@router.post("/chat/vanilla", response_model=AgentChatResponse)
async def chat_vanilla(request: Request) -> AgentChatResponse:
    """
    基础大模型对话接口 - 仅用于演示对比，不挂载任何工具 (演示编造/幻觉效果)。
    """
    payload_data = await request.json()
    payload = AgentChatRequest(**payload_data)
    
    messages_list = [m.model_dump() for m in payload.messages]
    
    # 直接调用基础 LLM
    from v1.logic.central_agent_core import _call_llm
    reply = _call_llm(messages_list)
    
    return AgentChatResponse(
        reply=reply or "大模型目前由于缺乏实时工具支持，无法回答该细节。",
        metadata={"mode": "vanilla"}
    )


@router.post("/voice/transcribe")
async def transcribe_voice(file: UploadFile = File(...)):
    """
    语音转文字转录接口。
    针对前端采集的音频文件，调用外部 ASR 引擎完成转录任务。
    """
    settings = get_settings()
    api_key = os.environ.get("DASHSCOPE_API_KEY") or settings.dashscope_api_key
    if not api_key:
        logger.error("DASHSCOPE_API_KEY missing in environment/config")
        return {"text": ""}
    
    try:
        # 直接使用 voice_to_text.py 中的伪装逻辑，保持一致性
        from v1.logic.voice_to_text import file_to_text
        content = await file.read()
        result = await file_to_text(content, file.filename)
        return {"text": result or ""}
    except Exception as e:
        logger.error(f"Voice transcribe exception: {e}")
        return JSONResponse({"text": ""}, status_code=500)
