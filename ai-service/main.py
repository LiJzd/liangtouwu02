# -*- coding: utf-8 -*-
import numpy as np  # 🚀 强制在任何其他逻辑前锁定 numpy 状态，解决 Py3.13 冲突
"""
Liangtouwu AI Service - FastAPI Application Entry Point

负责服务生命周期管理、全局异常处理、中间件配置及业务路由分发。
"""

import starlette.requests
import starlette.formparsers

# 解决 "Part exceeded maximum size of 1024KB" 错误
# 提升单个 multipart 分块的最大内存限制（默认 1MB，改为 10MB）
try:
    if hasattr(starlette.requests.Request.form, "__kwdefaults__") and starlette.requests.Request.form.__kwdefaults__:
        starlette.requests.Request.form.__kwdefaults__["max_part_size"] = 10 * 1024 * 1024
    if hasattr(starlette.formparsers.MultiPartParser.__init__, "__kwdefaults__") and starlette.formparsers.MultiPartParser.__init__.__kwdefaults__:
        starlette.formparsers.MultiPartParser.__init__.__kwdefaults__["max_part_size"] = 10 * 1024 * 1024
except Exception as e:
    logging.getLogger(__name__).warning(f"Failed to apply multipart monkey patch: {e}")

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import sys
from datetime import datetime
import asyncio

from v1.common.config import get_settings
from v1.objects.perception_dto import ErrorResponse
from v1.common.db import init_db
from v1.logic.bot_scheduler import scheduler_loop

# --- 日志配置 ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("./logs/algorithm.log", encoding="utf-8")
    ]
)
logger = logging.getLogger(__name__)


