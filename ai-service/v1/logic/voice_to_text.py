# -*- coding: utf-8 -*-
"""
自动语音识别 (ASR) 逻辑层。

负责将音频文件 URL 转换为结构化文本。
本模块对接阿里云 DashScope Paraformer 语音识别服务，支持中英文混识及异步识别流程。
"""
from __future__ import annotations

import logging
import os
import tempfile
from typing import Optional

import httpx

from v1.common.config import get_settings

logger = logging.getLogger("voice_to_text")


async def voice_to_text(audio_url: str) -> Optional[str]:
    """
    将语音URL转为文字

    优先使用 DashScope Paraformer 进行识别，
    支持通过 URL 直接识别或先下载后识别。
    """
    settings = get_settings()
    api_key = os.environ.get("DASHSCOPE_API_KEY") or settings.dashscope_api_key

    if not api_key:
        logger.warning("缺少 DASHSCOPE_API_KEY，无法进行语音识别")
        return None

    # 方案1: 使用 DashScope Paraformer 异步识别（通过URL直传）
    result = await _transcribe_with_paraformer(audio_url, api_key)
    if result:
        return result

    # 方案2: 下载音频并重试
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(audio_url)
            if resp.status_code == 200:
                suffix = ".wav"
                if ".silk" in audio_url.lower(): suffix = ".silk"
                elif ".amr" in audio_url.lower(): suffix = ".amr"
                elif ".mp3" in audio_url.lower(): suffix = ".mp3"
                return await file_to_text(resp.content, f"audio{suffix}")
    except Exception as e:
        logger.warning(f"下载并转写语音失败: {e}")

    logger.error("所有语音识别方案均失败")
    return None


async def file_to_text(file_content: bytes, filename: str) -> Optional[str]:
    """
    直接将音频文件二进制内容转为文字。
    使用 DashScope OpenAI 兼容接口进行同步识别。
    """
    settings = get_settings()
    api_key = os.environ.get("DASHSCOPE_API_KEY") or settings.dashscope_api_key
    if not api_key:
        logger.warning("缺少 DASHSCOPE_API_KEY，无法进行语音识别")
        return None

    try:
        logger.info(f"开始同步语音转写: {filename} ({len(file_content)} bytes)")
        
        base_url = (
            os.environ.get("DASHSCOPE_BASE_URL")
            or settings.dashscope_base_url
            or "https://dashscope.aliyuncs.com/compatible-mode/v1"
        )

        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as tmp:
            tmp.write(file_content)
            tmp_path = tmp.name

        try:
            async with httpx.AsyncClient(timeout=45) as client:
                with open(tmp_path, "rb") as f:
                    resp = await client.post(
                        f"{base_url}/audio/transcriptions",
                        headers={"Authorization": f"Bearer {api_key}"},
                        files={"file": (filename, f, "audio/wav")},
                        data={"model": "paraformer-v2"},
                    )

                if resp.status_code == 200:
                    data = resp.json()
                    text = data.get("text", "")
                    if text:
                        logger.info(f"语音转写成功: {text[:100]}")
                        return text
                
                logger.warning(f"语音转写失败: {resp.status_code} {resp.text[:200]}")
                return None
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    except Exception as e:
        logger.error(f"语音转写异常: {e}", exc_info=True)
        return None


async def _transcribe_with_paraformer(audio_url: str, api_key: str) -> Optional[str]:
    """通过 DashScope Paraformer 异步任务接口进行语音识别。"""
    try:
        logger.info(f"开始 Paraformer 异步识别，URL: {audio_url[:80]}...")
        submit_url = "https://dashscope.aliyuncs.com/api/v1/services/audio/asr/transcription"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable",
        }
        payload = {
            "model": "paraformer-v2",
            "input": {"file_urls": [audio_url]},
            "parameters": {"language_hints": ["zh", "en"]}
        }
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(submit_url, json=payload, headers=headers)
            if resp.status_code != 200:
                logger.warning(f"Paraformer 任务提交失败: {resp.status_code} {resp.text[:200]}")
                return None
            
            task_id = resp.json().get("output", {}).get("task_id")
            if not task_id: return None

            # 轮询状态
            query_url = f"https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}"
            import asyncio
            for _ in range(30):
                await asyncio.sleep(1)
                q_resp = await client.get(query_url, headers={"Authorization": f"Bearer {api_key}"})
                if q_resp.status_code != 200: continue
                result = q_resp.json()
                status = result.get("output", {}).get("task_status")
                if status == "SUCCEEDED":
                    # 简化逻辑：直接从 output 返回的 text 中拿（paraformer-v2 支持）
                    # 或者从 transcription_url 拿完整结果
                    results = result.get("output", {}).get("results", [])
                    if results:
                        text = results[0].get("text", "")
                        if text: return text
                elif status == "FAILED":
                    return None
            return None
    except Exception as e:
        logger.error(f"Paraformer 异步识别异常: {e}")
        return None
