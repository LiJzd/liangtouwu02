# -*- coding: utf-8 -*-
"""
v1/agents/nodes/direct_reply_node.py
系统寒暄及直复迎宾节点
"""

import asyncio
import random
import logging
from typing import Dict, Any

from v1.logic.agent_debug_controller import push_debug_event

logger = logging.getLogger("DirectReplyNode")

async def direct_reply_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    直复节点：处理与用户的基本寒暄和迎宾交互。
    """
    logger.info("=== [DirectReplyNode] 寒暄处理启动 ===")
    client_id = state.get("client_id") or "default"
    
    # 提取最后一条用户消息
    messages = state.get("messages") or []
    last_msg = messages[-1] if messages else None
    user_input = last_msg.content if last_msg and hasattr(last_msg, "content") else str(last_msg or "")
    
    welcome_msgs = [
        f"您好！我是两头乌智能管家。关于您提到的“{user_input}”，您可以尝试询问我关于生猪疾病诊断、生产日报简报或者猪只电子档案查询等专业问题。",
        f"收到您的消息啦：“{user_input}”。我是两头乌数字养殖场的 AI 智慧助手。如果您需要查询生猪的生长预测曲线或全场环控监测指标，可以直接告诉我。",
        f"您好，金华两头乌智慧养殖系统为您服务。刚才您说的是：{user_input}。我是全能管家，您可以问我“生成今日日报”或“查看 PIG001 发育档案”等指令。"
    ]
    
    ans = random.choice(welcome_msgs)
    
    # 模拟流式打字机推送
    chunk_size = 15
    for i in range(0, len(ans), chunk_size):
        chunk = ans[i:i+chunk_size]
        await push_debug_event("final_answer_chunk", {"text": chunk}, client_id, agent="Supervisor")
        await asyncio.sleep(0.04)
        
    await push_debug_event("thinking_end", {"answer": "回复已生成"}, client_id, agent="Supervisor", status="直复完毕")
    
    return {"final_answer": ans}
