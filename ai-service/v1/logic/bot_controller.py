# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from v1.common.db import AsyncSessionLocal, get_session
from v1.logic.bot_agent import handle_message
from v1.logic.voice_to_text import file_to_text
from v1.objects.bot_models import BotOutbox, BotUser
from v1.objects.bot_schemas import (
    BotHandleRequest,
    BotHandleResponse,
    OutboxMarkRequest,
    OutboxPendingResponse,
    OutboxItem,
    AsrResponse,
)

router = APIRouter()


@router.post("/handle", response_model=BotHandleResponse)
async def handle_message_api(payload: BotHandleRequest, session: AsyncSession = Depends(get_session)):
    """
    智能体交互外部调用接口。
    作为底层交互调用的接入层，接收原始请求并将其分发至核心逻辑层进行处理。
    """
    reply, image = await handle_message(
        session, payload.qq_user_id, payload.message,
        guild_id=payload.guild_id,
        image_urls=payload.image_urls,
    )
    return BotHandleResponse(reply=reply, image=image)


@router.get("/outbox/pending", response_model=OutboxPendingResponse)
async def get_pending_outbox(limit: int = 20) -> OutboxPendingResponse:
    """
    检索处于待处理状态的待发消息任务。
    支持限制单次检索的数量上限。
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(BotOutbox, BotUser.dms_guild_id)
            .join(BotUser, BotUser.qq_user_id == BotOutbox.qq_user_id, isouter=True)
            .where(BotOutbox.status == "pending")
            .order_by(BotOutbox.created_at.asc())
            .limit(limit)
        )
        items: List[OutboxItem] = []
        for outbox, guild_id in result.all():
            items.append(
                OutboxItem(
                    id=outbox.id,
                    qq_user_id=outbox.qq_user_id,
                    guild_id=guild_id,
                    content=outbox.content,
                )
            )
        return OutboxPendingResponse(items=items)


@router.post("/outbox/mark")
async def mark_outbox(payload: OutboxMarkRequest):
    """
    更新待发消息的任务状态。
    记录发送结果，包括成功发送的时间戳或执行失败时的错误摘要。
    """
    async with AsyncSessionLocal() as session:
        values = {
            "status": payload.status,
            "error": payload.error,
            "sent_at": datetime.utcnow() if payload.status == "sent" else None,
        }
        await session.execute(update(BotOutbox).where(BotOutbox.id.in_(payload.ids)).values(**values))
        await session.commit()
        return {"updated": len(payload.ids)}


@router.post("/asr", response_model=AsrResponse)
async def voice_to_text_api(file: UploadFile = File(...)):
    """
    语音转文字接口。
    上传音频文件，返回识别出的文本。
    """
    content = await file.read()
    text = await file_to_text(content, file.filename)
    if text is None:
        return AsrResponse(text="", code=500, message="transcription failed")
    return AsrResponse(text=text)
