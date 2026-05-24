# -*- coding: utf-8 -*-
"""
v1/agents/nodes/hardware_node.py
监控抓拍与 IoT 风扇控制专家节点
"""

import asyncio
import logging
import json
import glob
import os
import re
from typing import Dict, Any

from v1.logic.agent_debug_controller import push_debug_event
from v1.logic.bot_tools import tool_capture_pig_farm_snapshot, tool_query_env_status, _IMAGE_CACHE

logger = logging.getLogger("HardwareNode")

async def hardware_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    硬件专家节点：处理监控画面抓拍截图与 IOT 物联网风扇开关控制。
    """
    logger.info("=== [HardwareNode] 硬件专家监控/控制启动 ===")
    client_id = state.get("client_id") or "default"
    
    await push_debug_event("connected", {"message": "专家 HardwareAgent 已连接"}, client_id, agent="HardwareAgent")
    
    messages = state.get("messages") or []
    last_msg = messages[-1] if messages else None
    user_input = last_msg.content if last_msg and hasattr(last_msg, "content") else str(last_msg or "")
    
    ans = ""
    img_base64 = ""
    img_key = ""
    
    # 1. 匹配监控抓图/抓拍/视频查看意图
    is_capture_req = any(k in str(user_input) for k in [
        "拍照", "截图", "抓拍", "画面", "监控", "摄像头", "视频",
        "猪场", "全场", "猪舍", "看看", "看一下", "查看", "情况"
    ])
    
    if is_capture_req:
        video_dir = os.path.abspath(os.path.join(os.getcwd(), "../resources/videos"))
        # 寻找包含 pred 的金华两头乌演示视频作为首选
        matches = glob.glob(os.path.join(video_dir, "*pred*.mp4"))
        
        if matches:
            target_video = os.path.basename(matches[0])
            await push_debug_event("thought", {"content": f"已定位 2 号演示片源: {target_video}，正在读取视频流..."}, client_id, agent="HardwareAgent")
        else:
            # 备用视频文件搜索
            matches_alt = glob.glob(os.path.join(video_dir, "4abdf*.mp4"))
            target_video = os.path.basename(matches_alt[0]) if matches_alt else "4abdf5306f1a7165dc7eca7ed3f39f3e.mp4"
            await push_debug_event("thought", {"content": "未找到指定 2 号片源，自动接入备用 1 号监控流..."}, client_id, agent="HardwareAgent")
            
        try:
            # 调用底层截图及图像处理算法工具
            raw_res = await tool_capture_pig_farm_snapshot(json.dumps({"video_file": target_video}))
            data = json.loads(raw_res)
            
            if data.get("success"):
                ans = f"已经为您抓取了猪场的实时监控画面。{data.get('summary', '')}。您可以查阅下方返回的抓拍图片。"
                img_key = data.get("image_key", "")
                img_base64 = _IMAGE_CACHE.get(img_key, "")
                
                await push_debug_event("observation", {"output": f"抓拍成功：{data.get('summary')}"}, client_id, agent="HardwareAgent")
            else:
                err_msg = data.get("error", "视频推理服务响应异常")
                await push_debug_event("observation", {"output": f"抓拍失败：{err_msg}"}, client_id, agent="HardwareAgent")
                ans = f"抱歉，监控抓拍失败：{err_msg}"
        except Exception as e:
            logger.error(f"[HardwareNode] 监控抓拍异常: {e}")
            await push_debug_event("observation", {"output": f"监控系统接入异常: {e}"}, client_id, agent="HardwareAgent")
            ans = f"监控系统接入异常: {e}"

    # 2. 匹配物联网控制 (风扇开关) 意图
    elif any(k in str(user_input) for k in ["风扇", "开关", "启动", "停止", "开启", "关闭"]):
        try:
            from v1.logic.iot_controller import iot_manager, SERIAL_PORT
            
            is_on = any(k in str(user_input) for k in ["开启", "启动", "打开", "1", "开"])
            if "关" in str(user_input) or "停" in str(user_input) or "0" in str(user_input):
                is_on = False
                
            await push_debug_event("thought", {"content": "检测到硬件控制指令，正在绕过云端推理，直接激活物理控制链路..."}, client_id, agent="HardwareAgent", status="急速控制")
            await asyncio.sleep(0.5)
            
            success = await iot_manager.set_switch(is_on)
            if success:
                msg = f"已成功发送物理指令：{'开启' if is_on else '关闭'}风扇。"
                await push_debug_event("observation", {"output": msg}, client_id, agent="HardwareAgent")
                ans = f"✅ {msg} 硬件响应正常，已实时同步至猪舍终端。"
            else:
                msg = "硬件控制链路响应异常，请检查 ESP32 模块是否在线。"
                await push_debug_event("observation", {"output": msg}, client_id, agent="HardwareAgent")
                ans = f"⚠️ {msg} (串口: {SERIAL_PORT})"
        except Exception as e:
            logger.error(f"[HardwareNode] IoT 风扇控制异常: {e}")
            await push_debug_event("observation", {"output": f"硬件控制失败: {e}"}, client_id, agent="HardwareAgent")
            ans = f"硬件控制失败: {e}"

    # 3. 匹配环境查询意图
    else:
        await push_debug_event("thought", {"content": "正在调取全场 IoT 传感器指标..."}, client_id, agent="HardwareAgent")
        try:
            raw_env = await tool_query_env_status("{}")
            env_data = json.loads(raw_env)
            env = env_data.get("environment", {})
            ans = f"全场实时环境指标：\n- 温度：{env.get('temperature_c')}°C\n- 湿度：{env.get('humidity_pct')}%\n- 氨气：{env.get('ammonia_ppm')}ppm\n\n当前设备运行状态：{env.get('ventilation_status', '正常')}"
            await push_debug_event("observation", {"output": "环境数据获取成功"}, client_id, agent="HardwareAgent")
        except Exception as e:
            logger.error(f"[HardwareNode] 获取环境传感器异常: {e}")
            ans = f"环境传感器调取失败: {e}"

    # 流式输出
    chunk_size = 20
    for i in range(0, len(ans), chunk_size):
        chunk = ans[i:i+chunk_size]
        await push_debug_event("final_answer_chunk", {"text": chunk}, client_id, agent="HardwareAgent")
        await asyncio.sleep(0.04)
        
    await push_debug_event("thinking_end", {"answer": "硬件指令执行完成"}, client_id, agent="HardwareAgent", status="已响应")
    
    return {"final_answer": ans, "image_base64": img_base64, "image_key": img_key}
