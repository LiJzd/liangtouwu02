"""
========================================
配置管理模块
========================================
等效于 SpringBoot 的 @Configuration + application.yml

架构定位：
- 使用 pydantic-settings 实现类型安全的配置读取
- 支持从 .env 文件和环境变量自动加载配置
- 提供全局单例配置对象

配置优先级（从高到低）：
1. 环境变量（最高优先级）
2. .env 文件
3. 代码中的默认值（最低优先级）

使用方式：
```python
from v1.common.config import get_settings

settings = get_settings()
print(settings.app_name)
```
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """
    ========================================
    全局配置类
    ========================================
    等效于 SpringBoot 的 @ConfigurationProperties
    
    配置加载优先级：
    1. 环境变量（最高优先级）
    2. .env 文件
    3. 默认值（最低优先级）
    
    配置分类：
    - 应用基础配置：应用名称、版本、调试模式
    - 服务端口配置：监听地址和端口
    - CORS配置：跨域资源共享设置
    - YOLO模型配置：模型路径和推理参数
    - RAG配置：向量数据库和嵌入模型
    - 数据库配置：SQLite/MySQL连接信息
    - QQ Bot配置：机器人认证信息
    - AI服务配置：DashScope API密钥和模型
    - 日志配置：日志级别和文件路径
    """
    
    # ==================== 应用基础配置 ====================
    app_name: str = "掌上明猪-AI算法中枢"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # ==================== 服务端口配置 ====================
    host: str = "0.0.0.0"
    port: int = 8000
    
    # ==================== CORS 跨域配置（与 SpringBoot 端通信必需）====================
    cors_origins: list[str] = ["http://localhost:8080", "http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:5173", "http://127.0.0.1:8080", "http://127.0.0.1:3000"]
    
    # ==================== YOLO 模型配置 ====================
    yolo_model_path: str = "../resources/assets/yolov10m_train_312/weights/best.pt"
    yolo_confidence_threshold: float = 0.25
    yolo_iou_threshold: float = 0.45
    
    # ==================== RAG 向量检索配置 ====================
    vector_db_path: str = "./data/vector_store"
    embedding_model: str = "text-embedding-ada-002"
    
    # ==================== 数据库配置（如需算法端持久化）====================
    database_url: str = "sqlite+aiosqlite:///./algorithm.db"  # 异步 SQLite
    
    # ==================== MySQL 配置 ====================
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = "your_password"
    mysql_database: str = "pig_farm"


    # ==================== QQ Bot 配置 ====================
    bot_app_id: str = ""
    bot_app_secret: str = ""
    bot_api_base: str = "http://127.0.0.1:8000"
    bot_timezone: str = "Asia/Shanghai"

    bot_outbox_poll_seconds: int = 10
    central_agent_url: str = "http://127.0.0.1:8000/api/v1/agent/chat"
    central_agent_api_key: str = ""
    central_agent_timeout_seconds: int = 60
    central_agent_max_history: int = 6
    dashscope_api_key: str = ""
    dashscope_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    dashscope_model: str = "qwen-plus"
    dashscope_vl_model: str = "qwen-vl-max"  # 多模态视觉理解模型
    # ==================== 日志配置 ====================
    log_level: str = "INFO"
    log_file: str = "./logs/algorithm.log"
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore")


@lru_cache()
def get_settings() -> Settings:
    """
    ========================================
    获取全局配置单例
    ========================================
    等效于 SpringBoot 的 @Autowired 注入配置 Bean
    
    实现原理：
    - 使用 @lru_cache 装饰器确保配置对象只被实例化一次（单例模式）
    - 在 FastAPI 中通过 Depends(get_settings) 注入使用
    
    使用示例：
    ```python
    # 方式1：直接调用
    settings = get_settings()
    
    # 方式2：依赖注入（推荐）
    @router.get("/example")
    async def example(settings: Settings = Depends(get_settings)):
        return {"app_name": settings.app_name}
    ```
    
    Returns:
        Settings: 全局配置对象单例
    """
    return Settings()










