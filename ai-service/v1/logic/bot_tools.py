from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict

_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_PIG_RAG_DIR = os.path.join(_BASE_DIR, "pig_rag")
if _PIG_RAG_DIR not in sys.path:
    sys.path.append(_PIG_RAG_DIR)

from mysql_tool import get_pig_info_by_id, list_pigs
from pig_lifecycle_rag import query_pig_growth_prediction


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    handler: Callable[[str], Awaitable[str]]


_REGISTRY: Dict[str, Tool] = {}


def tool(name: str, description: str) -> Callable[[Callable[[str], Awaitable[str]]], Callable[[str], Awaitable[str]]]:
    def decorator(func: Callable[[str], Awaitable[str]]) -> Callable[[str], Awaitable[str]]:
        _REGISTRY[name] = Tool(name=name, description=description, handler=func)
        return func

    return decorator


def list_tools() -> Dict[str, Tool]:
    return dict(_REGISTRY)


def _parse_args(text: str) -> Dict[str, Any]:
    raw = (text or "").strip()
    if not raw:
        return {}
    if raw.startswith("{") or raw.startswith("["):
        try:
            data = json.loads(raw)
            return data if isinstance(data, dict) else {"_args": data}
        except Exception:
            return {"_raw": raw}
    parts = re.split(r"[,\s]+", raw)
    data: Dict[str, Any] = {}
    for part in parts:
        if not part:
            continue
        if "=" in part:
            key, value = part.split("=", 1)
            data[key.strip()] = value.strip()
        else:
            data.setdefault("_args", []).append(part)
    return data


