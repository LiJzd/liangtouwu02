"""
感知层的数据“合同”

这里定义了咱们和后端系统打交道的规矩。
我们用 Pydantic 来把关，确保传进来的数据都是齐整的。
"""

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List
from datetime import datetime


# ==================== 感知推理请求 DTO ====================

class PerceptionRequest(BaseModel):
    """
    具体的识别请求包。
    
    用来接收从主系统传过来的图像识别任务。
    """
    
    image_url: HttpUrl = Field(
        ...,  # ... 表示必填（等效于 @NotNull）
        description="待推理的图像 URL（支持 HTTP/HTTPS/OSS 链接）",
        examples=["https://example.com/pig_image.jpg"]
    )
    
    task_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="任务唯一标识（由 SpringBoot 端生成，用于追踪）",
        examples=["TASK_20240315_001"]
    )
    
    model_type: str = Field(
        default="yolov8n",
        description="指定使用的 YOLO 模型类型",
        examples=["yolov8n", "yolov8s", "yolov8m"]
    )
    
    confidence_threshold: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="置信度阈值（可选，不传则使用全局配置）"
    )
    
    class Config:
        """Pydantic 配置（生成 JSON Schema 示例）"""
        json_schema_extra = {
            "example": {
                "image_url": "https://oss.example.com/pig_farm/camera01/20240315_120000.jpg",
                "task_id": "TASK_20240315_001",
                "model_type": "yolov8n",
                "confidence_threshold": 0.6
            }
        }


# ==================== 检测目标对象 ====================

class DetectionObject(BaseModel):
    """
    认出来的“宝贝”物件。
    """
    
    class_id: int = Field(..., description="类别 ID（0=猪, 1=人, 2=异常物体等）")
    class_name: str = Field(..., description="类别名称（中文）", examples=["生猪", "饲养员"])
    confidence: float = Field(..., ge=0.0, le=1.0, description="置信度分数")
    
    # 边界框坐标（归一化坐标 0-1）
    bbox_x1: float = Field(..., ge=0.0, le=1.0, description="左上角 X 坐标")
    bbox_y1: float = Field(..., ge=0.0, le=1.0, description="左上角 Y 坐标")
    bbox_x2: float = Field(..., ge=0.0, le=1.0, description="右下角 X 坐标")
    bbox_y2: float = Field(..., ge=0.0, le=1.0, description="右下角 Y 坐标")


# ==================== 感知推理响应 DTO ====================

class PerceptionResponse(BaseModel):
    """
    干完活儿后的回信。
    
    告诉后端咱们识别的结果，还有这次干活花了多少时间。
    """
    
    code: int = Field(default=200, description="业务状态码（200=成功, 500=失败）")
    message: str = Field(default="推理成功", description="响应消息")
    
    task_id: str = Field(..., description="任务 ID（回传用于关联）")
    
    # 推理结果数据
    detections: List[DetectionObject] = Field(
        default_factory=list,
        description="检测到的目标列表"
    )
    
    detection_count: int = Field(default=0, description="检测目标总数")
    
    # 元数据
    inference_time_ms: float = Field(..., description="推理耗时（毫秒）")
    model_version: str = Field(..., description="使用的模型版本")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间戳")
    
    class Config:
        """Pydantic 配置"""
        json_schema_extra = {
            "example": {
                "code": 200,
                "message": "推理成功",
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


# ==================== 统一错误响应 DTO ====================

class ErrorResponse(BaseModel):
    """
    万一出故障了，统一的“道歉声明”。
    """
    
    code: int = Field(..., description="错误码（4xx=客户端错误, 5xx=服务端错误）")
    message: str = Field(..., description="错误描述信息")
    detail: Optional[str] = Field(default=None, description="详细错误堆栈（仅 debug 模式）")
    task_id: Optional[str] = Field(default=None, description="关联的任务 ID（如有）")
    timestamp: datetime = Field(default_factory=datetime.now, description="错误发生时间")
