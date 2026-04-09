"""
掌上明猪 AI 算法大本营 - FastAPI 入口

这里就像是整个 AI 后台的心脏。
我们主要干了这几件事：
1. 把服务拉起来，定好什么时候开机、什么时候关机。
2. 统一管好报错，别让前端拿到一些莫名其妙的错误代码。
3. 把门口（CORS）守好，让自家前端能进来。
4. 把不同业务的路由都接进来，像拼图一样凑成一个大服务。
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import sys
from datetime import datetime
import asyncio

# 导入内部模块
# v1.common.config: 系统全局配置管理
# v1.objects.perception_dto: 数据传输对象定义
from v1.common.config import get_settings
from v1.objects.perception_dto import ErrorResponse
from v1.common.db import init_db
from v1.logic.bot_scheduler import scheduler_loop

# ==================== 日志系统配置 ====================
# 配置全局日志格式和输出通道（等效于 SpringBoot 的 logback-spring.xml）
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout), # 输出到终端
        logging.FileHandler("./logs/algorithm.log", encoding="utf-8") # 输出到本地日志文件
    ]
)
logger = logging.getLogger(__name__)


# ==================== 服务生命周期 ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    这里管着服务的“生老病死”。
    
    开机的时候：加载配置、初始化数据库、把后台机器人也叫醒。
    关机的时候：优雅地把后台任务掐掉，清理战场。
    """
    # ---------- [启动阶段] ----------
    logger.info("========== 掌上明猪 AI 算法中枢启动中 ==========")
    
    # 获取当前环境变量配置
    settings = get_settings()
    logger.info(f"应用名称: {settings.app_name}")
    logger.info(f"应用版本: {settings.app_version}")
    logger.info(f"核心配置: Host={settings.host}, Port={settings.port}, Debug={settings.debug}")
    logger.info(f"模型依赖: YOLO_MODEL_PATH={settings.yolo_model_path}")
    
    # [性能优化建议]
    # 在生产环境中，应在此处预加载 YOLO 模型到全局变量或 app.state
    # 避免每个预测请求都触发 IO 读取模型文件，从而将延迟降低 1-2 秒
    # TODO: 实现模型单例加载
    
    logger.info("========== 启动完成，等待 API 请求 ==========")
    
    await init_db()
    app.state.bot_stop_event = asyncio.Event()
    app.state.bot_task = asyncio.create_task(scheduler_loop(app.state.bot_stop_event))
    yield  # --- 应用运行中 ---
    
    # ---------- [关闭阶段] ----------
    
    stop_event = getattr(app.state, "bot_stop_event", None)
    if stop_event:
        stop_event.set()
    task = getattr(app.state, "bot_task", None)
    if task:
        await task

    # TODO: 释放显存、解除模型占用等


# ==================== 创建应用实例 ====================

# 把 FastAPI 搞起来
app = FastAPI(
    title="掌上明猪 AI 算法中枢",
    description="后端核心 AI 服务：承载 YOLOv10 对象检测、DTW 轨迹匹配及 RAG 智能预测功能",
    version="1.0.0",
    lifespan=lifespan,
    # 自动生成的交互式 API 文档地址
    docs_url="/docs",  # Swagger UI (类似 /swagger-ui.html)
    redoc_url="/redoc"  # ReDoc 备用文档
)


# ==================== 跨域资源共享 (CORS) 配置 ====================

settings = get_settings()
# 让前端 Vue 页面能顺利调咱们的接口
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins, # 允许的来源列表，由 .env 动态配置
    allow_credentials=True,
    allow_methods=["*"], # 允许所有 HTTP 动词 (GET, POST, etc.)
    allow_headers=["*"], # 允许所有 HTTP 请求头
)


# ==================== 全局拦截报错 ====================

# 1. 处理自定义或预料中的参数验证失败 (ValueError)
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """
    要是代码里某处报了数据校验错误，咱们在这儿统一拦截。
    """
    logger.error(f"业务参数校验失败: {str(exc)}")
    error_response = ErrorResponse(
        code=status.HTTP_400_BAD_REQUEST,
        message="请求参数有误，请检查输入数据",
        detail=str(exc) if settings.debug else None, # 仅在测试环境暴露堆栈
        timestamp=datetime.now()
    )
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=error_response.model_dump(mode='json')
    )

# 2. 处理所有未捕获的系统级异常 (兜底方案)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    万一出了什么没想到的错误，这儿就是最后的兜底。
    """
    logger.error(f"服务器内部异常 [未捕获]: {type(exc).__name__} - {str(exc)}", exc_info=True)
    error_response = ErrorResponse(
        code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message="服务器内部错误，请稍后再试",
        detail=str(exc) if settings.debug else "由于隐私策略，详细错误已在日志中记录",
        timestamp=datetime.now()
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump(mode='json')
    )


# ==================== 系统基础端点 ====================

@app.get("/health", tags=["系统监控"])
async def health_check():
    """
    报个平安，告诉外界咱们的服务还没挂。
    """
    return {
        "status": "UP",
        "service": "Liangtouwu-AI-Service",
        "timestamp": datetime.now(),
        "info": "掌上明猪算法中枢运行正常"
    }


# ==================== 把各模块接进来 ====================

# [生猪检测报告模块] - 处理生猪盘点、异常报表逻辑
try:
    from v1.logic.pig_inspection_controller import router as inspection_router
    app.include_router(
        inspection_router,
        prefix="/api/v1/inspection",
        tags=["生猪检测功能"]
    )
except ImportError as e:
    logger.warning(f"无法加载 生猪检测 模块: {e}")

# [视觉感知推理模块] - 处理 YOLO 目标检测、实时视频流分析
try:
    from v1.logic.perception_controller import router as perception_router
    app.include_router(
        perception_router,
        prefix="/api/v1/perception",
        tags=["感知推理服务"]
    )
except ImportError as e:
    logger.warning(f"无法加载 视觉感知 模块: {e}")


# ==================== 应用启动执行器 ====================


# [QQ Bot 控制器]
try:
    from v1.logic.bot_controller import router as bot_router
    app.include_router(
        bot_router,
        prefix="/api/v1/bot",
        tags=["QQ Bot"]
    )
except ImportError as e:
    logger.warning(f"bot_controller import failed: {e}")

# [Central Agent 控制器 - V1 单智能体]
try:
    from v1.logic.central_agent_controller import router as central_agent_router
    app.include_router(
        central_agent_router,
        prefix="/api/v1/agent",
        tags=["Central Agent (V1)"]
    )
except ImportError as e:
    logger.warning(f"central_agent_controller import failed: {e}")

# [Multi Agent 控制器 - V2 多智能体]
try:
    from v1.logic.multi_agent_controller import router as multi_agent_router
    app.include_router(
        multi_agent_router,
        prefix="/api/v1/agent",
        tags=["Multi Agent (V2)"]
    )
except ImportError as e:
    logger.warning(f"multi_agent_controller import failed: {e}")

# [Agent 调试控制器]
try:
    from v1.logic.agent_debug_controller import router as agent_debug_router
    app.include_router(
        agent_debug_router,
        prefix="/api/v1/agent",
        tags=["Agent Debug"]
    )
except ImportError as e:
    logger.warning(f"agent_debug_controller import failed: {e}")

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




