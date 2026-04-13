# -*- coding: utf-8 -*-
"""
System Configuration Management

统一管理 API 密钥、数据库连接字符串及模型路径。
从环境变量及 .env 文件中自动加载配置项。
"""

from typing import Any, AnyStr, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """
    应用全局配置类。
    
    包含：
    - 基础配置：应用名称、版本号。
    - 服务配置：Host、Port、CORS 策略。
    - AI 模型配置：YOLO 参数与 RAG 指标。
    - 基础设施配置：数据库、MySQL 及向量库。
    - 第三方集成：QQ Bot 密钥与 Dashscope 模型参数。
    """
    
    # --- 应用基础配置 ---
    app_name: str = "Liangtouwu-AI-Service"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # --- 服务端口配置 ---
    host: str = "0.0.0.0"
    port: int = 8000
    
    # --- CORS 配置 ---
    cors_origins: list[str] = [
        "http://localhost:8080", 
        "http://localhost:3000", 
        "http://localhost:5173", 
        "http://localhost:8888",
        "http://127.0.0.1:5173", 
        "http://127.0.0.1:8080", 
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8888"
    ]
    
    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            import json
            try:
                # 尝试解析 JSON 格式的列表 (e.g. '["a", "b"]')
                return json.loads(v)
            except json.JSONDecodeError:
                # 如果不是 JSON 格式，则按逗号分隔 (e.g. 'a, b')
                return [i.strip() for i in v.split(",") if i.strip()]
        return v
    
    # --- YOLO 模型配置 ---
    yolo_model_path: str = "../resources/assets/yolov10m_train_312/weights/best.pt"
    yolo_confidence_threshold: float = 0.25
    yolo_iou_threshold: float = 0.45
    
    # --- RAG 向量检索配置 ---
    vector_db_path: str = "./data/vector_store"
    embedding_model: str = "text-embedding-ada-002"
    
    # --- 数据库配置 (异步 SQLite) ---
    database_url: str = "sqlite+aiosqlite:///./algorithm.db"
    
    # --- MySQL 配置 ---
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = "your_password"
    mysql_database: str = "pig_farm"


    # --- QQ Bot 配置 ---
    bot_app_id: str = ""
    bot_app_secret: str = ""
    bot_api_base: str = "http://127.0.0.1:8000"
    bot_timezone: str = "Asia/Shanghai"

    bot_outbox_poll_seconds: int = 10
    bot_scheduler_interval_seconds: int = 60
    central_agent_url: str = "http://127.0.0.1:8000/api/v1/agent/chat"
    central_agent_api_key: str = ""
    central_agent_timeout_seconds: int = 60
    central_agent_max_history: int = 6
    dashscope_api_key: str = ""
    dashscope_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    dashscope_model: str = "qwen3.5-plus"
    dashscope_vl_model: str = "qwen3.5-plus"
    dashscope_omni_model: str = "qwen3.5-plus"

    # --- 日志配置 ---
    log_level: str = "INFO"
    log_file: str = "./logs/algorithm.log"
    
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        case_sensitive=False, 
        extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    """
    获取全局单例配置对象。
    
    使用 lru_cache 确保配置在应用运行期间仅加载和解析一次，提升性能。
    """
    return Settings()
