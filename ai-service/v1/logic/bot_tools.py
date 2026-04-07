"""
工具注册与管理系统 (Tool Registry & Management System)
=====================================================

本模块是整个AI服务的"工具箱"，负责定义和管理所有可供智能体调用的工具函数。

核心架构：
1. 工具注册机制：使用装饰器模式 (@tool) 自动注册工具到全局注册表
2. 工具调用接口：提供统一的异步调用接口，支持参数解析和错误处理
3. 工具分类：
   - 基础工具：时间查询、健康检查等
   - 数据查询工具：猪只档案、列表查询（通过Java API）
   - 诊断工具：疾病知识库、环境监测、历史病例检索
   - 预测工具：生长曲线预测（基于RAG）
   - 告警工具：异常告警发布与语音播报
   - 视觉工具：视频截图与AI识别

工具注册流程：
1. 使用 @tool(name, description) 装饰器标记函数
2. 装饰器自动将工具注册到 _REGISTRY 全局字典
3. Agent通过 list_tools() 获取所有可用工具
4. Agent通过 Tool.handler(arg) 调用具体工具

工具调用约定：
- 所有工具函数必须是异步函数 (async def)
- 输入参数统一为字符串类型（支持JSON格式）
- 返回值统一为字符串类型（通常是JSON格式）
- 工具内部负责参数解析、类型转换和错误处理
"""
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

# 动态路径配置：确保可以导入 pig_rag 模块
_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_PIG_RAG_DIR = os.path.join(_BASE_DIR, "pig_rag")
if _PIG_RAG_DIR not in sys.path:
    sys.path.append(_PIG_RAG_DIR)

from pig_lifecycle_rag import query_pig_growth_prediction

# ============================================================
# 全局缓存与配置
# ============================================================

# 图片缓存：用于临时存储工具生成的图片（Base64编码）
# 键：图片缓存键（如 "snapshot_video1_timestamp"）
# 值：Base64编码的图片数据（不含data URI前缀）
_IMAGE_CACHE: Dict[str, str] = {}


def get_cached_image(image_key: str) -> Optional[str]:
    """
    从全局缓存中获取图片
    
    Args:
        image_key: 图片缓存键
    
    Returns:
        Base64编码的图片数据，如果不存在则返回None
    """
    return _IMAGE_CACHE.get(image_key)


# Java后端API配置
JAVA_API_BASE_URL = os.getenv("JAVA_API_BASE_URL", "http://localhost:8080")
JAVA_API_TIMEOUT = 30.0  # 超时时间（秒）


# ============================================================
# 工具注册系统核心数据结构
# ============================================================

@dataclass(frozen=True)
class Tool:
    """
    工具定义数据类
    
    Attributes:
        name: 工具名称（唯一标识符）
        description: 工具描述（供LLM理解工具用途）
        handler: 工具处理函数（异步函数，接收字符串参数，返回字符串结果）
    """
    name: str
    description: str
    handler: Callable[[str], Awaitable[str]]


# 全局工具注册表：存储所有已注册的工具
_REGISTRY: Dict[str, Tool] = {}


def tool(name: str, description: str) -> Callable[[Callable[[str], Awaitable[str]]], Callable[[str], Awaitable[str]]]:
    """
    工具注册装饰器
    
    使用方法：
        @tool(name="工具名称", description="工具描述")
        async def my_tool(arg: str) -> str:
            # 工具实现
            return result
    
    Args:
        name: 工具名称（在Agent中调用时使用）
        description: 工具功能描述（LLM根据此描述决定是否调用该工具）
    
    Returns:
        装饰器函数
    """
    def decorator(func: Callable[[str], Awaitable[str]]) -> Callable[[str], Awaitable[str]]:
        # 将工具注册到全局注册表
        _REGISTRY[name] = Tool(name=name, description=description, handler=func)
        return func

    return decorator


def list_tools() -> Dict[str, Tool]:
    """
    获取所有已注册的工具
    
    Returns:
        工具字典，键为工具名称，值为Tool对象
    """
    return dict(_REGISTRY)


# ============================================================
# 工具参数解析辅助函数
# ============================================================

