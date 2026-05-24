# -*- coding: utf-8 -*-
"""
Kafka 异步常驻消费守护协程

订阅 pig-farm-tasks 主题，接收 Java 端投递的多智能体推理任务，
驱动 LangGraph 状态图引擎，并将推理结果投递到 pig-farm-results 主题。
支持网络异常避让重试、多线程/协程并发调度、优雅关闭与异常恢复。
"""
import asyncio
import json
import logging
import os
import signal
import sys
from typing import Dict, Any

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from v1.common.config import get_settings
from v1.agents.base_graph import execute_agent_graph

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("kafka_consumer")

# 强制设置 UTF-8
if sys.platform.startswith("win"):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# 优雅退出标志
keep_running = True

def handle_exit_signal(sig, frame):
    global keep_running
    logger.info(f"收到系统信号 {sig}，准备优雅退出...")
    keep_running = False

# 注册信号
try:
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, handle_exit_signal)
except NotImplementedError:
    # Windows/某些环境可能不支持特定信号
    pass


async def process_message(msg_value: bytes, producer: AIOKafkaProducer, results_topic: str):
    """
    处理单条 Kafka 消息，驱动 LangGraph 引擎，并将结果发回结果 Topic。
    """
    try:
        data = json.loads(msg_value.decode("utf-8"))
    except Exception as e:
        logger.error(f"消息 JSON 解析失败: {e}, 原始数据: {msg_value}")
        return

    client_id = data.get("client_id") or data.get("trace_id") or f"kafka_{asyncio.get_event_loop().time()}"
    user_id = data.get("user_id") or "demo_user"
    user_input = data.get("query") or data.get("user_input") or ""
    messages_list = data.get("messages") or []
    metadata = data.get("metadata") or {}
    image_urls = data.get("image_urls") or []
    audio_path = data.get("audio_path") or None

    logger.info(f"收到来自客户端 {client_id} (用户: {user_id}) 的推理任务: '{user_input[:50]}'")

    # 将历史消息转换为 LangChain 消息实例
    langchain_messages = []
    for m in messages_list:
        role = m.get("role")
        content = m.get("content", "")
        # 支持复杂的 content 结构
        if isinstance(content, list):
            text_parts = [
                item.get("text", "") 
                for item in content 
                if isinstance(item, dict) and item.get("type") == "text"
            ]
            content_str = " ".join(text_parts) if text_parts else ""
        else:
            content_str = content or ""
            
        if role in ("user", "human"):
            langchain_messages.append(HumanMessage(content=content_str))
        elif role in ("assistant", "ai"):
            langchain_messages.append(AIMessage(content=content_str))
        elif role == "system":
            langchain_messages.append(SystemMessage(content=content_str))
    
    # 追加最新的意图
    langchain_messages.append(HumanMessage(content=user_input))

    is_ammonia = bool(
        metadata.get("is_ammonia_demo") or 
        metadata.get("scene") == "ammonia" or 
        metadata.get("ammonia")
    )
    is_simulation = bool(
        metadata.get("is_simulation_demo") or 
        metadata.get("scene") == "simulation" or 
        metadata.get("simulation")
    )

    # 组装初始状态
    init_state = {
        "messages": langchain_messages,
        "current_agent": None,
        "schema_metadata": {},
        "query_context": {
            "image_urls": image_urls,
            "audio_path": audio_path
        },
        "errors": [],
        "client_id": client_id,
        "user_id": user_id,
        "is_ammonia_demo": is_ammonia,
        "is_simulation_demo": is_simulation,
        "metadata": metadata,
        "final_answer": "",
        "image_base64": "",
        "image_key": ""
    }

    try:
        logger.info(f"[{client_id}] 启动 LangGraph 状态图计算...")
        res_state = await execute_agent_graph(init_state)
        
        reply = res_state.get("final_answer") or "系统推理异常，未生成有效回复。"
        image_base64 = res_state.get("image_base64") or ""
        
        res_metadata = {
            "current_agent": res_state.get("current_agent"),
            "image_key": res_state.get("image_key"),
            **res_state.get("metadata", {})
        }

        result_payload = {
            "client_id": client_id,
            "user_id": user_id,
            "reply": reply,
            "image": image_base64,
            "metadata": res_metadata,
            "status": "success"
        }
        logger.info(f"[{client_id}] LangGraph 推理完成，路由至智能体: {res_state.get('current_agent')}")

    except Exception as e:
        logger.exception(f"[{client_id}] LangGraph 执行抛出异常: {e}")
        result_payload = {
            "client_id": client_id,
            "user_id": user_id,
            "reply": f"AI推理服务端处理异常: {str(e)}",
            "image": "",
            "metadata": {"error": str(e)},
            "status": "error",
            "error": str(e)
        }

    # 投递回 Kafka 结果主题
    try:
        payload_bytes = json.dumps(result_payload, ensure_ascii=False).encode("utf-8")
        await producer.send_and_wait(results_topic, payload_bytes)
        logger.info(f"[{client_id}] 结果成功投递至 {results_topic}")
    except Exception as e:
        logger.error(f"[{client_id}] 投递推理结果失败: {e}")


