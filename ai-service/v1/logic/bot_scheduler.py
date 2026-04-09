"""
这个文件管着后台的“定时提醒”功能。
比如哪个老乡订阅了每日简报，咱们就得定时去数据库里翻翻，看该给谁发报送了。
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select

from v1.common.config import get_settings
from v1.common.db import AsyncSessionLocal
from v1.logic.bot_agent import build_daily_brief, enqueue_brief, is_due
from v1.objects.bot_models import BotSubscription


async def process_due_subscriptions() -> int:
    """
    看看现在有谁该收简报了。
    
    流程大概是：
    1. 查日子：根据配置的时区，看看现在是几点。
    2. 搜名单：去数据库里把所有订阅用户都拎出来。
    3. 挨个发：谁到点儿了，就给谁出一份简报，塞进发信队列里。
    """
    settings = get_settings()
    tz = ZoneInfo(settings.bot_timezone)
    now = datetime.now(tz)
    now_time = now.strftime("%H:%M")
    now_date = now.date()

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(BotSubscription))
        subs = result.scalars().all()
        due = [sub for sub in subs if is_due(sub, now_date, now_time)]

        sent_count = 0
        for sub in due:
            content = await build_daily_brief(session, sub.qq_user_id)
            await enqueue_brief(session, sub.qq_user_id, content)
            sub.last_sent_date = now_date
            sent_count += 1

        if sent_count:
            await session.commit()

    return sent_count


async def scheduler_loop(stop_event: asyncio.Event) -> None:
    """
    这是个永不停歇的小钟表，每隔一段时间就去检查一下有没有该发的订阅。
    """
    settings = get_settings()
    interval = max(10, int(settings.bot_scheduler_interval_seconds))

    while not stop_event.is_set():
        try:
            await process_due_subscriptions()
        except Exception:
            pass
        await asyncio.sleep(interval)