def _parse_args(text: str) -> Dict[str, Any]:
    """
    智能参数解析器：支持多种输入格式，并自动映射常用参数名。
    
    支持的格式：
    1. JSON格式：{"key": "value", "key2": 123}
    2. 键值对格式：key=value, key2=value2
    3. 纯文本格式：直接作为参数
    """
    raw = (text or "").strip()
    data: Dict[str, Any] = {}
    
    if not raw:
        return {}
    
    # 尝试解析为JSON
    if raw.startswith("{") or raw.startswith("["):
        try:
            decoded = json.loads(raw)
            if isinstance(decoded, dict):
                data = decoded
            else:
                data = {"_args": decoded}
        except Exception:
            data = {"_raw": raw}
    else:
        # 解析键值对格式（如：key1=value1, key2=value2）
        parts = re.split(r"[,\s]+", raw)
        for part in parts:
            if not part:
                continue
            if "=" in part:
                key, value = part.split("=", 1)
                data[key.strip()] = value.strip()
            else:
                data.setdefault("_args", []).append(part)
    
    # --- 参数纠偏 (Normalizing Parameter Names) ---
    # 常见幻觉处理：把 id, pigId 统一映射为 pig_id
    if "pig_id" not in data:
        if "id" in data:
            data["pig_id"] = data.pop("id")
        elif "pigId" in data:
            data["pig_id"] = data.pop("pigId")
        elif "pig_ID" in data:
            data["pig_id"] = data.pop("pig_ID")
            
    return data


def _parse_json_maybe(value: Any) -> Any:
    """
    尝试将字符串解析为JSON对象
    
    Args:
        value: 待解析的值
    
    Returns:
        解析后的对象（如果是JSON）或原值
    """
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
    """
    类型安全的整数转换
    
    Args:
        value: 待转换的值
        default: 转换失败时的默认值
    
    Returns:
        转换后的整数或默认值
    """
    try:
        return int(value)
    except Exception:
        return default


# ============================================================
# 基础工具集
# ============================================================

@tool(name="当前时间", description="返回服务器当前时间")
async def tool_current_time(_: str) -> str:
    """
    获取服务器当前时间
    
    Returns:
        格式化的时间字符串（YYYY-MM-DD HH:MM:SS）
    """
    now = datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S")


@tool(name="ping", description="健康检查")
async def tool_ping(_: str) -> str:
    """
    系统健康检查工具
    
    Returns:
        "pong" 表示系统正常运行
    """
    return "pong"


@tool(name="list_tools", description="查看当前可用工具列表")
async def tool_list_tools(_: str) -> str:
    """
    列出所有已注册的工具及其描述
    
    Returns:
        工具列表的文本描述
    """
    tools = list_tools()
    lines = ["可用工具:"]
    for name, tool in tools.items():
        lines.append(f"- {name}: {tool.description}")
    return "\n".join(lines)


# ============================================================
# 数据查询工具集（通过Java后端API）
# ============================================================

@tool(name="list_pigs", description="列出猪场内的猪只列表（通过 Java API）")
async def tool_list_pigs(arg: str) -> str:
    """
    查询猪只列表
    
    调用Java后端API获取猪场内的猪只列表，支持过滤和分页。
    
    参数格式（JSON或键值对）：
        limit: 返回数量限制（默认 50）
        abnormal_only: 是否只返回异常猪只（默认 false）
    
    Returns:
        JSON格式的猪只列表数据
    
    注意：
        - 需要从上下文获取 user_id（当前使用演示值）
        - 返回的数据包含猪只ID、品种、健康状态等基础信息
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
    查询猪只详细档案
    
    根据猪只ID查询完整的档案信息，包括基础信息和生长周期数据。
    
    参数格式（JSON或键值对）：
        pig_id: 猪只 ID（必填）
        include_lifecycle: 是否包含生长周期数据（默认 true）
    
    Returns:
        JSON格式的猪只详细档案，包含：
        - 基础信息：品种、区域、当前体重、当前月龄等
        - 生长周期：每月体重记录（如果 include_lifecycle=true）
    
    注意：
        - 需要从上下文获取 user_id（当前使用演示值）
        - 生长周期数据用于生成生长曲线和预测
    """
    data = _parse_args(arg)
    pig_id = None
    include_lifecycle = True
    
    if isinstance(data, dict):
        pig_id = data.get("pig_id")
        if not pig_id and data.get("_args"):
            pig_id = data["_args"][0]
        include_lifecycle = data.get("include_lifecycle", True)
    
    # 彻底清理 pig_id 可能包含的 JSON 字符（LLM 偶尔会传 {"pig_id": "PIG001"} 作为字符串）
    if not pig_id:
        pig_id = (arg or "").strip()
    
    if isinstance(pig_id, str):
        pig_id = pig_id.strip("'\"")
        if (pig_id.startswith("{") and "id" in pig_id) or pig_id.startswith("id="):
            # 再次尝试解析
            try:
                sub_data = _parse_args(pig_id)
                pig_id = sub_data.get("pig_id") or pig_id
            except Exception:
                pass

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


