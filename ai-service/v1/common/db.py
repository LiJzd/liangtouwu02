from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from v1.common.config import get_settings
from v1.objects.bot_models import Base


def _build_mysql_url() -> str:
    settings = get_settings()
    user = settings.mysql_user
    password = settings.mysql_password
    host = settings.mysql_host
    port = settings.mysql_port
    database = settings.mysql_database
    return f"mysql+aiomysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4"


_engine = create_async_engine(
    _build_mysql_url(),
    pool_pre_ping=True,
    pool_recycle=3600,
)

AsyncSessionLocal = async_sessionmaker(bind=_engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
