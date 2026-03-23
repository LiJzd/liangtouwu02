from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict, Optional

import httpx

_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_PIG_RAG_DIR = os.path.join(_BASE_DIR, "pig_rag")
if _PIG_RAG_DIR not in sys.path:
    sys.path.append(_PIG_RAG_DIR)

from pig_lifecycle_rag import query_pig_growth_prediction

# 全局图片缓存（用于临时存储工具生成的图片）
_IMAGE_CACHE: Dict[str, str] = {}


def get_cached_image(image_key: str) -> Optional[str]:
    """从缓存中获取图片"""
    return _IMAGE_CACHE.get(image_key)

# Java 后端 API 配置
JAVA_API_BASE_URL = os.getenv("JAVA_API_BASE_URL", "http://localhost:8080")
JAVA_API_TIMEOUT = 30.0


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


@tool(name="list_pigs", description="列出猪场内的猪只列表（通过 Java API）")
async def tool_list_pigs(arg: str) -> str:
    """
    调用 Java 后端 API 查询猪只列表
    
    参数:
        limit: 返回数量限制（默认 50）
        abnormal_only: 是否只返回异常猪只（默认 false）
    
    注意：需要从上下文获取 user_id
    """
    data = _parse_args(arg)
    limit = _coerce_int(data.get("limit"), 50) if isinstance(data, dict) else 50
    abnormal_only = data.get("abnormal_only", False) if isinstance(data, dict) else False
    
    # TODO: 从上下文获取真实 user_id（当前使用演示值）
    user_id = "demo_user_001"
    
    try:
        async with httpx.AsyncClient(timeout=JAVA_API_TIMEOUT) as client:
            response = await client.post(
                f"{JAVA_API_BASE_URL}/api/v1/ai-tool/pigs/list",
                headers={"X-User-ID": user_id, "Content-Type": "application/json"},
                json={"limit": limit, "abnormalOnly": abnormal_only}
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get("code") != 200:
                return f"查询失败: {result.get('message', '未知错误')}"
            
            return json.dumps(result.get("data"), ensure_ascii=False, indent=2)
            
    except httpx.HTTPError as e:
        return f"调用 Java API 失败: {str(e)}"
    except Exception as e:
        return f"查询猪只列表异常: {str(e)}"


@tool(name="get_pig_info_by_id", description="查询猪只基础信息与生长周期（通过 Java API）")
async def tool_get_pig_info_by_id(arg: str) -> str:
    """
    调用 Java 后端 API 查询猪只详细档案
    
    参数:
        pig_id: 猪只 ID（必填）
        include_lifecycle: 是否包含生长周期数据（默认 true）
    
    注意：需要从上下文获取 user_id
    """
    data = _parse_args(arg)
    pig_id = None
    include_lifecycle = True
    
    if isinstance(data, dict):
        pig_id = data.get("pig_id")
        if not pig_id and data.get("_args"):
            pig_id = data["_args"][0]
        include_lifecycle = data.get("include_lifecycle", True)
    
    if not pig_id:
        pig_id = (arg or "").strip()
    
    if not pig_id:
        return "用法: 调用 get_pig_info_by_id pig_id=XXX"
    
    # TODO: 从上下文获取真实 user_id（当前使用演示值）
    user_id = "demo_user_001"
    
    try:
        async with httpx.AsyncClient(timeout=JAVA_API_TIMEOUT) as client:
            response = await client.post(
                f"{JAVA_API_BASE_URL}/api/v1/ai-tool/pigs/info",
                headers={"X-User-ID": user_id, "Content-Type": "application/json"},
                json={"pigId": str(pig_id), "includeLifecycle": include_lifecycle}
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get("code") != 200:
                return f"查询失败: {result.get('message', '未知错误')}"
            
            return json.dumps(result.get("data"), ensure_ascii=False, indent=2)
            
    except httpx.HTTPError as e:
        return f"调用 Java API 失败: {str(e)}"
    except Exception as e:
        return f"查询猪只档案异常: {str(e)}"


@tool(name="query_pig_disease_rag", description="查询两头乌猪病症知识库，根据症状描述返回可能的疾病、诊断建议和治疗方案")
async def tool_query_pig_disease_rag(arg: str) -> str:
    """
    查询两头乌猪病症向量库
    
    参数:
        symptoms: 症状描述（如：呕吐、拉稀、咳嗽、发烧等）
    
    返回:
        相关疾病信息、诊断建议和治疗方案
    """
    data = _parse_args(arg)
    
    # 提取症状描述
    symptoms = None
    if isinstance(data, dict):
        symptoms = data.get("symptoms") or data.get("_raw")
    else:
        symptoms = str(arg).strip()
    
    if not symptoms:
        return "用法: 调用 query_pig_disease_rag symptoms=症状描述"
    
    try:
        # TODO: 这里应该调用实际的向量库查询
        # 目前返回模拟数据，你需要实现真实的 RAG 查询逻辑
        
        # 示例：使用 ChromaDB 或其他向量数据库查询
        # from pig_rag.pig_disease_rag import query_disease_knowledge
        # result = query_disease_knowledge(symptoms)
        
        # 临时返回示例数据
        mock_result = {
            "query": symptoms,
            "relevant_diseases": [
                {
                    "disease_name": "急性胃肠炎",
                    "symptoms": ["呕吐", "腹泻", "食欲不振", "精神萎靡"],
                    "causes": ["饲料变质", "饮水不洁", "应激反应"],
                    "treatment": "停食12-24小时，提供清洁饮水，口服补液盐，必要时注射抗生素",
                    "prevention": "保证饲料新鲜，饮水清洁，避免突然换料",
                    "severity": "中等",
                    "similarity": 0.85
                },
                {
                    "disease_name": "传染性胃肠炎",
                    "symptoms": ["严重呕吐", "水样腹泻", "脱水", "体温升高"],
                    "causes": ["病毒感染", "传染性强"],
                    "treatment": "隔离病猪，补液防脱水，抗病毒治疗，对症支持",
                    "prevention": "疫苗接种，严格消毒，隔离病猪",
                    "severity": "严重",
                    "similarity": 0.72
                }
            ],
            "general_advice": "建议立即隔离病猪，观察症状变化，如症状加重请及时联系兽医"
        }
        
        return json.dumps(mock_result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": "查询病症知识库失败",
            "message": str(e)
        }, ensure_ascii=False)


@tool(name="query_pig_growth_prediction", description="生长曲线 RAG 预测未来轨迹")
async def tool_query_pig_growth_prediction(arg: str) -> str:
    data = _parse_args(arg)
    if not isinstance(data, dict):
        return "用法: 调用 query_pig_growth_prediction {\"breed\":\"...\",\"current_month\":3,\"current_month_data\":{...},\"top_n\":3}"

    top_n = _coerce_int(data.get("top_n"), 3) or 3
    pig_id = data.get("pig_id")
    
    # 如果提供了 pig_id，先调用 API 获取猪只信息
    if pig_id and not data.get("breed") and not data.get("current_month"):
        pig_raw = await tool_get_pig_info_by_id(str(pig_id))
        try:
            pig_info = json.loads(pig_raw)
        except Exception:
            return pig_raw
        if isinstance(pig_info, dict) and pig_info.get("error"):
            return pig_raw

        breed = pig_info.get("breed")
        lifecycle = pig_info.get("lifecycle") or []
        current_month = _coerce_int(pig_info.get("currentMonth"), 0) or (len(lifecycle) if isinstance(lifecycle, list) else 0)
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


@tool(name="get_abnormal_pigs", description="查询异常猪只列表（通过 Java API）")
async def tool_get_abnormal_pigs(arg: str) -> str:
    """
    调用 Java 后端 API 查询异常猪只
    
    参数:
        threshold: 健康评分阈值（默认 60）
        limit: 返回数量限制（默认 20）
    
    注意：需要从上下文获取 user_id
    """
    data = _parse_args(arg)
    threshold = _coerce_int(data.get("threshold"), 60) if isinstance(data, dict) else 60
    limit = _coerce_int(data.get("limit"), 20) if isinstance(data, dict) else 20
    
    # TODO: 从上下文获取真实 user_id（当前使用演示值）
    user_id = "demo_user_001"
    
    try:
        async with httpx.AsyncClient(timeout=JAVA_API_TIMEOUT) as client:
            response = await client.post(
                f"{JAVA_API_BASE_URL}/api/v1/ai-tool/pigs/abnormal",
                headers={"X-User-ID": user_id, "Content-Type": "application/json"},
                json={"threshold": threshold, "limit": limit}
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get("code") != 200:
                return f"查询失败: {result.get('message', '未知错误')}"
            
            return json.dumps(result.get("data"), ensure_ascii=False, indent=2)
            
    except httpx.HTTPError as e:
        return f"调用 Java API 失败: {str(e)}"
    except Exception as e:
        return f"查询异常猪只失败: {str(e)}"


@tool(name="get_farm_stats", description="获取猪场统计概览（通过 Java API）")
async def tool_get_farm_stats(arg: str) -> str:
    """
    调用 Java 后端 API 查询猪场整体统计数据
    
    参数: 无需参数
    
    注意：需要从上下文获取 user_id
    """
    # TODO: 从上下文获取真实 user_id（当前使用演示值）
    user_id = "demo_user_001"
    
    try:
        async with httpx.AsyncClient(timeout=JAVA_API_TIMEOUT) as client:
            response = await client.post(
                f"{JAVA_API_BASE_URL}/api/v1/ai-tool/farm/stats",
                headers={"X-User-ID": user_id, "Content-Type": "application/json"},
                json={}
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get("code") != 200:
                return f"查询失败: {result.get('message', '未知错误')}"
            
            return json.dumps(result.get("data"), ensure_ascii=False, indent=2)
            
    except httpx.HTTPError as e:
        return f"调用 Java API 失败: {str(e)}"
    except Exception as e:
        return f"查询猪场统计失败: {str(e)}"


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
        
        import logging
        logger = logging.getLogger("bot_tools")
        
        # 获取视频信息
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        duration = total_frames / fps if fps > 0 else 0
        
        logger.info(f"视频信息: 总帧数={total_frames}, FPS={fps}, 时长={duration:.2f}秒")
        
        # 跳过前5秒，然后顺序读取直到找到有效帧
        if fps > 0:
            skip_frames = int(fps * 5)  # 跳过前5秒
            logger.info(f"跳过前 {skip_frames} 帧")
            
            for i in range(skip_frames):
                cap.read()
        
        # 读取接下来的帧，找到第一个有效的
        frame = None
        success = False
        
        for attempt in range(50):  # 最多尝试50帧
            success, frame = cap.read()
            
            if not success or frame is None:
                logger.warning(f"读取帧失败，尝试 {attempt + 1}/50")
                continue
            
            # 检查帧是否有效
            if frame.size > 0:
                mean_brightness = frame.mean()
                logger.info(f"帧 {attempt}: 亮度={mean_brightness:.2f}, 形状={frame.shape}")
                
                # 只要不是全黑就接受
                if mean_brightness > 5:
                    logger.info(f"找到有效帧")
                    break
        
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
        
        # 在图片上绘制检测框
        annotated_frame = frame.copy()
        for det in detections:
            x1, y1, x2, y2 = int(det.bbox_x1), int(det.bbox_y1), int(det.bbox_x2), int(det.bbox_y2)
            # 绘制边界框
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            # 绘制标签
            label = f"{det.class_name} {det.confidence:.2f}"
            cv2.putText(annotated_frame, label, (x1, y1 - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # 将图片编码为 base64
        import base64
        _, buffer = cv2.imencode('.jpg', annotated_frame)
        image_base64 = base64.b64encode(buffer).decode('utf-8')
        image_data_uri = f"data:image/jpeg;base64,{image_base64}"
        
        # 生成友好的摘要信息
        if len(detections) > 0:
            class_counts = {}
            for det in detections:
                class_counts[det.class_name] = class_counts.get(det.class_name, 0) + 1
            
            summary_parts = []
            for class_name, count in class_counts.items():
                summary_parts.append(f"{count}只{class_name}")
            
            summary = f"检测到 {', '.join(summary_parts)}"
        else:
            summary = "未检测到任何目标"
        
        # 将图片存入全局缓存
        cache_key = f"snapshot_{os.path.basename(video_file)}_{datetime.now().timestamp()}"
        _IMAGE_CACHE[cache_key] = image_data_uri
        
        import logging
        logger = logging.getLogger("bot_tools")
        logger.info(f"图片已存入缓存: {cache_key}, 缓存大小: {len(_IMAGE_CACHE)}")
        
        # 只保留最近的 10 张图片
        if len(_IMAGE_CACHE) > 10:
            oldest_key = min(_IMAGE_CACHE.keys())
            del _IMAGE_CACHE[oldest_key]
            logger.info(f"清理旧图片: {oldest_key}")
        
        # 构建返回结果（简短版本，不包含完整图片）
        result = {
            "success": True,
            "video_file": os.path.basename(video_file),
            "detection_count": len(detections),
            "summary": summary,
            "image_key": cache_key,  # 返回缓存键而不是图片本身
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
        
        # 返回简短的文本描述（完全不包含图片）
        # 图片通过 image_key 从缓存中获取
        return json.dumps({
            "success": True,
            "summary": result["summary"],
            "detection_count": result["detection_count"],
            "image_key": cache_key  # 返回缓存键
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "error": "视频截图识别失败",
            "message": str(e)
        }, ensure_ascii=False)