@tool(name="query_env_status", description="查询猪场当前环境数据（温度、湿度、氨气浓度等IoT传感器数据），用于判断是否环境因素导致发病")
async def tool_query_env_status(arg: str) -> str:
    """
    查询猪场环境状态数据

    参数:
        area: 区域名称（可选，默认查询全场）

    返回:
        JSON 格式的环境数据，包含温度、湿度、氨气、CO2等
    """
    import random
    from datetime import datetime

    data = _parse_args(arg)
    area = data.get("area", "全场") if isinstance(data, dict) else "全场"

    # 尝试从 Java 后端获取真实环境数据
    try:
        async with httpx.AsyncClient(timeout=JAVA_API_TIMEOUT) as client:
            response = await client.post(
                f"{JAVA_API_BASE_URL}/api/v1/ai-tool/farm/stats",
                headers={"X-User-ID": "demo_user_001", "Content-Type": "application/json"},
                json={}
            )
            if response.status_code == 200:
                result = response.json()
                if result.get("code") == 200:
                    # 后端有真实数据，直接返回
                    farm_data = result.get("data", {})
                    env_result = {
                        "source": "real_time_iot",
                        "area": area,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "farm_stats": farm_data,
                    }
                    return json.dumps(env_result, ensure_ascii=False, indent=2)
    except Exception:
        pass  # 后端不可用，使用模拟数据兜底

    # 模拟数据兜底：生成合理范围内的环境参数
    env_result = {
        "source": "simulated_iot",
        "area": area,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "environment": {
            "temperature_c": round(random.uniform(18.0, 28.0), 1),
            "humidity_pct": round(random.uniform(55.0, 80.0), 1),
            "ammonia_ppm": round(random.uniform(5.0, 25.0), 1),
            "co2_ppm": round(random.uniform(800, 2500), 0),
            "ventilation_status": random.choice(["正常运行", "低速运行", "高速运行"]),
            "lighting": random.choice(["自然光", "人工补光", "昏暗"]),
        },
        "alert_thresholds": {
            "temperature_high": 30.0,
            "temperature_low": 15.0,
            "humidity_high": 85.0,
            "ammonia_high": 20.0,
            "co2_high": 3000,
        },
        "recent_weather": {
            "outdoor_temp_c": round(random.uniform(5.0, 35.0), 1),
            "condition": random.choice(["晴", "多云", "阴", "小雨", "大雨"]),
            "season": _get_current_season(),
        },
        "pig_population": {
            "total_count": random.randint(80, 200),
            "abnormal_count": random.randint(0, 5),
        }
    }

    # 模拟环境异常判断
    alerts = []
    env = env_result["environment"]
    thresholds = env_result["alert_thresholds"]
    if env["temperature_c"] > thresholds["temperature_high"]:
        alerts.append(f"⚠️ 舍内温度偏高 ({env['temperature_c']}°C)，可能导致热应激")
    if env["temperature_c"] < thresholds["temperature_low"]:
        alerts.append(f"⚠️ 舍内温度偏低 ({env['temperature_c']}°C)，仔猪易感冒")
    if env["humidity_pct"] > thresholds["humidity_high"]:
        alerts.append(f"⚠️ 湿度过高 ({env['humidity_pct']}%)，易滋生细菌")
    if env["ammonia_ppm"] > thresholds["ammonia_high"]:
        alerts.append(f"⚠️ 氨气浓度超标 ({env['ammonia_ppm']}ppm)，影响呼吸道健康")

    env_result["alerts"] = alerts if alerts else ["✅ 环境指标均在正常范围内"]

    return json.dumps(env_result, ensure_ascii=False, indent=2)


