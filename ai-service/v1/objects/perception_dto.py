# -*- coding: utf-8 -*-
"""
感知层数据传输对象 (DTO)

定义 AI 服务与后端系统交互的数据协议，利用 Pydantic 进行类型校验。
"""

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List
from datetime import datetime


# --- 感知推理请求 DTO ---

class PerceptionRequest(BaseModel):
    """
    图像识别任务请求。
    接收主系统下发的视觉感知推理任务。
    """
    
    image_url: HttpUrl = Field(
        ...,
        description="待推理图像的 URL 地址（支持 HTTP/HTTPS/OSS）",
        examples=["https://example.com/pig_image.jpg"]
    )
    
    task_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="任务唯一标识符，用于跨系统链路追踪",
        examples=["TASK_20240315_001"]
    )
    
    model_type: str = Field(
        default="yolov8n",
        description="指定推理所用的模型架构或版本",
        examples=["yolov8n", "yolov8s", "yolov8m"]
    )
    
    confidence_threshold: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="置信度过滤阈值，缺省则使用全局配置"
    )
    
    class Config:
        """Pydantic 配置及 JSON Schema 示例"""
        json_schema_extra = {
            "example": {
                "image_url": "https://oss.example.com/pig_farm/camera01/20240315_120000.jpg",
                "task_id": "TASK_20240315_001",
                "model_type": "yolov8n",
                "confidence_threshold": 0.6
            }
        }


# --- 检测目标对象 ---

class DetectionObject(BaseModel):
    """
    识别出的目标实体元数据。
    """
    
    class_id: int = Field(..., description="目标分类 ID")
    class_name: str = Field(..., description="目标分类名称（中文）", examples=["生猪", "饲养员"])
    confidence: float = Field(..., ge=0.0, le=1.0, description="识别置信度")
    
    # 归一化坐标 (0.0 - 1.0)
    bbox_x1: float = Field(..., ge=0.0, le=1.0, description="左上角 X 轴偏移")
    bbox_y1: float = Field(..., ge=0.0, le=1.0, description="左上角 Y 轴偏移")
    bbox_x2: float = Field(..., ge=0.0, le=1.0, description="右下角 X 轴偏移")
    bbox_y2: float = Field(..., ge=0.0, le=1.0, description="右下角 Y 轴偏移")


# --- 感知推理响应 DTO ---

class PerceptionResponse(BaseModel):
    """
    视觉感知推理响应结果。
    """
    
    code: int = Field(default=200, description="业务逻辑状态码")
    message: str = Field(default="Success", description="响应说明")
    
    task_id: str = Field(..., description="关联的任务 ID")
    
    # 推理结果
    detections: List[DetectionObject] = Field(
        default_factory=list,
        description="检测到的目标列表"
    )
    
    detection_count: int = Field(default=0, description="目标总数")
    
    # 性能及元数据
    inference_time_ms: float = Field(..., description="模型推理耗时 (ms)")
    model_version: str = Field(..., description="所用的模型版本")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应生成的时间戳")
    
    class Config:
        """Pydantic 配置"""
        json_schema_extra = {
            "example": {
                "code": 200,
                "message": "Success",
                "task_id": "TASK_20240315_001",
                "detections": [
                    {
                        "class_id": 0,
                        "class_name": "生猪",
                        "confidence": 0.92,
                        "bbox_x1": 0.25,
                        "bbox_y1": 0.30,
                        "bbox_x2": 0.65,
                        "bbox_y2": 0.80
                    }
                ],
                "detection_count": 1,
                "inference_time_ms": 45.6,
                "model_version": "yolov8n",
                "timestamp": "2024-03-15T12:00:00"
            }
        }


# --- 统一错误响应 DTO ---

class ErrorResponse(BaseModel):
    """
    统一错误响应数据对象。
    封装异常状态下的错误码、语义化描述及任务关联信息。
    """
    code: int = Field(..., description="错误码（4xx=客户端错误, 5xx=服务端错误）")
    message: str = Field(..., description="错误描述信息")
    detail: Optional[str] = Field(default=None, description="详细错误堆栈（仅 debug 模式）")
    task_id: Optional[str] = Field(default=None, description="关联的任务 ID（如有）")
    timestamp: datetime = Field(default_factory=datetime.now, description="错误发生时间")