# --- 生命周期管理 ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    管理服务初始化与资源释放逻辑。
    
    启动阶段：加载配置、初始化数据库、启动后台任务。
    停止阶段：终止后台任务、释放相关资源。
    """
    logger.info("Liangtouwu AI Service initializing...")
    
    settings = get_settings()
    logger.info(f"App Name: {settings.app_name}")
    logger.info(f"App Version: {settings.app_version}")
    logger.info(f"Config: Host={settings.host}, Port={settings.port}, Debug={settings.debug}")
    logger.info(f"YOLO Model: {settings.yolo_model_path}")
    
    # 待优化：模型单例加载逻辑
    
    await init_db()
    app.state.bot_stop_event = asyncio.Event()
    app.state.bot_task = asyncio.create_task(scheduler_loop(app.state.bot_stop_event))
    
    logger.info("Service initialized, ready for requests.")
    yield
    
    # 停止阶段逻辑
    stop_event = getattr(app.state, "bot_stop_event", None)
    if stop_event:
        stop_event.set()
    task = getattr(app.state, "bot_task", None)
    if task:
        await task

    # TODO: 释放显存等后续清理工作


# --- 应用实例初始化 ---

app = FastAPI(
    title="Liangtouwu AI Service",
    description="后端核心 AI 服务：集成目标检测、轨迹分析及 RAG 智能预测功能。",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)


# --- CORS 配置 ---

settings = get_settings()


class CORSPreflightMiddleware:
    """
    纯 ASGI 中间件：处理没有 access-control-request-method 头的 OPTIONS，
    以及任何其他 CORSMiddleware 是否安全返回 200。
    """
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope.get("method", "").upper() == "OPTIONS":
            origin = b"*"
            allow_credentials = False
            for name, value in scope.get("headers", []):
                if name.lower() == b"origin":
                    origin = value
                    allow_credentials = True
                    break

            headers = [
                (b"access-control-allow-origin", origin),
                (b"access-control-allow-methods", b"GET, POST, PUT, DELETE, OPTIONS, PATCH"),
                (b"access-control-allow-headers", b"*"),
                (b"access-control-max-age", b"86400"),
                (b"content-length", b"0"),
                (b"vary", b"Origin"),
            ]
            if allow_credentials:
                headers.append((b"access-control-allow-credentials", b"true"))

            logger.debug(f"[CORSPreflightMiddleware] OPTIONS {scope.get('path')} -> 200")
            await send({"type": "http.response.start", "status": 200, "headers": headers})
            await send({"type": "http.response.body", "body": b"", "more_body": False})
            return

        await self.app(scope, receive, send)


# --- CORS 配置 ---

# 使用正则匹配所有 localhost/127.0.0.1 源，比列表更可靠
# allow_origin_regex 会在 is_allowed_origin() 里通过，preflight 返回 200
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# 必须在 CORSMiddleware 之后调用，使其成为最外层入口
# Starlette 的 add_middleware 是前向插入，最后调用的会被包在最外层
app.add_middleware(CORSPreflightMiddleware)
logger.info("[CORS] 已启用 allow_origin_regex 匹配所有 localhost/127.0.0.1 源")


# --- 全局异常处理 ---

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """捕获并处理业务逻辑中的参数校验错误。"""
    logger.error(f"Parameter validation failed: {str(exc)}", exc_info=True)
    error_response = ErrorResponse(
        code=status.HTTP_400_BAD_REQUEST,
        message="Request parameter error",
        detail=str(exc) if settings.debug else None,
        timestamp=datetime.now()
    )
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=error_response.model_dump(mode='json')
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """兜底异常处理逻辑。"""
    logger.error(f"Unhandled system exception: {type(exc).__name__} - {str(exc)}", exc_info=True)
    error_response = ErrorResponse(
        code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message="Internal server error",
        detail=str(exc) if settings.debug else "Internal error recorded in logs",
        timestamp=datetime.now()
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump(mode='json')
    )


# --- 系统监控端点 ---

@app.get("/health", tags=["System"])
async def health_check():
    """提供服务运行状态监控。"""
    return {
        "status": "UP",
        "service": "Liangtouwu-AI-Service",
        "timestamp": datetime.now()
    }


# --- 业务路由集成 ---

# 生猪检测报告模块
try:
    from v1.logic.pig_inspection_controller import router as inspection_router
    app.include_router(
        inspection_router,
        prefix="/api/v1/inspection",
        tags=["Pig Inspection"]
    )
except ImportError as e:
    logger.warning(f"Failed to load Pig Inspection module: {e}")

# 视觉感知推理模块
try:
    from v1.logic.perception_controller import router as perception_router
    app.include_router(
        perception_router,
        prefix="/api/v1/perception",
        tags=["Perception"]
    )
except ImportError as e:
    logger.warning(f"Failed to load Perception module: {e}")

# QQ Bot 模块
try:
    from v1.logic.bot_controller import router as bot_router
    app.include_router(
        bot_router,
        prefix="/api/v1/bot",
        tags=["QQ Bot"]
    )
except ImportError as e:
    logger.warning(f"Failed to load Bot Controller: {e}")

# Central Agent 模块 (V1)
try:
    from v1.logic.central_agent_controller import router as central_agent_router
    app.include_router(
        central_agent_router,
        prefix="/api/v1/agent",
        tags=["Agent V1"]
    )
except ImportError as e:
    logger.warning(f"Failed to load Agent V1 module: {e}")

# Multi Agent 模块 (V2)
try:
    from v1.logic.multi_agent_controller import router as multi_agent_router
    app.include_router(
        multi_agent_router,
        prefix="/api/v1/agent",
        tags=["Agent V2"]
    )
except ImportError as e:
    logger.warning(f"Failed to load Agent V2 module: {e}")

# Agent 调试模块
try:
    from v1.logic.agent_debug_controller import router as agent_debug_router
    app.include_router(
        agent_debug_router,
        prefix="/api/v1/agent",
        tags=["Agent Debug"]
    )
except ImportError as e:
    logger.warning(f"Failed to load Agent Debug module: {e}")

# Agent 仿真模块
try:
    from v1.logic.agent_simulation_controller import router as agent_simulation_router
    app.include_router(
        agent_simulation_router,
        prefix="/api/v1/agent",
        tags=["Agent Simulation"]
    )
except ImportError as e:
    logger.warning(f"agent_simulation_controller import failed: {e}")

# IOT 控制模块 (蓝牙设备控制)
try:
    from v1.logic.iot_controller import router as iot_router
    app.include_router(
        iot_router,
        prefix="/api/v1/iot",
        tags=["IOT Control"]
    )
    logger.info("IOT Control 模块路由挂载成功。")
except ImportError as e:
    logger.warning(f"Failed to load IOT Control module: {e}")

# [静态文件服务 - 调试网页]
try:
    from fastapi.staticfiles import StaticFiles
    import os
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
        logger.info(f"静态文件服务已挂载: /static -> {static_dir}")
except Exception as e:
    logger.warning(f"静态文件服务挂载失败: {e}")

if __name__ == "__main__":
    import uvicorn
    from v1.common.config import get_settings

    settings = get_settings()
    
    # 确保项目根目录在 sys.path 中 (增强稳定性)
    project_root = os.path.dirname(os.path.abspath(__file__))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    # 移除日志噪音
    class EndpointFilter(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            return record.getMessage().find("/api/v1/bot/outbox/pending") == -1

    logging.getLogger("uvicorn.access").addFilter(EndpointFilter())

    print(f"--- 正在使用原生入口启动 AI 服务 (Python {sys.version.split()[0]}) ---")
    uvicorn.run(
        "main:app", 
        host=settings.host,
        port=settings.port,
        reload=False, 
        log_level=settings.log_level.lower()
    )