def _get_current_season() -> str:
    """根据当前月份返回季节"""
    month = datetime.now().month
    if month in (3, 4, 5):
        return "春季"
    elif month in (6, 7, 8):
        return "夏季"
    elif month in (9, 10, 11):
        return "秋季"
    else:
        return "冬季"


@tool(name="query_similar_cases", description="查询历史相似病例，根据症状描述在知识库中检索曾经出现过类似症状的案例及其处理结果")
async def tool_query_similar_cases(arg: str) -> str:
    """
    基于 RAG 向量检索查询历史相似病例

    参数:
        symptoms: 症状描述（如：拉稀、咳嗽、不吃料）
        breed: 品种（可选，默认两头乌）

    返回:
        JSON 格式的相似历史案例列表
    """
    data = _parse_args(arg)

    symptoms = None
    breed = "两头乌"
    if isinstance(data, dict):
        symptoms = data.get("symptoms") or data.get("_raw")
        breed = data.get("breed", "两头乌")
    else:
        symptoms = str(arg).strip()

    # 兼容 LLM 传入列表格式的症状（如 ["嗜睡", "虚弱"]）
    if isinstance(symptoms, list):
        symptoms = "、".join(str(s) for s in symptoms)

    if not symptoms:
        return json.dumps({"error": "请提供症状描述"}, ensure_ascii=False)

    # 尝试使用 RAG 向量检索
    try:
        from pig_rag.pig_rag_system import query_similar_pig_records
        rag_result = query_similar_pig_records(
            breed=breed,
            age_days=120,      # 默认使用中等日龄
            weight_kg=50.0,    # 默认中等体重
            top_n=3,
        )
        rag_data = json.loads(rag_result) if isinstance(rag_result, str) else rag_result
    except Exception as e:
        rag_data = {"error": f"RAG 检索失败: {str(e)}"}

    # 构建历史病例库（模拟 + RAG 结合）
    # 这些是两头乌常见的典型病例记录
    historical_cases = [
        {
            "case_id": "CASE-2024-001",
            "date": "2024-11-15",
            "breed": "两头乌",
            "age_months": 4,
            "symptoms": ["腹泻", "食欲下降", "精神萎靡"],
            "diagnosis": "急性肠胃炎（饲料变质引发）",
            "treatment": "停食12小时，口服补液盐+庆大霉素，3天康复",
            "outcome": "治愈",
            "env_factors": "换料期间未过渡"
        },
        {
            "case_id": "CASE-2024-002",
            "date": "2024-12-03",
            "breed": "两头乌",
            "age_months": 3,
            "symptoms": ["咳嗽", "流鼻涕", "体温38.5°C"],
            "diagnosis": "上呼吸道感染（天气骤降引发）",
            "treatment": "阿莫西林+退烧药，加强保暖，5天康复",
            "outcome": "治愈",
            "env_factors": "气温骤降15°C以上"
        },
        {
            "case_id": "CASE-2025-001",
            "date": "2025-01-20",
            "breed": "两头乌",
            "age_months": 6,
            "symptoms": ["皮肤红疹", "瘙痒", "蹭墙"],
            "diagnosis": "疥螨感染",
            "treatment": "伊维菌素皮下注射，患部涂敌百虫，隔离治疗",
            "outcome": "治愈（14天）",
            "env_factors": "圈舍潮湿、通风不良"
        },
        {
            "case_id": "CASE-2025-002",
            "date": "2025-02-10",
            "breed": "两头乌",
            "age_months": 2,
            "symptoms": ["水样腹泻", "脱水", "体温升高至40°C"],
            "diagnosis": "传染性胃肠炎（TGE病毒）",
            "treatment": "隔离+补液+抗病毒+全场消毒，严重者淘汰",
            "outcome": "死亡1头，其余治愈",
            "env_factors": "冬季低温、圈舍消毒不彻底"
        },
        {
            "case_id": "CASE-2025-003",
            "date": "2025-03-05",
            "breed": "两头乌",
            "age_months": 5,
            "symptoms": ["不吃料", "趴卧不起", "腹部胀大"],
            "diagnosis": "胃溃疡（应激+饲料过细）",
            "treatment": "停食24小时，碳酸氢钠灌胃，改粗料，7天好转",
            "outcome": "治愈",
            "env_factors": "转群应激+饲料粉碎过细"
        },
    ]

    # 根据症状做简单的关键词匹配排序
    symptoms_lower = symptoms.lower()
    scored_cases = []
    for case in historical_cases:
        score = 0
        for sym in case["symptoms"]:
            if any(kw in symptoms_lower for kw in sym):
                score += 1
            if any(kw in sym for kw in symptoms_lower if len(kw) > 1):
                score += 1
        scored_cases.append((score, case))

    scored_cases.sort(key=lambda x: x[0], reverse=True)
    matched_cases = [c for _, c in scored_cases[:3]]

    result = {
        "query_symptoms": symptoms,
        "matched_cases": matched_cases,
        "match_count": len(matched_cases),
        "rag_similar_pigs": rag_data,
        "advice": "以上为历史类似案例，仅供参考，具体诊断需结合当前猪只实际状况"
    }

    return json.dumps(result, ensure_ascii=False, indent=2)


