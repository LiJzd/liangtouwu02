# -*- coding: utf-8 -*-
"""
Database Connection Management

负责异步数据库引擎初始化、会话工厂配置及数据库表结构自动同步。
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from v1.common.config import get_settings
from v1.objects.bot_models import Base


def _build_mysql_url() -> str:
    """构建 MySQL 异步连接字符串。"""
    settings = get_settings()
    user = settings.mysql_user
    password = settings.mysql_password
    host = settings.mysql_host
    port = settings.mysql_port
    database = settings.mysql_database
    return f"mysql+aiomysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4"


# --- 异步数据库引擎配置 ---
# 配置参数：
# - pool_pre_ping: 每次连接前验证有效性。
# - pool_recycle: 连接回收周期，防止长连接失效。
_engine = create_async_engine(
    _build_mysql_url(),
    pool_pre_ping=True,
    pool_recycle=3600,
)

# --- 异步会话工厂 ---
# 配置参数：
# - expire_on_commit: 事务提交后保持对象可用状态。
AsyncSessionLocal = async_sessionmaker(
    bind=_engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)


async def init_db() -> None:
    """初始化数据库架构，自动创建所有定义的物理表。"""
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    """异步会话生成器，用于依赖注入。"""
    async with AsyncSessionLocal() as session:
        yield session
