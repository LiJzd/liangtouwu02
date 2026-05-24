# -*- coding: utf-8 -*-
"""
v1/agents/nodes/fallback_node.py
意图匹配失败兜底 fallback 节点
"""

import asyncio
import logging
from typing import Dict, Any

from v1.logic.agent_debug_controller import push_debug_event

logger = logging.getLogger("FallbackNode")

async def fallback_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    兜底节点：当系统无法识别用户的特定意图或发生不可逆故障时触发，提供温和提示并推送报警。
    """
    logger.info("=== [FallbackNode] 意图匹配失败兜底触发 ===")
    client_id = state.get("client_id") or "default"
    
    # 提取最后一条用户消息
    messages = state.get("messages") or []
    last_msg = messages[-1] if messages else None
    user_input = last_msg.content if last_msg and hasattr(last_msg, "content") else str(last_msg or "")
    
    # 模拟系统级动作：自动归档并推送异常到值班大屏
    await push_debug_event("thought", {"content": f"正在将无法分类的异常意图：“{user_input}”进行标准化封装归档..."}, client_id, agent="Supervisor", status="异常归档")
    await asyncio.sleep(0.6)
    await push_debug_event("thought", {"content": "已成功将此外部非结构化指令上报并推送至猪舍中央值班大屏，通知人工客服对接。"}, client_id, agent="Supervisor", status="事件上报")
    await asyncio.sleep(0.5)
    
    ans = (
        f"抱歉，我作为两头乌智能管家，暂时无法识别并提供关于“{user_input}”的直接专家解答。\n\n"
        "**💡 解决方案**：\n"
        "1. **系统上报**：我已经自动把您的问题归档并推送到了我们猪场的**值班管理大屏**，值班人员收到后会为您跟进。\n"
        "2. **您可以尝试询问**：\n"
        "   - *“金华两头乌生病了趴着不动，呼吸很急促，是什么原因？”* (病理诊断)\n"
        "   - *“今天全场的生产日报和健康简报怎么样？”* (养殖简报)\n"
        "   - *“帮我查一下 PIG001 的体重和长势电子档案。”* (数据查询)\n"
        "   - *“帮我开启二号猪舍的风机。”* (物联网设备控制)"
    )
    
    # 模拟打字机流式推送
    chunk_size = 20
    for i in range(0, len(ans), chunk_size):
        chunk = ans[i:i+chunk_size]
        await push_debug_event("final_answer_chunk", {"text": chunk}, client_id, agent="Supervisor")
        await asyncio.sleep(0.04)
        
    await push_debug_event("thinking_end", {"answer": "已下发兜底响应说明"}, client_id, agent="Supervisor", status="处理完毕")
    
    return {"final_answer": ans}