@tool(name="query_pig_health_records", description="查询猪只健康档案，支持按ID查单只猪的完整档案或查询当前所有异常猪只")
async def tool_query_pig_health_records(arg: str) -> str:
    """
    查询猪只健康档案

    参数:
        pig_id: 猪只ID（可选，查单只猪详细档案）
        abnormal_only: 只查异常猪只（默认 false）
        threshold: 健康评分阈值（默认 60）

    返回:
        JSON 格式的猪只健康档案或异常猪只列表
    """
    data = _parse_args(arg)

    pig_id = None
    abnormal_only = False
    threshold = 60

    if isinstance(data, dict):
        pig_id = data.get("pig_id")
        abnormal_only = data.get("abnormal_only", False)
        threshold = _coerce_int(data.get("threshold"), 60)
        if not pig_id and data.get("_args"):
            pig_id = data["_args"][0]

    if not pig_id:
        pig_id = (arg or "").strip() if not abnormal_only else None

    user_id = "demo_user_001"

    # 查询单只猪的完整档案
    if pig_id:
        try:
            async with httpx.AsyncClient(timeout=JAVA_API_TIMEOUT) as client:
                response = await client.post(
                    f"{JAVA_API_BASE_URL}/api/v1/ai-tool/pigs/info",
                    headers={"X-User-ID": user_id, "Content-Type": "application/json"},
                    json={"pigId": str(pig_id), "includeLifecycle": True}
                )
                if response.status_code == 200:
                    result = response.json()
                    if result.get("code") == 200:
                        pig_data = result.get("data", {})
                        # 增加健康评估摘要
                        health_summary = _assess_pig_health(pig_data)
                        return json.dumps({
                            "pig_id": pig_id,
                            "basic_info": pig_data,
                            "health_assessment": health_summary,
                        }, ensure_ascii=False, indent=2)
        except Exception:
            pass  # Java API 不可用，使用模拟数据

        # 模拟兜底
        return json.dumps({
            "pig_id": pig_id,
            "basic_info": {
                "breed": "两头乌",
                "current_month": 5,
                "current_weight_kg": 48.5,
                "health_status": "待评估",
            },
            "health_assessment": {
                "score": 75,
                "level": "一般",
                "notes": "无法连接数据库获取详细档案，建议人工核查"
            }
        }, ensure_ascii=False, indent=2)

    # 查询异常猪只列表
    try:
        async with httpx.AsyncClient(timeout=JAVA_API_TIMEOUT) as client:
            response = await client.post(
                f"{JAVA_API_BASE_URL}/api/v1/ai-tool/pigs/abnormal",
                headers={"X-User-ID": user_id, "Content-Type": "application/json"},
                json={"threshold": threshold, "limit": 20}
            )
            if response.status_code == 200:
                result = response.json()
                if result.get("code") == 200:
                    return json.dumps({
                        "abnormal_pigs": result.get("data", []),
                        "threshold": threshold,
                    }, ensure_ascii=False, indent=2)
    except Exception:
        pass

    # 模拟兜底
    return json.dumps({
        "abnormal_pigs": [
            {"pig_id": "LTW-037", "breed": "两头乌", "health_score": 45, "symptoms": ["食欲下降", "精神不振"]},
            {"pig_id": "LTW-052", "breed": "两头乌", "health_score": 55, "symptoms": ["轻微腹泻"]},
        ],
        "threshold": threshold,
        "source": "simulated",
        "note": "模拟数据，仅供参考"
    }, ensure_ascii=False, indent=2)


