"""
感知推理控制器 - 视觉 AI 的“大本营”

要是想让系统看懂图片或者视频里的猪，全靠这儿了。
里头集成了 YOLO 检测算法，不管是传图片、传 Base64，还是直接看监控直播，
这一层都能帮你搞定，顺便把识别结果清清楚楚地圈出来。
"""

import os
import sys
import time
import logging
from datetime import datetime
from typing import Optional, List
import base64
import io
import numpy as np
from PIL import Image
import cv2

# 抑制 OpenCV FFmpeg 的警告日志 - 必须在导入 cv2 之前设置
os.environ['OPENCV_FFMPEG_LOGLEVEL'] = '-8'
os.environ['OPENCV_LOG_LEVEL'] = 'SILENT'
os.environ['OPENCV_VIDEOIO_DEBUG'] = '0'
os.environ['OPENCV_VIDEOIO_PRIORITY_FFMPEG'] = '0'

# 重定向 stderr 到 devnull 以完全抑制 FFmpeg 警告
import contextlib

@contextlib.contextmanager
def suppress_stderr():
    """上下文管理器：临时抑制 stderr 输出"""
    stderr_fd = sys.stderr.fileno()
    with open(os.devnull, 'w') as devnull:
        old_stderr = os.dup(stderr_fd)
        os.dup2(devnull.fileno(), stderr_fd)
        try:
            yield
        finally:
            os.dup2(old_stderr, stderr_fd)
            os.close(old_stderr)

from fastapi import APIRouter, HTTPException, status, UploadFile, File, Form
from pydantic import BaseModel, Field, HttpUrl

from v1.objects.perception_dto import (
    PerceptionRequest,
    PerceptionResponse,
    DetectionObject,
    ErrorResponse
)
from v1.common.config import get_settings

# ==================== 全局状态与模型兼容性补丁 ====================

# 延迟导入的 YOLO 模型单例，避免应用启动时因加载大模型导致超时
_yolo_model = None
_id_model = None  # ID识别模型
_detection_model = None  # 检测模型（jiance）

# YOLOv10 的兼容性补丁：
# 厂商出的库版本经常变，内部类名也爱乱动。
# 咱们这儿打几个补丁（Monkey Patching），不管外面怎么变，咱这儿都能稳稳地跑。
try:
    import ultralytics.utils.loss
    from ultralytics.nn.modules import head
    
    # 补全 v10Detect 别名 (处理内部命名变更)
    if not hasattr(ultralytics.utils.loss, 'v10Detect'):
        ultralytics.utils.loss.v10Detect = head.v10Detect
        
    # 补全 E2ELoss 别名 (End-to-End Loss)
    if not hasattr(ultralytics.utils.loss, 'E2ELoss'):
        if hasattr(ultralytics.utils.loss, 'v10DetectLoss'):
            ultralytics.utils.loss.E2ELoss = ultralytics.utils.loss.v10DetectLoss
    
    # 补齐 DFLoss 类 (Distribution Focal Loss)
    if not hasattr(ultralytics.utils.loss, 'DFLoss'):
        import torch.nn as nn
        import torch.nn.functional as F
        class DFLoss(nn.Module):
            """分布焦点损失函数的补丁实现"""
            def __init__(self, reg_max):
                super().__init__()
                self.reg_max = reg_max
            def forward(self, pred_dist, target):
                return F.cross_entropy(pred_dist, target)
        ultralytics.utils.loss.DFLoss = DFLoss

    # 修复 YOLOv10 推理返回格式问题：在某些版本中模型可能返回字典格式结果
    # 补丁确保在推理模式下只提取 core 'one2one' 的检测结果
    orig_v10_forward = head.v10Detect.forward
    def patched_v10_forward(self, x):
        res = orig_v10_forward(self, x)
        if not self.training and isinstance(res, dict):
            return res.get("one2one", res)
        return res
    head.v10Detect.forward = patched_v10_forward

except ImportError:
    # 如果环境下未安装 ultralytics，跳过补丁逻辑
    pass

logger = logging.getLogger(__name__)
# 定义 API 路由器，添加 "/api/v1/perception" 前缀在 main.py 中统一挂载
router = APIRouter()


# ==================== 核心辅助逻辑 (Service Layer) ====================

def get_yolo_model():
    """
    把 YOLO 检测模型请出来。
    
    它是懒加载的。第一次用的时候得去硬盘里搬权重、占显存，会稍微卡一下，
    之后就都在内存里了，随叫随到，快得很。
    """
    global _yolo_model
    if _yolo_model is None:
        try:
            from ultralytics import YOLO
            settings = get_settings()
            model_path = settings.yolo_model_path
            logger.info(f"正在加载 YOLO 模型单例: {model_path}")
            # 加载预训练的权重文件
            _yolo_model = YOLO(model_path)
            logger.info("YOLO 模型加载成功，显存初始化完成")
        except Exception as e:
            logger.error(f"YOLO 模型加载失败: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"AI 模型服务未就绪，无法进行推理: {str(e)}"
            )
    return _yolo_model


