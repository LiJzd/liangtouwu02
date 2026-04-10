# -*- coding: utf-8 -*-
"""
智能助手任务调度模块。
负责处理周期性订阅任务，检查并下发每日简报等定时通知。
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
    处理已到期的订阅汇报任务。
    
    执行逻辑：
    1. 时间检查：依据配置时区获取当前系统时间。
    2. 订阅检索：从数据库加载所有活跃的订阅配置。
    3. 任务分发：筛选到期任务，生成简报并载入待发队列。
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
    调度器主循环，周期性触发订阅检查任务。
    """
    settings = get_settings()
    interval = max(10, int(settings.bot_scheduler_interval_seconds))

    while not stop_event.is_set():
        try:
            await process_due_subscriptions()
        except Exception:
            pass
        await asyncio.sleep(interval)