def _assess_pig_health(pig_data: dict) -> dict:
    """根据猪只档案数据评估健康状况"""
    score = 80  # 基础分

    weight = pig_data.get("current_weight_kg", 0)
    month = pig_data.get("current_month", 0)

    # 体重偏离检查（两头乌参考标准）
    if month > 0 and weight > 0:
        expected_weight = month * 10  # 粗略估算：每月约10kg
        deviation = abs(weight - expected_weight) / expected_weight
        if deviation > 0.3:
            score -= 20
        elif deviation > 0.15:
            score -= 10

    level = "良好" if score >= 80 else ("一般" if score >= 60 else "关注")

    return {
        "score": score,
        "level": level,
        "weight_status": "正常" if month == 0 or abs(weight - month * 10) / max(month * 10, 1) < 0.15 else "偏离标准",
        "notes": "基于档案数据自动评估"
    }


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


@tool(
    name="publish_alert",
    description="触发网页端异常告警大屏，并播放网页端语音播报。当通过其他工具获取到异常（如环境异常、健康异常）时，务必调用此工具将告警发布并触发语音提醒。参数是JSON格式，包含 pigId, area, type, risk, announcementText 字段。",
)
async def tool_publish_alert(arg: str) -> str:
    data = _parse_args(arg)
    if not isinstance(data, dict):
        return json.dumps({"error": "publish_alert expects a JSON object payload."}, ensure_ascii=False)

    payload = {
        "pigId": data.get("pigId") or data.get("pig_id") or "UNKNOWN",
        "area": data.get("area") or "unknown-area",
        "type": data.get("type") or "综合异常",
        "risk": data.get("risk") or "High",
        "timestamp": data.get("timestamp") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "announcementText": data.get("announcementText") or data.get("announcement_text"),
    }
    user_id = str(data.get("user_id") or "agent_system")
    
    import logging
    logger = logging.getLogger("bot_tools")
    logger.info(f"🎙️ 正在调用网页语音播报 / 告警发布工具，播报内容: {payload.get('announcementText')}")

    try:
        async with httpx.AsyncClient(timeout=JAVA_API_TIMEOUT) as client:
            response = await client.post(
                f"{JAVA_API_BASE_URL}/api/v1/ai-tool/alerts/publish",
                headers={"X-User-ID": user_id, "Content-Type": "application/json"},
                json=payload,
            )
            response.raise_for_status()
            result = response.json()

            if result.get("code") != 200:
                return json.dumps(
                    {"error": result.get("message", "publish_alert failed")},
                    ensure_ascii=False,
                )

            return json.dumps(
                {
                    "alert_published": True,
                    "alert": result.get("data"),
                },
                ensure_ascii=False,
            )
    except httpx.HTTPError as e:
        return json.dumps({"error": f"publish_alert HTTP error: {str(e)}"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"publish_alert failed: {str(e)}"}, ensure_ascii=False)


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
            video_dir = os.path.abspath(os.path.join(_BASE_DIR, "../resources/videos"))
            # 查找第一个视频文件
            if os.path.exists(video_dir):
                for f in os.listdir(video_dir):
                    if f.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
                        video_file = os.path.join(video_dir, f)
                        break
        else:
            # 使用指定的视频文件
            video_dir = os.path.abspath(os.path.join(_BASE_DIR, "../resources/videos"))
            video_file = os.path.join(video_dir, video_file)
        
        if not video_file or not os.path.exists(video_file):
            return json.dumps({
                "error": "未找到可用的视频文件",
                "message": "请确保视频文件存在于 resources/videos 目录中"
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
        
        # 将图片编码为 base64（不包含 data URI 前缀，由前端添加）
        import base64
        _, buffer = cv2.imencode('.jpg', annotated_frame)
        image_base64 = base64.b64encode(buffer).decode('utf-8')
        
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
        
        # 将图片存入全局缓存（存储纯 base64，不含 data URI 前缀）
        cache_key = f"snapshot_{os.path.basename(video_file)}_{datetime.now().timestamp()}"
        _IMAGE_CACHE[cache_key] = image_base64
        
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
