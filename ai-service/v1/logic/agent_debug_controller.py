# -*- coding: utf-8 -*-
"""
智能体调试控制器。
通过 SSE (Server-Sent Events) 接口实时推送智能体 ReAct 推理逻辑及追踪日志至前端。
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter()
logger = logging.getLogger("agent_debug")

# 全局调试事件队列（生产环境应使用 Redis Pub/Sub）
_debug_queues: dict[str, asyncio.Queue] = {}
_queue_lock = asyncio.Lock()


async def get_or_create_queue(client_id: str = "default") -> asyncio.Queue:
    """获取或初始化指定客户端的调试消息异步队列。"""
    async with _queue_lock:
        if client_id not in _debug_queues:
            _debug_queues[client_id] = asyncio.Queue(maxsize=100)
        return _debug_queues[client_id]


async def push_debug_event(event_type: str, data: dict, client_id: str = "default", agent: str = None, status: str = None) -> None:
    """
    向调试队列推送事件消息。
    
    支持推送包括推理逻辑（Thought）、工具调用记录（Action）及观察结果（Observation）在内的实时追踪数据。
    """
    queue = await get_or_create_queue(client_id)
    event = {
        "type": event_type,
        "data": data,
        "agent": agent,
        "status": status,
        "timestamp": datetime.now().isoformat()
    }
    try:
        # 非阻塞推送，队列满时丢弃旧事件
        logger.info(f"[SSE Push] Client={client_id} Type={event_type}")
        queue.put_nowait(event)
    except asyncio.QueueFull:
        # 队列满时移除最旧的事件
        try:
            queue.get_nowait()
            queue.put_nowait(event)
            logger.info(f"[SSE Push] Queue Full, replaced oldest event for Client={client_id}")
        except Exception:
            pass


async def cleanup_queue(client_id: str) -> None:
    """清理客户端队列"""
    async with _queue_lock:
        if client_id in _debug_queues:
            del _debug_queues[client_id]


@router.get("/debug/agent-trace")
async def agent_trace_stream(client_id: str = "default"):
    """
    建立智能体追踪日志的 SSE 流连接。
    提供实时推理过程订阅能力。
    """
    async def event_generator() -> AsyncGenerator[str, None]:
        queue = await get_or_create_queue(client_id)
        try:
            # 发送连接成功事件
            yield f"data: {json.dumps({'type': 'connected', 'message': 'Agent 调试流已连接', 'timestamp': datetime.now().isoformat()}, ensure_ascii=False)}\n\n"
            
            while True:
                # 等待事件（带超时，避免连接僵死）
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    # 发送心跳包
                    yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': datetime.now().isoformat()}, ensure_ascii=False)}\n\n"
        except asyncio.CancelledError:
            # 客户端断开连接
            await cleanup_queue(client_id)
            raise
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲
        }
    )


@router.post("/debug/clear")
async def clear_debug_queue(client_id: str = "default"):
    """清空调试队列"""
    await cleanup_queue(client_id)
    return {"message": f"已清空客户端 {client_id} 的调试队列"}
