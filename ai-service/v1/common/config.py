"""
这里管着整个系统的配置。

咱们把所有的 API 秘钥、数据库地址、模型路径什么的都拢到这儿统一打理。
它会自动去翻 .env 文件或者系统环境变量，咱们想用的时候直接调个 get_settings 拿出来就行，特别省事。
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """
    这就是咱系统的配置大全了。
    
    里面分门别类地装好了：
    - 基础配置：App 叫啥名、版本号是啥。
    - 门牌号：服务器跑在哪个 Host 和端口上。
    - 跨域：专门留门给前端 Vue 页面调接口用的。
    - AI 模型：YOLO 检测和 RAG 相关的路径、参数。
    - 数据库：咱存数的地方。
    - 机器人：QQ Bot 的那些密匙。
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
    一键拿走所有配置。
    
    咱们加了个缓存，保证全厂配置只用加载一次，以后再调就直接拿现成的。
    """
    return Settings()










