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
            # [Fix] 增加队列容量，防止长报告流式输出时早期片段被覆盖丢弃
            _debug_queues[client_id] = asyncio.Queue(maxsize=1000)
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


# ============================================================
# LangChain Tracing Handler
# ============================================================

from v1.common.langchain_compat import BaseCallbackHandler

class RichTraceHandler(BaseCallbackHandler):
    """
    对接 LangChain 回调系统的实时追踪处理器。
    将智能体的思考、动作及观察结果实时推送至 SSE 队列。
    """
    def __init__(self, client_id: str, agent_name: str):
        self.client_id = client_id
        self.agent_name = agent_name
        self._current_thought = ""
        self._last_push_time = 0.0  # 用于节流控制

    async def on_llm_new_token(self, token: str, **kwargs) -> None:
        """处理器实时输出的 Token 流（精细化追踪 + 节流保护）"""
        import time
        if token:
            self._current_thought += token
            now = time.time()
            # 节流阈值：约 150ms 推送一次中间状态，避免因推送过密导致前端卡顿
            if now - self._last_push_time > 0.15:
                await push_debug_event("thought", {"content": self._current_thought}, self.client_id, agent=self.agent_name, status="思索中")
                self._last_push_time = now

    async def on_agent_action(self, action: Any, **kwargs) -> Any:
        """处理器决定执行某个工具"""
        tool_name = action.tool
        tool_input = str(action.tool_input)
        thought = getattr(action, 'log', '')
        
        # 将 Thought 部分从 Action 中抽离并推送
        await push_debug_event("action", {
            "tool": tool_name,
            "input": tool_input,
            "thought": thought
        }, self.client_id, agent=self.agent_name, status="执行工具")

    async def on_tool_end(self, output: str, **kwargs) -> Any:
        """处理器获取到工具执行结果"""
        await push_debug_event("observation", {"output": output}, self.client_id, agent=self.agent_name, status="获得观察")

    async def on_agent_finish(self, finish: Any, **kwargs) -> Any:
        """处理器完成最终决策"""
        await push_debug_event("thinking_end", {"answer": finish.return_values.get("output", "")}, self.client_id, agent=self.agent_name, status="决策完成")

    def get_thoughts(self) -> list[str]:
        return [self._current_thought] if self._current_thought else []
