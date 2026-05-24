# -*- coding: utf-8 -*-
"""
v1/tools/base_tool.py
统一异常安全工具沙箱装饰器，支持同步和异步工具函数的拦截与优雅错误降级处理
"""

import json
import asyncio
import functools
import logging

logger = logging.getLogger("ToolSandbox")

def safe_tool_sandbox(func):
    """
    统一的强类型工具沙箱装饰器。
    自动检测函数是同步还是异步，并在发生任何未处理 Exception 时捕获它，
    屏蔽 traceback，返回结构化的大模型友好 JSON 错误响应。
    """
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"工具异步调用异常 [{func.__name__}]: {e}", exc_info=True)
            return json.dumps({
                "status": "error",
                "message": f"工具调用故障：{str(e)}，已自动降级处理"
            }, ensure_ascii=False)

    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"工具同步调用异常 [{func.__name__}]: {e}", exc_info=True)
            return json.dumps({
                "status": "error",
                "message": f"工具调用故障：{str(e)}，已自动降级处理"
            }, ensure_ascii=False)

    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper
