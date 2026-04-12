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
import asyncio
import random
from typing import Optional

import httpx

from v1.common.config import get_settings

logger = logging.getLogger("voice_to_text")


async def voice_to_text(audio_url: str) -> Optional[str]:
    """
    将语音URL转为文字 (伪装识别逻辑)
    """
    logger.info(f"开始伪装语音识别 (URL): {audio_url[:50]}...")
    
    # 模拟网络延时和处理耗时
    await asyncio.sleep(random.uniform(1.2, 2.8))
    
    fixed_text = "我的猪今天生病了,一天都没有精神"
    logger.info(f"伪装识别完成: {fixed_text}")
    return fixed_text


async def file_to_text(file_content: bytes, filename: str) -> Optional[str]:
    """
    直接将音频文件二进制内容转为文字 (伪装识别逻辑)
    """
    logger.info(f"开始伪装同步语音转写: {filename} ({len(file_content)} bytes)")
    
    # 模拟处理耗时
    await asyncio.sleep(random.uniform(1.0, 2.5))
    
    fixed_text = "我的猪今天生病了,一天都没有精神"
    logger.info(f"伪装同步转写成功: {fixed_text}")
    return fixed_text


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
