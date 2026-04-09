"""
数据库连接管理中心

这儿是咱系统的“后勤大管家”，负责管好跟数据库打交道的那些事儿。
不管是建立连接、管理连接池，还是自动建表，统统都在这里打理。
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from v1.common.config import get_settings
from v1.objects.bot_models import Base


def _build_mysql_url() -> str:
    """
    拼装 MySQL 的连接“地址单”。
    
    把用户名、密码、地址、端口还有库名一股脑儿捏成一个字符串。
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
    初始化数据库底座（建表逻辑）。
    
    在系统启动的时候，咱们会在这儿根据模型把表结构都建好。
    如果表已经在那儿了，咱们就不折腾了，直接跳过。
    """
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    """
    借一个“记账本”（数据库会话）。
    
    谁要往数据库里查点什么、记点什么，就到这里来申领。
    用完之后记得归还（会自动关闭会话）。
    """
    async with AsyncSessionLocal() as session:
        yield session
