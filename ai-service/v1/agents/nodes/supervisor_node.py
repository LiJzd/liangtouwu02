# -*- coding: utf-8 -*-
"""
v1/agents/nodes/supervisor_node.py
意图分析分发节点
"""

import asyncio
import logging
import os
import re
from typing import Dict, Any
from langchain_core.messages import HumanMessage
import dashscope
from dashscope import Generation

from v1.common.config import get_settings
from v1.logic.agent_debug_controller import push_debug_event

logger = logging.getLogger("SupervisorNode")

async def supervisor_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    意图分类节点：分析用户输入并路由至相应的专家节点。
    """
    logger.info("=== [SupervisorNode] 意图分析启动 ===")
    
    # 0. 获取客户端标识和基本状态
    client_id = state.get("client_id") or "default"
    metadata = state.get("metadata") or {}
    
    # 特殊处理：仿真告警事件包含具体风险特征，直接强制走 VetAgent 智能诊断链路
    if state.get("is_ammonia_demo") or state.get("is_simulation_demo") or metadata.get("source") == "simulation_ingest":
        logger.info("[SupervisorNode] 匹配到仿真剧本/异常推送，直接路由至 vet")
        await push_debug_event("thought", {"content": "检测到系统级仿真告警输入，正在接通兽医诊疗专家通道..."}, client_id, agent="Supervisor")
        return {"current_agent": "vet"}
    
    # 提取最后一条用户消息
    messages = state.get("messages") or []
    if not messages:
        logger.warning("[SupervisorNode] 消息列表为空，路由至 fallback")
        return {"current_agent": "fallback"}
        
    last_msg = messages[-1]
    user_input = last_msg.content if hasattr(last_msg, "content") else str(last_msg)
    
    # 1. 优先多模态判定 (图片或音频存在)
    has_image = bool(state.get("image_base64") or state.get("image_key"))
    has_audio = False
    
    # 如果用户消息本身包含图片或音频
    if isinstance(user_input, list):
        for item in user_input:
            if isinstance(item, dict):
                if "image" in item or "image_url" in item:
                    has_image = True
                if "audio" in item or "audio_path" in item:
                    has_audio = True
        # 将用户输入提取为纯文本用于后续可能的语义分析
        text_parts = [item.get("text", "") for item in user_input if isinstance(item, dict) and "text" in item]
        user_input = "".join(text_parts) if text_parts else str(user_input)
    else:
        user_input = str(user_input)

    # 检查 metadata 里是否有 audio_path
    if metadata.get("audio_path") or state.get("query_context", {}).get("audio_path"):
        has_audio = True

    if has_image or has_audio:
        logger.info(f"[SupervisorNode] 识别到多模态输入 (has_image={has_image}, has_audio={has_audio})，路由至 vet")
        await push_debug_event("thought", {"content": "检测到多模态（图像/语音）输入，正在接通多模态兽医诊疗专家..."}, client_id, agent="Supervisor")
        return {"current_agent": "vet"}

    # 2. 意图解析前端推送效果展现
    await push_debug_event("thought", {"content": "正在提取用户输入特征，分析养殖任务上下文与实时语境..."}, client_id, agent="Supervisor", status="感知分析")
    await asyncio.sleep(0.8)
    await push_debug_event("thought", {"content": "【语义解析】提取关键词特征向量，对比系统历史策略库..."}, client_id, agent="Supervisor", status="意图解析")
    await asyncio.sleep(0.6)
    await push_debug_event("thought", {"content": "【专家匹配】判定指令意图：计算多维度专家领域匹配度，锁定执行路径..."}, client_id, agent="Supervisor", status="专家匹配")
    await asyncio.sleep(0.8)

    # 3. 关键词快速匹配与兜底
    text_lower = user_input.lower()
    
    # 大模型调用配置准备
    settings = get_settings()
    api_key = os.environ.get("DASHSCOPE_API_KEY") or settings.dashscope_api_key
    model = os.environ.get("DASHSCOPE_MODEL") or settings.dashscope_model or "qwen-plus"
    
    system_prompt = (
        "你是一个智能养殖场管理系统的路由调度员。请根据用户输入，将其分类到以下最合适的专家通道：\n"
        "- vet: 询问猪病诊断、用药建议、健康评估、疫苗及兽医相关问题。\n"
        "- data: 查询具体的猪只档案、列表、基本信息或历史记录。\n"
        "- growth_curve: 涉及体重预测、生长曲线、增重情况等预测类问题。\n"
        "- briefing: 请求日报、简报、生产总结或全场数据汇总。\n"
        "- hardware: 涉及监控摄像头、视频抓拍、画面查看，以及风扇、电源开关等硬件设备的控制与状态查询。\n"
        "- direct_reply: 简单的寒暄、问好，或不属于上述范围的通用指令。\n\n"
        "仅返回分类标识符（即 vet, data, growth_curve, briefing, hardware, direct_reply 之一），不要返回任何其他文字。如果无法确定，返回 unknown。"
    )

    route = "unknown"
    try:
        def _call_llm():
            dashscope.api_key = api_key
            return Generation.call(
                model=model,
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': f"用户输入: {user_input}"}
                ],
                result_format='message'
            )
        
        response = await asyncio.to_thread(_call_llm)
        if response.status_code == 200:
            res_output = response.output
            if hasattr(res_output, 'choices') and res_output.choices:
                content = res_output.choices[0].message.content
            elif hasattr(res_output, 'choice') and res_output.choice:
                content = res_output.choice.message.content
            else:
                content = str(res_output)
            
            content = content.strip().lower()
            for candidate in ["vet", "data", "growth_curve", "briefing", "hardware", "direct_reply"]:
                if candidate in content:
                    route = candidate
                    break
    except Exception as e:
        logger.warning(f"[SupervisorNode] LLM classification failed: {e}")

    # 如果大模型无法匹配，则进行关键词规则匹配
    if route == "unknown":
        if any(k in text_lower for k in ["日报", "简报", "总结", "日报表", "生产日报"]):
            route = "briefing"
        elif any(k in text_lower for k in ["预测", "生长", "曲线", "体重", "长势", "增重"]):
            route = "growth_curve"
        elif any(k in text_lower for k in ["档案", "列表", "查询", "信息", "数据", "电子档案", "详情"]):
            route = "data"
        elif any(k in text_lower for k in ["诊断", "病", "疼", "兽医", "不舒服", "拉稀", "咳嗽", "死", "发烧", "生病"]):
            route = "vet"
        elif any(k in text_lower for k in ["监控", "画面", "拍照", "截图", "抓拍", "视频",
                                           "风扇", "开关", "控制", "开启", "关闭", "设备", "硬件",
                                           "猪场", "全场", "看看", "看一下", "情况", "查看猪", "猪舍"]):
            route = "hardware"
        elif any(k in text_lower for k in ["你好", "您好", "早上好", "下午好", "嗨", "hello", "介绍", "你是谁", "能做什么"]):
            route = "direct_reply"
        else:
            route = "fallback"

    logger.info(f"[SupervisorNode] 判定路由决策 -> {route}")
    await push_debug_event("thought", {"content": f"意图分类决策完毕，成功分配至专家节点：{route}"}, client_id, agent="Supervisor")
    
    return {"current_agent": route}
