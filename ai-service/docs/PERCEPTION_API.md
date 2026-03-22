# 视觉感知 API 使用文档

## 概述

视觉感知 API 基于 YOLOv8 模型，提供两头乌猪的状态识别功能。支持三种图像输入方式：URL、Base64 编码、文件上传。

## 基础信息

- **基础路径**: `/api/v1/perception`
- **模型**: YOLOv8 (自定义训练的两头乌猪检测模型)
- **模型路径**: `./yolo模型/best.pt`

## API 端点

### 1. 健康检查

检查服务是否正常运行。

```http
GET /api/v1/perception/health
```

**响应示例**:
```json
{
  "status": "UP",
  "service": "视觉感知服务（YOLO）",
  "timestamp": "2024-03-15T12:00:00"
}
```

---

### 2. 获取模型信息

获取当前加载的 YOLO 模型详细信息。

```http
GET /api/v1/perception/model/info
```

**响应示例**:
```json
{
  "status": "loaded",
  "model_path": "./yolo模型/best.pt",
  "model_type": "YOLOv8",
  "confidence_threshold": 0.5,
  "iou_threshold": 0.45,
  "classes": {
    "0": "pig",
    "1": "pig_lying",
    "2": "pig_standing",
    "3": "pig_eating"
  },
  "timestamp": "2024-03-15T12:00:00"
}
```

---

### 3. 基于 URL 的图像检测

通过图像 URL 进行目标检测。

```http
POST /api/v1/perception/detect
Content-Type: application/json
```

**请求体**:
```json
{
  "image_url": "https://example.com/pig_image.jpg",
  "task_id": "TASK_20240315_001",
  "model_type": "yolov8n",
  "confidence_threshold": 0.5
}
```

**参数说明**:
- `image_url` (必填): 图像的 HTTP/HTTPS URL
- `task_id` (必填): 任务唯一标识，用于追踪
- `model_type` (可选): 模型类型，默认 "yolov8n"
- `confidence_threshold` (可选): 置信度阈值 (0.0-1.0)，默认 0.5

**响应示例**:
```json
{
  "code": 200,
  "message": "推理成功",
  "task_id": "TASK_20240315_001",
  "detections": [
    {
      "class_id": 0,
      "class_name": "pig",
      "confidence": 0.92,
      "bbox_x1": 0.25,
      "bbox_y1": 0.30,
      "bbox_x2": 0.65,
      "bbox_y2": 0.80
    },
    {
      "class_id": 2,
      "class_name": "pig_standing",
      "confidence": 0.87,
      "bbox_x1": 0.70,
      "bbox_y1": 0.35,
      "bbox_x2": 0.95,
      "bbox_y2": 0.85
    }
  ],
  "detection_count": 2,
  "inference_time_ms": 45.6,
  "model_version": "yolov8n",
  "timestamp": "2024-03-15T12:00:00"
}
```

---

### 4. 基于 Base64 的图像检测

通过 Base64 编码的图像进行目标检测。

```http
POST /api/v1/perception/detect/base64
Content-Type: application/json
```

**请求体**:
```json
{
  "image_base64": "/9j/4AAQSkZJRgABAQAAAQABAAD...",
  "task_id": "TASK_20240315_002",
  "confidence_threshold": 0.6
}
```

**参数说明**:
- `image_base64` (必填): Base64 编码的图像数据
- `task_id` (必填): 任务唯一标识
- `confidence_threshold` (可选): 置信度阈值 (0.0-1.0)

**响应格式**: 与 URL 检测相同

---

### 5. 基于文件上传的图像检测

通过上传图像文件进行目标检测。

```http
POST /api/v1/perception/detect/upload
Content-Type: multipart/form-data
```

**表单参数**:
- `file` (必填): 图像文件 (支持 JPG, PNG 等格式)
- `task_id` (必填): 任务唯一标识
- `confidence_threshold` (可选): 置信度阈值 (0.0-1.0)

**cURL 示例**:
```bash
curl -X POST "http://localhost:8000/api/v1/perception/detect/upload" \
  -F "file=@/path/to/pig_image.jpg" \
  -F "task_id=TASK_20240315_003" \
  -F "confidence_threshold=0.5"
```

**响应格式**: 与 URL 检测相同

---

## 检测结果说明

### DetectionObject 字段

