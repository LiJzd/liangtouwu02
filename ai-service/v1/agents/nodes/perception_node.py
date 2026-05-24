# -*- coding: utf-8 -*-
"""
v1/agents/nodes/perception_node.py
舍内环境感知监测节点
"""

import asyncio
import logging
import json
from typing import Dict, Any

from v1.logic.agent_debug_controller import push_debug_event
from v1.logic.bot_tools import tool_query_env_status

logger = logging.getLogger("PerceptionNode")

async def perception_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    环境感知专家节点：查询全场实时环境数据（温度、湿度、氨气等）。
    """
    logger.info("=== [PerceptionNode] 环境感知启动 ===")
    client_id = state.get("client_id") or "default"
    
    await push_debug_event("connected", {"message": "载入 PerceptionAgent 专家模块"}, client_id, agent="PerceptionAgent")
    await push_debug_event("thought", {"content": "正在对接全场 IoP 环境监测网关，同步所有传感器数据..."}, client_id, agent="PerceptionAgent")
    
    ans = ""
    try:
        raw_env = await tool_query_env_status("{}")
        env_data = json.loads(raw_env)
        
        # 提取环境指标并进行人性化 Markdown 格式化展示
        env = env_data.get("environment", {})
        alerts = env_data.get("alerts", ["✅ 环境指标均在正常范围内"])
        
        ans = "# 🌡️ 猪场实时物理环境监测报告\n\n"
        ans += f"- **监测位置**: 全场 (二号猪舍为核心点)\n"
        ans += f"- **更新时间**: {env_data.get('timestamp', '--')}\n"
        ans += f"- **传感器源**: {env_data.get('source', 'simulated_iot')}\n\n"
        
        ans += "### 📊 核心物理指标快照\n"
        ans += "| 指标名称 | 实时观测值 | 安全基准阈值范围 | 运行评估 |\n"
        ans += "| :--- | :--- | :--- | :--- |\n"
        ans += f"| 舍内温度 | {env.get('temperature_c', '--')} °C | 15.0 - 30.0 °C | {'正常' if 15.0 <= env.get('temperature_c', 20) <= 30.0 else '异常'} |\n"
        ans += f"| 舍内湿度 | {env.get('humidity_pct', '--')} % | 55.0 - 85.0 % | {'正常' if 55.0 <= env.get('humidity_pct', 65) <= 85.0 else '异常'} |\n"
        ans += f"| 氨气浓度 | {env.get('ammonia_ppm', '--')} ppm | < 20.0 ppm | {'正常' if env.get('ammonia_ppm', 10) < 20.0 else '⚠️ 超标'} |\n"
        ans += f"| 二氧化碳 | {env.get('co2_ppm', '--')} ppm | < 3000 ppm | {'正常' if env.get('co2_ppm', 1000) < 3000 else '⚠️ 闷气'} |\n"
        ans += f"| 风机工况 | {env.get('ventilation_status', '--')} | -- | 良好 |\n"
        ans += f"| 舍内照明 | {env.get('lighting', '--')} | -- | 自动调节 |\n\n"
        
        ans += "### 🚨 告警与诊断说明\n"
        for alt in alerts:
            ans += f"- {alt}\n"
            
        await push_debug_event("observation", {"output": "实时环境感知网关数据获取成功"}, client_id, agent="PerceptionAgent")
    except Exception as e:
        logger.error(f"[PerceptionNode] 获取环境感知数据异常: {e}")
        ans = f"抱歉，获取全场物理环境监测数据失败。\n错误详情: {e}"
        await push_debug_event("observation", {"output": f"获取环境失败: {e}"}, client_id, agent="PerceptionAgent")

    # 流式输出
    chunk_size = 20
    for i in range(0, len(ans), chunk_size):
        chunk = ans[i:i+chunk_size]
        await push_debug_event("final_answer_chunk", {"text": chunk}, client_id, agent="PerceptionAgent")
        await asyncio.sleep(0.04)
        
    await push_debug_event("thinking_end", {"answer": "环境监测报告发布成功"}, client_id, agent="PerceptionAgent", status="感知完毕")
    
    return {"final_answer": ans}
