"""
语音转文字工具模块
使用 DashScope Paraformer-v2 将用户发送的语音消息转为文字

数据流：
  QQ用户发送语音 → bot_runner 提取语音URL → voice_to_text() → 返回识别文本
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

    Args:
        audio_url: 语音文件的公网URL

    Returns:
        识别出的文字，失败则返回 None
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

    # 方案2: 使用 OpenAI 兼容接口 (whisper 兼容) 作为降级
    result = await _transcribe_with_openai_compat(audio_url, api_key, settings)
    if result:
        return result

    logger.error("所有语音识别方案均失败")
    return None


async def _transcribe_with_paraformer(audio_url: str, api_key: str) -> Optional[str]:
    """使用 DashScope Paraformer-v2 模型进行语音识别（HTTP API 方式）"""
    try:
        logger.info(f"开始 Paraformer 语音识别，URL: {audio_url[:80]}...")

        # DashScope Paraformer 异步录音识别 API
        submit_url = "https://dashscope.aliyuncs.com/api/v1/services/audio/asr/transcription"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable",  # 异步模式
        }

        payload = {
            "model": "paraformer-v2",
            "input": {
                "file_urls": [audio_url]
            },
            "parameters": {
                "language_hints": ["zh", "en"],  # 支持中英文
            }
        }

        async with httpx.AsyncClient(timeout=60) as client:
            # 提交异步任务
            resp = await client.post(submit_url, json=payload, headers=headers)
            if resp.status_code != 200:
                logger.warning(f"Paraformer 任务提交失败: {resp.status_code} {resp.text[:200]}")
                return None

            data = resp.json()
            task_id = data.get("output", {}).get("task_id")
            if not task_id:
                logger.warning(f"Paraformer 未返回 task_id: {data}")
                return None

            logger.info(f"Paraformer 任务已提交: task_id={task_id}")

            # 轮询等待结果（最多等30秒）
            query_url = f"https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}"
            query_headers = {"Authorization": f"Bearer {api_key}"}

            import asyncio
            for _ in range(30):
                await asyncio.sleep(1)
                resp = await client.get(query_url, headers=query_headers)
                if resp.status_code != 200:
                    continue

                result = resp.json()
                status = result.get("output", {}).get("task_status")

                if status == "SUCCEEDED":
                    # 提取识别结果
                    results = result.get("output", {}).get("results", [])
                    if results:
                        # 获取第一个文件的转录结果URL
                        transcription_url = results[0].get("transcription_url")
                        if transcription_url:
                            # 下载转录结果 JSON
                            trans_resp = await client.get(transcription_url)
                            if trans_resp.status_code == 200:
                                trans_data = trans_resp.json()
                                # 提取所有识别文本
                                transcripts = trans_data.get("transcripts", [])
                                texts = []
                                for t in transcripts:
                                    text = t.get("text", "")
                                    if text:
                                        texts.append(text)
                                if texts:
                                    final_text = "".join(texts)
                                    logger.info(f"Paraformer 识别完成: {final_text[:100]}")
                                    return final_text

                        # 备用：直接从 results 中提取文本
                        text = results[0].get("text", "")
                        if text:
                            logger.info(f"Paraformer 识别完成: {text[:100]}")
                            return text

                    logger.warning("Paraformer 任务成功但无识别结果")
                    return None

                elif status == "FAILED":
                    error_msg = result.get("output", {}).get("message", "未知错误")
                    logger.warning(f"Paraformer 识别失败: {error_msg}")
                    return None

                # PENDING / RUNNING 继续等待

            logger.warning("Paraformer 识别超时（30秒）")
            return None

    except Exception as e:
        logger.error(f"Paraformer 语音识别异常: {e}", exc_info=True)
        return None


async def _transcribe_with_openai_compat(
    audio_url: str, api_key: str, settings
) -> Optional[str]:
    """
    降级方案：先下载语音文件，再通过 DashScope OpenAI 兼容接口
    使用 whisper 接口转写
    """
    try:
        logger.info("尝试 OpenAI 兼容接口语音识别...")

        # 先下载语音文件
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(audio_url)
            if resp.status_code != 200:
                logger.warning(f"下载语音文件失败: {resp.status_code}")
                return None
            audio_data = resp.content

        # 保存到临时文件
        suffix = ".wav"
        if ".silk" in audio_url.lower():
            suffix = ".silk"
        elif ".amr" in audio_url.lower():
            suffix = ".amr"

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(audio_data)
            tmp_path = tmp.name

        try:
            # 使用 OpenAI 兼容的 audio transcription（如果支持）
            base_url = (
                os.environ.get("DASHSCOPE_BASE_URL")
                or settings.dashscope_base_url
                or "https://dashscope.aliyuncs.com/compatible-mode/v1"
            )

            async with httpx.AsyncClient(timeout=30) as client:
                with open(tmp_path, "rb") as f:
                    resp = await client.post(
                        f"{base_url}/audio/transcriptions",
                        headers={"Authorization": f"Bearer {api_key}"},
                        files={"file": (f"audio{suffix}", f, "audio/wav")},
                        data={"model": "paraformer-v2"},
                    )

                if resp.status_code == 200:
                    data = resp.json()
                    text = data.get("text", "")
                    if text:
                        logger.info(f"OpenAI 兼容接口识别完成: {text[:100]}")
                        return text

                logger.warning(
                    f"OpenAI 兼容接口识别失败: {resp.status_code} {resp.text[:200]}"
                )
                return None

        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    except Exception as e:
        logger.error(f"OpenAI 兼容接口语音识别异常: {e}", exc_info=True)
        return None