def get_id_model():
    """获取ID识别模型单例"""
    global _id_model
    if _id_model is None:
        try:
            from ultralytics import YOLO
            id_model_path = os.path.abspath(os.path.join(
                os.path.dirname(__file__), 
                "../../../resources/models/ID models/id_best.pt"
            ))
            logger.info(f"正在加载 ID 识别模型: {id_model_path}")
            _id_model = YOLO(id_model_path)
            logger.info("ID 识别模型加载成功")
        except Exception as e:
            logger.error(f"ID 模型加载失败: {str(e)}")
            _id_model = None
    return _id_model


def get_detection_model():
    """获取检测模型单例（jiance）"""
    global _detection_model
    if _detection_model is None:
        try:
            from ultralytics import YOLO
            detection_model_path = os.path.abspath(os.path.join(
                os.path.dirname(__file__), 
                "../../../resources/models/ID models/jiance_best.pt"
            ))
            logger.info(f"正在加载检测模型: {detection_model_path}")
            _detection_model = YOLO(detection_model_path)
            logger.info("检测模型加载成功")
        except Exception as e:
            logger.error(f"检测模型加载失败: {str(e)}")
            _detection_model = None
    return _detection_model


def load_image_from_url(image_url: str) -> np.ndarray:
    """
    从远程 HTTP URL 加载并解码图像
    
    返回: BGR 格式的 numpy 数组 (OpenCV 标准格式)
    """
    import requests
    try:
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
        # 使用 Pillow 处理图像 IO，以支持多种格式
        image = Image.open(io.BytesIO(response.content))
        # 统一转为 RGB 并再转回 OpenCV 的 BGR 格式
        image_np = cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2BGR)
        return image_np
    except Exception as e:
        logger.error(f"远程图像加载失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无法从指定 URL 获取图像数据: {str(e)}"
        )


def load_image_from_base64(base64_str: str) -> np.ndarray:
    """
    从 Base64 字符串解码图像
    支持带 `data:image/jpeg;base64,` 前缀或纯内容字符串
    """
    try:
        # 处理常见的前端 Base64 字符串格式
        if ',' in base64_str:
            base64_str = base64_str.split(',')[1]
        
        image_bytes = base64.b64decode(base64_str)
        image = Image.open(io.BytesIO(image_bytes))
        image_np = cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2BGR)
        return image_np
    except Exception as e:
        logger.error(f"Base64 图像解码失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"图像 Base64 格式非法或已损坏: {str(e)}"
        )


def parse_yolo_results(results, image_shape, confidence_threshold: float) -> List[DetectionObject]:
    """
    把模型吐出来的一堆乱七八糟的数字翻译成咱们人能看懂的格式。
    
    比如把像素坐标换成百分比（归一化），这样不管屏幕多大，圈儿都能画对地方。
    顺便把那些“看着像又不太敢确定”的模糊结果（低于置信度阈值的）给剔除掉。
    """
    detections = []
    
    if len(results) == 0 or results[0].boxes is None:
        return detections
    
    boxes = results[0].boxes
    height, width = image_shape[:2]
    
    for box in boxes:
        # 1. 提取置信度
        conf = float(box.conf[0])
        if conf < confidence_threshold:
            continue
        
        # 2. 提取类别索引及名称
        cls_id = int(box.cls[0])
        cls_name = results[0].names[cls_id]
        
        # 3. 提取边界框坐标 (Top-Left x1y1, Bottom-Right x2y2)
        xyxy = box.xyxy[0].cpu().numpy()
        x1, y1, x2, y2 = xyxy
        
        # 4. 执行归一化计算
        x1_norm = float(x1 / width)
        y1_norm = float(y1 / height)
        x2_norm = float(x2 / width)
        y2_norm = float(y2 / height)
        
        detection = DetectionObject(
            class_id=cls_id,
            class_name=cls_name,
            confidence=conf,
            bbox_x1=x1_norm,
            bbox_y1=y1_norm,
            bbox_x2=x2_norm,
            bbox_y2=y2_norm
        )
        detections.append(detection)
    
    return detections


# ==================== 接口控制层 (Controller Layer) ====================