每个检测目标包含以下字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `class_id` | int | 类别 ID |
| `class_name` | string | 类别名称（中文） |
| `confidence` | float | 置信度分数 (0.0-1.0) |
| `bbox_x1` | float | 边界框左上角 X 坐标（归一化 0-1） |
| `bbox_y1` | float | 边界框左上角 Y 坐标（归一化 0-1） |
| `bbox_x2` | float | 边界框右下角 X 坐标（归一化 0-1） |
| `bbox_y2` | float | 边界框右下角 Y 坐标（归一化 0-1） |

### 坐标转换

归一化坐标转换为像素坐标：

```python
# 假设原图尺寸为 width x height
pixel_x1 = bbox_x1 * width
pixel_y1 = bbox_y1 * height
pixel_x2 = bbox_x2 * width
pixel_y2 = bbox_y2 * height
```

---

## 错误处理

### 错误响应格式

```json
{
  "code": 400,
  "message": "请求参数校验失败",
  "detail": "无法加载图像: Connection timeout",
  "task_id": "TASK_20240315_001",
  "timestamp": "2024-03-15T12:00:00"
}
```

### 常见错误码

| 状态码 | 说明 |
|--------|------|
| 400 | 请求参数错误（图像加载失败、格式错误等） |
| 500 | 服务器内部错误（模型加载失败、推理失败等） |

---

## Python 客户端示例

### 1. URL 检测

```python
import requests

url = "http://localhost:8000/api/v1/perception/detect"
payload = {
    "image_url": "https://example.com/pig.jpg",
    "task_id": "TASK_001",
    "confidence_threshold": 0.5
}

response = requests.post(url, json=payload)
result = response.json()

print(f"检测到 {result['detection_count']} 个目标")
for det in result['detections']:
    print(f"- {det['class_name']}: {det['confidence']:.2f}")
```

### 2. Base64 检测

```python
import requests
import base64

# 读取图像并编码
with open("pig_image.jpg", "rb") as f:
    image_base64 = base64.b64encode(f.read()).decode('utf-8')

url = "http://localhost:8000/api/v1/perception/detect/base64"
payload = {
    "image_base64": image_base64,
    "task_id": "TASK_002",
    "confidence_threshold": 0.5
}

response = requests.post(url, json=payload)
result = response.json()
```

### 3. 文件上传检测

```python
import requests

url = "http://localhost:8000/api/v1/perception/detect/upload"

with open("pig_image.jpg", "rb") as f:
    files = {"file": ("pig_image.jpg", f, "image/jpeg")}
    data = {
        "task_id": "TASK_003",
        "confidence_threshold": 0.5
    }
    response = requests.post(url, files=files, data=data)

result = response.json()
```

---

## JavaScript 客户端示例

### 1. URL 检测

```javascript
const response = await fetch('http://localhost:8000/api/v1/perception/detect', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    image_url: 'https://example.com/pig.jpg',
    task_id: 'TASK_001',
    confidence_threshold: 0.5
  })
});

const result = await response.json();
console.log(`检测到 ${result.detection_count} 个目标`);
```

### 2. 文件上传检测

```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);
formData.append('task_id', 'TASK_002');
formData.append('confidence_threshold', '0.5');

const response = await fetch('http://localhost:8000/api/v1/perception/detect/upload', {
  method: 'POST',
  body: formData
});

const result = await response.json();
```

---

## 性能优化建议

1. **模型预加载**: 首次调用会加载模型到内存（约 1-2 秒），后续调用直接使用缓存模型
2. **批量处理**: 如需处理多张图像，建议使用异步并发请求
3. **图像尺寸**: 建议图像分辨率在 640x640 到 1280x1280 之间，过大会影响推理速度
4. **置信度阈值**: 根据实际需求调整，较高阈值（0.6-0.8）可减少误检

---

## 测试

运行测试脚本：

```bash
# 确保服务已启动
python main.py

# 在另一个终端运行测试
python test_perception.py
```

---

## 常见问题

### Q: 模型加载失败怎么办？

A: 检查以下几点：
1. 确认模型文件存在：`./yolo模型/best.pt`
2. 确认已安装 ultralytics：`pip install ultralytics`
3. 查看日志文件：`./logs/algorithm.log`

### Q: 推理速度慢怎么办？

A: 
1. 使用 GPU 加速（需安装 CUDA 版本的 PyTorch）
2. 减小图像分辨率
3. 使用更小的模型（如 yolov8n）

### Q: 检测不到目标怎么办？

A:
1. 降低置信度阈值（如 0.3）
2. 确认图像质量良好
3. 确认模型已针对两头乌猪训练

---

## 更新日志

- **v1.0.0** (2024-03-15): 初始版本，支持三种图像输入方式

---

## 联系方式

如有问题，请查看日志文件或联系开发团队。
