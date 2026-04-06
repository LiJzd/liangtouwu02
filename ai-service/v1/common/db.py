"""
========================================
数据库连接管理模块
========================================
等效于 SpringBoot 的 DataSource + JPA Configuration

架构定位：
- 使用 SQLAlchemy 异步引擎管理数据库连接
- 提供连接池管理，优化数据库访问性能
- 支持自动创建表结构（类似 JPA 的 ddl-auto）

技术栈：
- SQLAlchemy: Python ORM框架
- aiomysql: 异步MySQL驱动
- AsyncSession: 异步会话管理

使用方式：
```python
from v1.common.db import get_session

async def example():
    async with get_session() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()
```
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from v1.common.config import get_settings
from v1.objects.bot_models import Base


def _build_mysql_url() -> str:
    """
    构建MySQL连接URL
    
    格式: mysql+aiomysql://user:password@host:port/database?charset=utf8mb4
    
    Returns:
        str: 完整的数据库连接URL
    """
    settings = get_settings()
    user = settings.mysql_user
    password = settings.mysql_password
    host = settings.mysql_host
    port = settings.mysql_port
    database = settings.mysql_database
    return f"mysql+aiomysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4"


# ========================================
# 创建异步数据库引擎
# ========================================
# 等效于 SpringBoot 的 DataSource Bean
#
# 配置说明：
# - pool_pre_ping: 连接前先ping，确保连接有效
# - pool_recycle: 连接回收时间（秒），防止连接超时
_engine = create_async_engine(
    _build_mysql_url(),
    pool_pre_ping=True,      # 使用前检查连接是否有效
    pool_recycle=3600,       # 1小时后回收连接
)

# ========================================
# 创建异步会话工厂
# ========================================
# 等效于 SpringBoot 的 EntityManager
#
# 配置说明：
# - expire_on_commit: 提交后不过期对象，允许在事务外访问
AsyncSessionLocal = async_sessionmaker(
    bind=_engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)


async def init_db() -> None:
    """
    初始化数据库表结构
    
    等效于 JPA 的 ddl-auto=update
    
    功能：
    - 根据 ORM 模型自动创建表
    - 如果表已存在则跳过
    - 在应用启动时调用
    """
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    """
    获取数据库会话
    
    等效于 SpringBoot 的 @Autowired EntityManager
    
    使用方式：
    ```python
    async with get_session() as session:
        # 执行数据库操作
        result = await session.execute(select(User))
    ```
    
    Yields:
        AsyncSession: 异步数据库会话
    """
    async with AsyncSessionLocal() as session:
        yield session
