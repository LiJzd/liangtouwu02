# -*- coding: utf-8 -*-
"""
MySQL 数据库查询工具模块
=======================
本模块专为生猪检测 Agent 设计，用于从关系型数据库中提取生猪的静态档案与动态生命周期数据。

核心职责：
1. 异步数据获取：使用 aiomysql 实现非阻塞式查询，确保高并发下的系统响应能力。
2. 同步适配层：提供同步包装函数，使不支持异步的遗留算法模块也能安全地调用数据库。
3. 数据清洗：处理 JSON 序列化字段，并统一输出为标准化的 JSON 接口格式。

数据库表结构：
- 表名: pig_info
- 关键字段: pig_id (主键), breed (品种), lifecycle (时序数据 JSON), current_weight_kg (当前体重)
"""

import asyncio
import json
import threading
from typing import Any, Dict

import aiomysql

# 导入应用全局配置
from v1.common.config import get_settings


async def get_pig_info_by_id(pig_id: str) -> str:
    """
    异步查询：根据生猪 ID 获取存放在 MySQL 中的完整生命周期档案。
    
    返回：
    - 成功：返回包含生猪属性和月度数据的 JSON 字符串。
    - 失败：返回包含 error 信息的 JSON 字符串。
    """
    settings = get_settings()
    conn = None

    try:
        # 建立数据库连接（参数来自 .env 配置文件）
        conn = await aiomysql.connect(
            host=settings.mysql_host,
            port=settings.mysql_port,
            user=settings.mysql_user,
            password=settings.mysql_password,
            db=settings.mysql_database,
            charset="utf8mb4",
        )

        # 使用 DictCursor 使得查询结果以字典形式返回，方便操作
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            query = """
                SELECT
                    pig_id,
                    breed,
                    lifecycle,
                    current_month,
                    current_weight_kg,
                    created_at,
                    updated_at
                FROM pig_info
                WHERE pig_id = %s
            """
            await cursor.execute(query, (pig_id,))
            result = await cursor.fetchone()

            # 猪只不存在处理
            if not result:
                return json.dumps({"error": f"未在数据库中找到 ID 为 {pig_id} 的猪只记录"}, ensure_ascii=False)

            # 解析 lifecycle 字段 (数据库中通常以文本字符串存储 JSON)
            lifecycle_raw = result.get("lifecycle")
            if isinstance(lifecycle_raw, str):
                try:
                    lifecycle = json.loads(lifecycle_raw)
                except json.JSONDecodeError:
                    lifecycle = []
            elif isinstance(lifecycle_raw, (list, dict)):
                lifecycle = lifecycle_raw
            else:
                lifecycle = []

            # 构建标准化业务响应负载
            payload = {
                "pig_id": result.get("pig_id"),
                "breed": result.get("breed"),
                "lifecycle": lifecycle,
                "current_month": int(result.get("current_month") or 0),
                "current_weight_kg": float(result.get("current_weight_kg") or 0.0),
                # 时间格式标准化为 ISO 字符串
                "created_at": result.get("created_at").isoformat() if result.get("created_at") else None,
                "updated_at": result.get("updated_at").isoformat() if result.get("updated_at") else None,
            }
            return json.dumps(payload, ensure_ascii=False, indent=2)

    except Exception as exc:
        return json.dumps({"error": f"MySQL 查询过程异常: {str(exc)}"}, ensure_ascii=False)
    finally:
        # 确保连接一定被关闭，防止数据库连接泄漏
        if conn is not None:
            conn.close()


async def list_pigs(limit: int = 50) -> str:
    """
    列出猪场内猪只的基础信息（从 pig_info 表读取）。
    返回 JSON，字段包含 pig_id / breed / current_month / current_weight_kg。
    """
    settings = get_settings()
    conn = None

    try:
        conn = await aiomysql.connect(
            host=settings.mysql_host,
            port=settings.mysql_port,
            user=settings.mysql_user,
            password=settings.mysql_password,
            db=settings.mysql_database,
            charset="utf8mb4",
        )
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            query = """
                SELECT
                    pig_id,
                    breed,
                    current_month,
                    current_weight_kg,
                    updated_at
                FROM pig_info
                ORDER BY updated_at DESC
                LIMIT %s
            """
            await cursor.execute(query, (limit,))
            rows = await cursor.fetchall()

        items = []
        for row in rows or []:
            items.append(
                {
                    "pig_id": row.get("pig_id"),
                    "breed": row.get("breed"),
                    "current_month": int(row.get("current_month") or 0),
                    "current_weight_kg": float(row.get("current_weight_kg") or 0.0),
                    "updated_at": row.get("updated_at").isoformat() if row.get("updated_at") else None,
                }
            )
        return json.dumps({"items": items}, ensure_ascii=False, indent=2)
    except Exception as exc:
        return json.dumps({"error": f"MySQL 查询失败: {str(exc)}"}, ensure_ascii=False)
    finally:
        if conn is not None:
            conn.close()


