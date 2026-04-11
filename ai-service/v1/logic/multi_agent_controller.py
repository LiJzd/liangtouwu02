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


@router.post("/chat/v2", response_model=AgentChatResponse)
async def chat_v2(
    request: Request,
    audio: Optional[UploadFile] = File(None),
    images: List[UploadFile] = File(default=[])
) -> AgentChatResponse:
    """
    智能体集群对话接口 (V2) - 增强多模态支持。
    同时支持 JSON 格式和 Multipart/form-data 格式。
    """
    content_type = request.headers.get("content-type", "")
    
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
        if images:
            for img in images:
                if not img.filename: continue
                suffix = f".{img.filename.split('.')[-1]}" if "." in img.filename else ".jpg"
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp.write(await img.read())
                    image_temp_paths.append(tmp.name)
            logger.info(f"Received {len(image_temp_paths)} uploaded image files")
        
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
                logger.info(f"Voice transcription completed: {text}")
                return {"text": text}
            else:
                logger.error(f"Voice Transcribe API error: {resp.text}")
                return JSONResponse({"text": ""}, status_code=resp.status_code)
    except Exception as e:
        logger.error(f"Voice transcribe exception: {e}")
        return JSONResponse({"text": ""}, status_code=500)
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
