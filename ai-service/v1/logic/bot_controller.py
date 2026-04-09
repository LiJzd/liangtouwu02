from __future__ import annotations

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from v1.common.db import AsyncSessionLocal, get_session
from v1.logic.bot_agent import handle_message
from v1.objects.bot_models import BotOutbox, BotUser
from v1.objects.bot_schemas import (
    BotHandleRequest,
    BotHandleResponse,
    OutboxMarkRequest,
    OutboxPendingResponse,
    OutboxItem,
)

router = APIRouter()


@router.post("/handle", response_model=BotHandleResponse)
async def handle_message_api(payload: BotHandleRequest, session: AsyncSession = Depends(get_session)):
    """
    这个接口是给外部（比如机器人运行器）调用的主入口。
    就像个专门负责传话的接线员，收到消息就转给 handle_message 那个大管家去处理。
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
    看看发信盒里还有哪些待发的信。
    咱们默认一次拿20封，省得一次性拿太多了看不过来。
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
    给发出去的信“打个戳”。
    要是顺利发出去了就记个时间，要是搞砸了也得把错误记下来。
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