@router.post("/detect", response_model=PerceptionResponse, tags=["视觉感知"])
async def detect_from_url(request: PerceptionRequest):
    """
    接口 1：基于远程 URL 的目标检测
    (等效于 Java Rest POST 请求)
    """
    start_time = time.time()
    
    try:
        model = get_yolo_model()
        settings = get_settings()
        
        # 加载并解码远程图像
        logger.info(f"[Task:{request.task_id}] 正在请求远程图像推理: {request.image_url}")
        image = load_image_from_url(str(request.image_url))
        
        # 执行模型推理
        confidence = request.confidence_threshold or settings.yolo_confidence_threshold
        results = model(image, conf=confidence, verbose=False)
        
        # 结果结构化包装
        detections = parse_yolo_results(results, image.shape, confidence)
        inference_time = (time.time() - start_time) * 1000
        
        return PerceptionResponse(
            code=200,
            message="视觉推理成功完成",
            task_id=request.task_id,
            detections=detections,
            detection_count=len(detections),
            inference_time_ms=inference_time,
            model_version=f"YOLO-{model.overrides.get('task', 'detect')}",
            timestamp=datetime.now()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"控制层推理执行异常: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"算法后端内部错误: {str(e)}"
        )


class Base64ImageRequest(BaseModel):
    """Base64 图像识别专用的 DTO"""
    image_base64: str = Field(..., description="Base64 编码的图像数据")
    task_id: str = Field(..., min_length=1, max_length=64, description="任务唯一标识")
    confidence_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)


@router.post("/detect/base64", response_model=PerceptionResponse, tags=["视觉感知"])
async def detect_from_base64(request: Base64ImageRequest):
    """
    接口 2：直接传一串 Base64 字符串过来。
    
    通常是前端网页刚拍的照片，或者是小程序里随手传的。
    """
    start_time = time.time()
    
    try:
        model = get_yolo_model()
        settings = get_settings()
        
        logger.info(f"[Task:{request.task_id}] 正在接收并处理 Base64 图像流...")
        image = load_image_from_base64(request.image_base64)
        
        confidence = request.confidence_threshold or settings.yolo_confidence_threshold
        results = model(image, conf=confidence, verbose=False)
        
        detections = parse_yolo_results(results, image.shape, confidence)
        inference_time = (time.time() - start_time) * 1000
        
        return PerceptionResponse(
            code=200,
            message="Base64 图像推理成功",
            task_id=request.task_id,
            detections=detections,
            detection_count=len(detections),
            inference_time_ms=inference_time,
            model_version="yolov10_custom",
            timestamp=datetime.now()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Base64 推理流程故障: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"服务器内部处理错误")


@router.post("/detect/upload", response_model=PerceptionResponse, tags=["视觉感知"])
async def detect_from_upload(
    file: UploadFile = File(..., description="上传的图像文件"),
    task_id: str = Form(..., description="任务唯一标识"),
    confidence_threshold: Optional[float] = Form(default=None, ge=0.0, le=1.0)
):
    """
    接口 3：基于标准 HTTP Multipart 协议的文件上传检测
    """
    start_time = time.time()
    
    try:
        model = get_yolo_model()
        settings = get_settings()
        
        logger.info(f"[Task:{task_id}] 正在处理上传文件: {file.filename}")
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        image_np = cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2BGR)
        
        confidence = confidence_threshold or settings.yolo_confidence_threshold
        results = model(image_np, conf=confidence, verbose=False)
        
        detections = parse_yolo_results(results, image_np.shape, confidence)
        inference_time = (time.time() - start_time) * 1000
        
        return PerceptionResponse(
            code=200,
            message="上传文件识别完成",
            task_id=task_id,
            detections=detections,
            detection_count=len(detections),
            inference_time_ms=inference_time,
            model_version="yolov10_native",
            timestamp=datetime.now()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件上传推理失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="上传图像处理失败")


# ==================== 实时视频流处理 (MJPEG Stream) ====================