async def get_daily_logs_last_7_days() -> str:
    """
    异步查询：获取过去 7 天内所有猪只的每日行为日志。
    返回 JSON，按猪只 ID 和日期分组。
    """
    settings = get_settings()
    conn = None

    try:
        conn = await aiomysql.connect(
            host=settings.mysql_host,
            port=settings.mysql_port,
            user=settings.mysql_user,
            password=settings.mysql_password,
            db=settings.mysql_database,
            charset="utf8mb4",
        )
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            # 查询过去 7 天的数据
            query = """
                SELECT 
                    pig_id, 
                    log_date, 
                    feed_count, 
                    feed_duration_mins, 
                    water_count, 
                    weight_kg, 
                    activity_level
                FROM daily_pig_logs
                WHERE log_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
                ORDER BY log_date DESC, pig_id ASC
            """
            await cursor.execute(query)
            rows = await cursor.fetchall()

        # 转换为可视化和分析友好的 JSON 结构
        logs = []
        for row in rows or []:
            logs.append({
                "pig_id": row.get("pig_id"),
                "log_date": row.get("log_date").isoformat() if row.get("log_date") else None,
                "feed_count": int(row.get("feed_count") or 0),
                "feed_duration": int(row.get("feed_duration_mins") or 0),
                "water_count": int(row.get("water_count") or 0),
                "weight_kg": float(row.get("weight_kg") or 0.0) if row.get("weight_kg") else None,
                "activity_level": int(row.get("activity_level") or 0)
            })
        return json.dumps({"logs": logs}, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"error": f"MySQL 查询失败: {str(exc)}"}, ensure_ascii=False)
    finally:
        if conn is not None:
            conn.close()


def get_daily_logs_sync() -> str:
    """同步包装器，用于获取过去 7 天的每日日志"""
    def _run() -> str:
        box = {}
        def worker():
            loop = asyncio.new_event_loop()
            try:
                box["result"] = loop.run_until_complete(get_daily_logs_last_7_days())
            except Exception as e:
                box["error"] = e
            finally:
                loop.close()
        t = threading.Thread(target=worker, daemon=True)
        t.start()
        t.join()
        return box.get("result", json.dumps({"error": str(box.get("error"))}))

    try:
        asyncio.get_running_loop()
        return _run()
    except RuntimeError:
        return asyncio.run(get_daily_logs_last_7_days())


def get_pig_info_by_id_sync(pig_id: str) -> str:
    """
    同步包装器：解决异步/同步上下文冲突的“黑科技”。
    
    场景说明：
    算法模块（如某些复杂的数学引擎）可能是纯同步实现的。
    如果直接在 FastAPI 的异步循环中调用 asyncio.run()，会报"事件循环正在运行"的错误。
    
    解决方案：
    开启一个独立的守护线程，在该线程中创建新的事件循环来运行异步查询任务，从而实现“假同步”调用。
    """

    def _run_in_thread() -> str:
        # box 用于在线程间共享结果
        box: Dict[str, Any] = {}

        def worker() -> None:
            # 在子线程创建独立的 loop
            loop = asyncio.new_event_loop()
            try:
                box["result"] = loop.run_until_complete(get_pig_info_by_id(pig_id))
            except Exception as exc:
                box["error"] = exc
            finally:
                loop.close()

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        # 阻塞当前线程直到 worker 线程完成，模拟同步调用效果
        thread.join()

        if "error" in box:
            return json.dumps({"error": f"同步包装器查询失败: {str(box['error'])}"}, ensure_ascii=False)
        return box.get("result", json.dumps({"error": "同步包装器未返回结果"}, ensure_ascii=False))

    try:
        # 检查当前环境是否已有运行中的 Event Loop
        asyncio.get_running_loop()
        # 若有，则开启新线程避开冲突
        return _run_in_thread()
    except RuntimeError:
        # 若当前环境没有 Event Loop，则可以直接运行
        return asyncio.run(get_pig_info_by_id(pig_id))