async def main():
    settings = get_settings()
    
    bootstrap_servers = settings.kafka_bootstrap_servers
    group_id = settings.kafka_group_id
    tasks_topic = settings.kafka_tasks_topic
    results_topic = settings.kafka_results_topic

    logger.info("=========================================")
    logger.info("  掌上明猪 - Python AI Kafka 消费守护协程 启动")
    logger.info(f"  Bootstrap Servers: {bootstrap_servers}")
    logger.info(f"  Consumer Group:    {group_id}")
    logger.info(f"  Tasks Topic:       {tasks_topic}")
    logger.info(f"  Results Topic:     {results_topic}")
    logger.info("=========================================")

    # 指数避让退避重试启动逻辑
    retry_delay = 1.0
    max_delay = 60.0

    while keep_running:
        consumer = None
        producer = None
        try:
            logger.info("正在尝试连接 Kafka Broker 并初始化 Consumer/Producer...")
            
            consumer = AIOKafkaConsumer(
                tasks_topic,
                bootstrap_servers=bootstrap_servers,
                group_id=group_id,
                auto_offset_reset="latest",
                enable_auto_commit=True
            )
            
            producer = AIOKafkaProducer(
                bootstrap_servers=bootstrap_servers
            )

            # 启动
            await consumer.start()
            await producer.start()
            
            logger.info("Kafka 连通性校验通过，开始拉取任务队列...")
            # 重置重试延迟
            retry_delay = 1.0

            # 持续拉取消息
            while keep_running:
                try:
                    # 使用 timeout 防止无限期阻塞导致信号无法捕获
                    msg_pack = await consumer.getmany(timeout_ms=1000)
                    for topic_partition, messages in msg_pack.items():
                        for msg in messages:
                            # 异步处理消息，实现高并发
                            asyncio.create_task(
                                process_message(msg.value, producer, results_topic)
                            )
                except Exception as e:
                    logger.error(f"消息循环拉取异常: {e}")
                    # 出错时跳出内循环，重新连 Kafka
                    break

        except Exception as e:
            logger.error(f"Kafka 服务连接失败: {e}")
            # 计算指数避让延迟
            logger.info(f"将在 {retry_delay:.1f} 秒后尝试重新连接...")
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, max_delay)
        finally:
            # 释放连接
            if consumer:
                try:
                    await consumer.stop()
                except Exception as e:
                    logger.debug(f"停止 Consumer 异常: {e}")
            if producer:
                try:
                    await producer.stop()
                except Exception as e:
                    logger.debug(f"停止 Producer 异常: {e}")

    logger.info("Kafka 守护协程正常退出完毕。")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("程序被手动中断退出。")
