# -*- coding: utf-8 -*-
"""
Liangtouwu AI Service - FastAPI Application Entry Point

负责服务生命周期管理、全局异常处理、中间件配置及业务路由分发。
"""

import starlette.requests
import starlette.formparsers

# 解决 "Part exceeded maximum size of 1024KB" 错误
# 提升单个 multipart 分块的最大内存限制（默认 1MB，改为 10MB）
# 因为 Starlette 在方法签名中硬编码了默认值，直接修改类属性可能无效，需修改 __kwdefaults__
starlette.requests.Request.form.__kwdefaults__["max_part_size"] = 10 * 1024 * 1024
starlette.formparsers.MultiPartParser.__init__.__kwdefaults__["max_part_size"] = 10 * 1024 * 1024

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
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- 全局异常处理 ---

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """捕获并处理业务逻辑中的参数校验错误。"""
    logger.error(f"Parameter validation failed: {str(exc)}")
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
    
    # 终于要点火起航了 (相当于 java -jar)
    # 核心参数说明：
    # - host/port: 绑定地址和端口
    # - reload: 由于 Windows 下 watchfiles 稳定性问题，建议生产/测试环境设为 False
    # - log_level: 日志过滤级别
    # 过滤掉 /api/v1/bot/outbox/pending 的访问日志
    class EndpointFilter(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            return record.getMessage().find("/api/v1/bot/outbox/pending") == -1

    logging.getLogger("uvicorn.access").addFilter(EndpointFilter())

    uvicorn.run(
        "main:app", 
        host=settings.host,
        port=settings.port,
        reload=False, 
        log_level=settings.log_level.lower()
    )




