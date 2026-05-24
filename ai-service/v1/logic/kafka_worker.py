# -*- coding: utf-8 -*-
"""
Kafka 守护进程启动入口

直接引导并拉起 v1.mq.kafka_consumer 主协程，保障架构与命名规范的 100% 对齐。
"""
import asyncio
import sys
from v1.mq.kafka_consumer import main, logger

if __name__ == "__main__":
    logger.info("正在通过 logic/kafka_worker.py 引导启动 v1.mq.kafka_consumer...")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("程序被手动中断退出。")