def generate_frames(video_path: str):
    """
    这是视频处理的“加工间”。
    
    它会盯着视频看：
    1. 咔嚓一下截一张图（一帧）。
    2. 看看这张图里有没有猪，都是啥状态。
    3. 把看出来的结果画在图上。
    4. 然后马不停蹄地传给前端，连起来就是带框的直播了。
    """
    try:
        cv2.setLogLevel(0)
    except AttributeError:
        pass
    
    cap = None
    try:
        with suppress_stderr():
            cap = cv2.VideoCapture(video_path, cv2.CAP_FFMPEG)
            if cap.isOpened():
                try:
                    cap.set(cv2.CAP_PROP_LOGLEVEL, 0)
                except:
                    pass
        if not cap.isOpened():
            logger.error(f"生成器无法打开视频路径: {video_path}")
            return

        # 加载YOLO模型
        yolo_model = get_yolo_model()
        
        settings = get_settings()
        yolo_names = yolo_model.names
        
        frame_count = 0
        logger.info(f"开始视频流推理（仅状态检测）: {video_path}")

        while True:
            try:
                with suppress_stderr():
                    success, frame = cap.read()
                    
                if not success:
                    logger.info(f"视频播放完毕，重新开始循环")
                    with suppress_stderr():
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue

                frame_count += 1
                
                # YOLO状态检测（不同状态不同颜色）
                yolo_results = yolo_model(frame, conf=settings.yolo_confidence_threshold, verbose=False)
                
                # 状态颜色映射（BGR格式）
                status_colors = {
                    0: (0, 255, 0),      # 绿色
                    1: (255, 0, 0),      # 蓝色
                    2: (0, 165, 255),    # 橙色
                    3: (0, 255, 255),    # 黄色
                    4: (255, 0, 255),    # 品红
                    5: (255, 255, 0),    # 青色
                    6: (128, 0, 128),    # 紫色
                    7: (0, 128, 255),    # 橙红
                }
                
                # 绘制YOLO状态检测框（不同状态不同颜色）
                if len(yolo_results) > 0 and yolo_results[0].boxes is not None:
                    boxes = yolo_results[0].boxes
                    for box in boxes:
                        xyxy = box.xyxy[0].cpu().numpy()
                        x1, y1, x2, y2 = map(int, xyxy)
                        
                        cls_id = int(box.cls[0])
                        status = yolo_names.get(cls_id, f"状态-{cls_id}")
                        conf = float(box.conf[0])
                        
                        # 根据状态类别选择颜色
                        status_color = status_colors.get(cls_id, (0, 255, 0))
                        cv2.rectangle(frame, (x1, y1), (x2, y2), status_color, 4)
                        
                        label = f"{status} {conf:.2f}"
                        font_scale = 1.5
                        font_thickness = 3
                        t_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, font_thickness)[0]
                        
                        padding = 15
                        cv2.rectangle(frame, (x1, y1 - t_size[1] - padding), (x1 + t_size[0] + padding, y1), status_color, -1)
                        cv2.putText(frame, label, (x1 + 8, y1 - 8), 
                                   cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), font_thickness, 
                                   cv2.LINE_AA)

                # 编码为 JPEG 字节流
                ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                if not ret:
                    logger.warning(f"帧 {frame_count} 编码失败")
                    continue
                
                frame_bytes = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                
                time.sleep(0.03)  # 约 30 FPS
                
            except Exception as e:
                logger.error(f"处理帧 {frame_count} 时出错: {e}")
                continue
                
    except Exception as e:
        logger.error(f"视频流生成器异常: {e}")
    finally:
        if cap is not None:
            cap.release()
            logger.info(f"视频流已关闭: {video_path}")


@router.get("/stream/{filename}", tags=["视觉感知"])
async def stream_video(filename: str):
    """
    接口 4：视频直播间系统。
    
    前端只要在 <img> 标签里填上这个地址，就能直接看到 AI 正在识别的现场画面。
    """
    from fastapi.responses import StreamingResponse
    import os
    
    # 路径构造逻辑：相对于当前文件的 ../../../resources/videos 目录
    video_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../resources/videos"))
    video_path = os.path.join(video_dir, filename)
    
    logger.info(f"正在建立 MJPEG 推流连接，文件: {filename}")
    
    if not os.path.exists(video_path):
        # 宽容性处理：若文件名不匹配，则在目录中进行模糊匹配
        logger.warning(f"指定视频不存在，正在执行模糊搜索...")
        found = False
        for f in os.listdir(video_dir):
            if f == filename or f.endswith(filename):
                video_path = os.path.join(video_dir, f)
                found = True
                break
        
        if not found:
            logger.error(f"核心视频资源缺失: {filename}")
            raise HTTPException(status_code=404, detail="无法找到请求的视频流资源")

    # 返回流式响应，MediaType 指定为 MJPEG
    return StreamingResponse(
        generate_frames(video_path),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


# ==================== 系统服务状态评估 ====================

@router.get("/model/info", tags=["系统监控"])
async def get_model_info():
    """
    查询当前加载的模型元数据 (权重路径、类别字典等)
    """
    try:
        model = get_yolo_model()
        settings = get_settings()
        
        return {
            "status": "active",
            "model_engine": "YOLOv10 (NMS-free)",
            "weight_path": settings.yolo_model_path,
            "thresholds": {
                "confidence": settings.yolo_confidence_threshold,
                "iou": settings.yolo_iou_threshold
            },
            "class_map": model.names if hasattr(model, 'names') else "unknown",
            "timestamp": datetime.now()
        }
    except Exception as e:
        return {
            "status": "error",
            "error_msg": str(e),
            "timestamp": datetime.now()
        }


@router.get("/health", tags=["系统监控"])
async def health_check():
    """轻量级健康检查"""
    return {
        "status": "UP",
        "service": "Visual-Perception-Service",
        "timestamp": datetime.now()
    }