def _parse_json_maybe(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    if not isinstance(value, str):
        return value
    text = value.strip()
    if text.startswith("{") or text.startswith("["):
        try:
            return json.loads(text)
        except Exception:
            return value
    return value


def _coerce_int(value: Any, default: int | None = None) -> int | None:
    try:
        return int(value)
    except Exception:
        return default


@tool(name="当前时间", description="返回服务器当前时间")
async def tool_current_time(_: str) -> str:
    now = datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S")


@tool(name="ping", description="健康检查")
async def tool_ping(_: str) -> str:
    return "pong"


@tool(name="list_tools", description="查看当前可用工具列表")
async def tool_list_tools(_: str) -> str:
    tools = list_tools()
    lines = ["可用工具:"]
    for name, tool in tools.items():
        lines.append(f"- {name}: {tool.description}")
    return "\n".join(lines)


@tool(name="list_pigs", description="列出猪场内的猪只列表 (MySQL)")
async def tool_list_pigs(arg: str) -> str:
    data = _parse_args(arg)
    limit = _coerce_int(data.get("limit"), 50) if isinstance(data, dict) else 50
    return await list_pigs(limit=limit or 50)


@tool(name="get_pig_info_by_id", description="查询猪只基础信息与生长周期 (MySQL)")
async def tool_get_pig_info_by_id(arg: str) -> str:
    data = _parse_args(arg)
    pig_id = None
    if isinstance(data, dict):
        pig_id = data.get("pig_id")
        if not pig_id and data.get("_args"):
            pig_id = data["_args"][0]
    if not pig_id:
        pig_id = (arg or "").strip()
    if not pig_id:
        return "用法: 调用 get_pig_info_by_id pig_id=XXX"
    return await get_pig_info_by_id(str(pig_id))


@tool(name="query_pig_growth_prediction", description="生长曲线 RAG 预测未来轨迹")
async def tool_query_pig_growth_prediction(arg: str) -> str:
    data = _parse_args(arg)
    if not isinstance(data, dict):
        return "用法: 调用 query_pig_growth_prediction {\"breed\":\"...\",\"current_month\":3,\"current_month_data\":{...},\"top_n\":3}"

    top_n = _coerce_int(data.get("top_n"), 3) or 3
    pig_id = data.get("pig_id")
    if pig_id and not data.get("breed") and not data.get("current_month"):
        pig_raw = await get_pig_info_by_id(str(pig_id))
        try:
            pig_info = json.loads(pig_raw)
        except Exception:
            return pig_raw
        if isinstance(pig_info, dict) and pig_info.get("error"):
            return pig_raw

        breed = pig_info.get("breed")
        lifecycle = pig_info.get("lifecycle") or []
        current_month = _coerce_int(pig_info.get("current_month"), 0) or (len(lifecycle) if isinstance(lifecycle, list) else 0)
        month_data = None
        if isinstance(lifecycle, list):
            for item in lifecycle:
                if isinstance(item, dict) and _coerce_int(item.get("month"), None) == current_month:
                    month_data = item
                    break
            if month_data is None and lifecycle:
                month_data = lifecycle[-1] if isinstance(lifecycle[-1], dict) else None

        if not breed or not current_month or not month_data:
            return "缺少参数: breed/current_month/current_month_data"

        return await asyncio.to_thread(
            query_pig_growth_prediction,
            str(breed),
            int(current_month),
            month_data,
            top_n,
        )

    breed = data.get("breed")
    current_month = _coerce_int(data.get("current_month"))
    current_month_data = _parse_json_maybe(data.get("current_month_data"))
    if not (breed and current_month and current_month_data):
        return "用法: 调用 query_pig_growth_prediction {\"breed\":\"...\",\"current_month\":3,\"current_month_data\":{...},\"top_n\":3}"

    return await asyncio.to_thread(
        query_pig_growth_prediction,
        str(breed),
        int(current_month),
        current_month_data,
        top_n,
    )


@tool(name="capture_pig_farm_snapshot", description="截取猪场视频图像并进行 AI 识别，返回检测到的猪只位置和状态")
async def tool_capture_pig_farm_snapshot(arg: str) -> str:
    """
    截取猪场视频的当前帧并进行 YOLO 目标检测
    
    参数:
        video_file: 视频文件名 (可选，默认使用配置的视频文件)
        confidence: 置信度阈值 (可选，默认 0.5)
    
    返回:
        JSON 格式的检测结果，包含检测到的猪只数量、位置和置信度
    """
    import cv2
    import numpy as np
    
    try:
        # 解析参数
        data = _parse_args(arg)
        video_file = None
        confidence = 0.5
        
        if isinstance(data, dict):
            video_file = data.get("video_file")
            confidence = _coerce_int(data.get("confidence"), 50) / 100.0 if data.get("confidence") else 0.5
        
        # 导入感知控制器相关模块
        from v1.logic.perception_controller import get_yolo_model, parse_yolo_results
        from v1.common.config import get_settings
        
        settings = get_settings()
        
        # 确定视频路径
        if not video_file:
            # 使用默认视频路径
            video_dir = os.path.abspath(os.path.join(_BASE_DIR, "../resources/assets"))
            # 查找第一个视频文件
            if os.path.exists(video_dir):
                for f in os.listdir(video_dir):
                    if f.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
                        video_file = os.path.join(video_dir, f)
                        break
        else:
            # 使用指定的视频文件
            video_dir = os.path.abspath(os.path.join(_BASE_DIR, "../resources/assets"))
            video_file = os.path.join(video_dir, video_file)
        
        if not video_file or not os.path.exists(video_file):
            return json.dumps({
                "error": "未找到可用的视频文件",
                "message": "请确保视频文件存在于 resources/assets 目录中"
            }, ensure_ascii=False)
        
        # 打开视频并截取当前帧
        cap = cv2.VideoCapture(video_file)
        if not cap.isOpened():
            return json.dumps({
                "error": "无法打开视频文件",
                "video_file": video_file
            }, ensure_ascii=False)
        
        # 读取一帧
        success, frame = cap.read()
        cap.release()
        
        if not success:
            return json.dumps({
                "error": "无法读取视频帧",
                "video_file": video_file
            }, ensure_ascii=False)
        
        # 使用 YOLO 模型进行检测
        model = get_yolo_model()
        results = model(frame, conf=confidence, verbose=False)
        
        # 解析检测结果
        detections = parse_yolo_results(results, frame.shape, confidence)
        
        # 构建返回结果
        result = {
            "success": True,
            "video_file": os.path.basename(video_file),
            "detection_count": len(detections),
            "detections": []
        }
        
        for det in detections:
            result["detections"].append({
                "class_name": det.class_name,
                "confidence": round(det.confidence, 3),
                "bbox": {
                    "x1": round(det.bbox_x1, 3),
                    "y1": round(det.bbox_y1, 3),
                    "x2": round(det.bbox_x2, 3),
                    "y2": round(det.bbox_y2, 3)
                }
            })
        
        # 生成友好的摘要信息
        if len(detections) > 0:
            class_counts = {}
            for det in detections:
                class_counts[det.class_name] = class_counts.get(det.class_name, 0) + 1
            
            summary_parts = []
            for class_name, count in class_counts.items():
                summary_parts.append(f"{count}只{class_name}")
            
            result["summary"] = f"检测到 {', '.join(summary_parts)}"
        else:
            result["summary"] = "未检测到任何目标"
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": "视频截图识别失败",
            "message": str(e)
        }, ensure_ascii=False)
