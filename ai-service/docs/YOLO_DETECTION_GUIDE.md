# YOLO 两头乌猪状态识别使用指南

## 快速开始

### 1. 确保依赖已安装

```bash
cd 两头乌ai端
pip install -r requirements.txt
```

### 2. 检查模型文件

确认 YOLO 模型文件存在：
```
两头乌ai端/yolo模型/best.pt
```

### 3. 启动服务

```bash
python main.py
```

服务将在 `http://localhost:8000` 启动。

### 4. 访问 API 文档

打开浏览器访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 5. 运行测试

```bash
# 基础测试
python test_perception.py

# 使用示例
python example_usage.py
```

---

## 功能说明

### 支持的输入方式

1. **图像 URL**: 通过 HTTP/HTTPS URL 加载图像
2. **Base64 编码**: 直接传输 Base64 编码的图像数据
3. **文件上传**: 通过 multipart/form-data 上传图像文件

### 检测结果

每个检测目标包含：
- 类别 ID 和名称
- 置信度分数
- 边界框坐标（归一化到 0-1）

### 性能特点

- 首次调用会加载模型（约 1-2 秒）
- 后续调用使用缓存模型（推理时间 30-100ms）
- 支持 GPU 加速（需安装 CUDA 版本的 PyTorch）

---

## API 端点

### 1. 健康检查
```
GET /api/v1/perception/health
```

### 2. 模型信息
```
GET /api/v1/perception/model/info
```

### 3. URL 检测
```
POST /api/v1/perception/detect
Content-Type: application/json

{
  "image_url": "https://example.com/pig.jpg",
  "task_id": "TASK_001",
  "confidence_threshold": 0.5
}
```

### 4. Base64 检测
```
POST /api/v1/perception/detect/base64
Content-Type: application/json

{
  "image_base64": "base64_encoded_image_data",
  "task_id": "TASK_002",
  "confidence_threshold": 0.5
}
```

### 5. 文件上传检测
```
POST /api/v1/perception/detect/upload
Content-Type: multipart/form-data

file: [image file]
task_id: TASK_003
confidence_threshold: 0.5
```

---

## Python 客户端使用

### 基础用法

```python
from example_usage import PerceptionClient

# 创建客户端
client = PerceptionClient(base_url="http://localhost:8000")

# 检查服务状态
health = client.health_check()
print(health)

# 获取模型信息
model_info = client.get_model_info()
print(model_info)

# URL 检测
result = client.detect_from_url(
    image_url="https://example.com/pig.jpg",
    task_id="TASK_001",
    confidence_threshold=0.5
)

# 打印结果
client.print_detection_result(result)
```

### 文件检测

```python
# 方式 1: 文件上传
result = client.detect_from_file(
    image_path="path/to/pig.jpg",
    task_id="TASK_002",
    use_base64=False
)

# 方式 2: Base64 编码
result = client.detect_from_file(
    image_path="path/to/pig.jpg",
    task_id="TASK_003",
    use_base64=True
)
```

---

## JavaScript/TypeScript 使用

### 前端调用示例

```typescript
// URL 检测
async function detectFromUrl(imageUrl: string) {
  const response = await fetch('http://localhost:8000/api/v1/perception/detect', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      image_url: imageUrl,
      task_id: `TASK_${Date.now()}`,
      confidence_threshold: 0.5
    })
  });
  
  const result = await response.json();
  return result;
}

// 文件上传检测
async function detectFromFile(file: File) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('task_id', `TASK_${Date.now()}`);
  formData.append('confidence_threshold', '0.5');
  
  const response = await fetch('http://localhost:8000/api/v1/perception/detect/upload', {
    method: 'POST',
    body: formData
  });
  
  const result = await response.json();
  return result;
}

// 使用示例
const result = await detectFromUrl('https://example.com/pig.jpg');
console.log(`检测到 ${result.detection_count} 个目标`);

result.detections.forEach((det, i) => {
  console.log(`${i + 1}. ${det.class_name} (${(det.confidence * 100).toFixed(1)}%)`);
});
```

---

## 响应格式

### 成功响应

```json
{
  "code": 200,
  "message": "推理成功",
  "task_id": "TASK_001",
  "detections": [
    {
      "class_id": 0,
      "class_name": "pig",
      "confidence": 0.92,
      "bbox_x1": 0.25,
      "bbox_y1": 0.30,
      "bbox_x2": 0.65,
      "bbox_y2": 0.80
    }
  ],
  "detection_count": 1,
  "inference_time_ms": 45.6,
  "model_version": "yolov8",
  "timestamp": "2024-03-15T12:00:00"
}
```

### 错误响应

```json
{
  "code": 400,
  "message": "请求参数错误",
  "detail": "无法加载图像: Connection timeout",
  "task_id": "TASK_001",
  "timestamp": "2024-03-15T12:00:00"
}
```

---

## 坐标系统

### 归一化坐标

API 返回的边界框坐标是归一化的（0-1 范围）：

```
bbox_x1, bbox_y1: 左上角坐标
bbox_x2, bbox_y2: 右下角坐标
```

### 转换为像素坐标

```python
# 假设原图尺寸为 1920x1080
width, height = 1920, 1080

# 转换坐标
pixel_x1 = int(bbox_x1 * width)
pixel_y1 = int(bbox_y1 * height)
pixel_x2 = int(bbox_x2 * width)
pixel_y2 = int(bbox_y2 * height)

# 计算中心点
center_x = (pixel_x1 + pixel_x2) // 2
center_y = (pixel_y1 + pixel_y2) // 2

# 计算宽高
box_width = pixel_x2 - pixel_x1
box_height = pixel_y2 - pixel_y1
```

---

## 配置说明

### 环境变量配置

在 `.env` 文件中配置：

```env
# YOLO 模型配置
YOLO_MODEL_PATH=./yolo模型/best.pt
YOLO_CONFIDENCE_THRESHOLD=0.5
YOLO_IOU_THRESHOLD=0.45
```

### 代码配置

在 `v1/common/config.py` 中修改：

```python
class Settings(BaseSettings):
    yolo_model_path: str = "./yolo模型/best.pt"
    yolo_confidence_threshold: float = 0.5
    yolo_iou_threshold: float = 0.45
```

---

## 性能优化

### 1. GPU 加速

安装 CUDA 版本的 PyTorch：

```bash
# CUDA 11.8
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# CUDA 12.1
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```

### 2. 批量处理

使用异步并发处理多张图像：

```python
import asyncio
import aiohttp

async def batch_detect(image_urls):
    async with aiohttp.ClientSession() as session:
        tasks = []
        for i, url in enumerate(image_urls):
            task = detect_async(session, url, f"TASK_{i}")
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        return results

async def detect_async(session, image_url, task_id):
    async with session.post(
        'http://localhost:8000/api/v1/perception/detect',
        json={
            'image_url': image_url,
            'task_id': task_id,
            'confidence_threshold': 0.5
        }
    ) as response:
        return await response.json()
```

### 3. 图像预处理

- 推荐分辨率: 640x640 到 1280x1280
- 支持格式: JPG, PNG, BMP
- 压缩质量: 80-95%

---

## 故障排查

### 问题 1: 模型加载失败

**症状**: 
```
错误: 模型加载失败: [Errno 2] No such file or directory: './yolo模型/best.pt'
```

**解决方案**:
1. 检查模型文件是否存在
2. 检查路径配置是否正确
3. 查看日志: `./logs/algorithm.log`

### 问题 2: 推理速度慢

**症状**: 推理时间超过 500ms

**解决方案**:
1. 使用 GPU 加速
2. 减小图像分辨率
3. 使用更小的模型（yolov8n）

### 问题 3: 检测不到目标

**症状**: `detection_count` 为 0

**解决方案**:
1. 降低置信度阈值（如 0.3）
2. 检查图像质量
3. 确认模型已正确训练

### 问题 4: 内存不足

**症状**: 
```
RuntimeError: CUDA out of memory
```

**解决方案**:
1. 减小批处理大小
2. 减小图像分辨率
3. 使用 CPU 模式

---

## 日志查看

### 应用日志

```bash
tail -f ./logs/algorithm.log
```

### 错误日志

```bash
tail -f ./logs/stderr.log
```

---

## 集成到现有系统

### 与 Spring Boot 后端集成

在 Spring Boot 中调用 AI 服务：

```java
@Service
public class PerceptionService {
    
    @Value("${ai.service.url}")
    private String aiServiceUrl;
    
    private final RestTemplate restTemplate;
    
    public PerceptionResponse detectPig(String imageUrl, String taskId) {
        String url = aiServiceUrl + "/api/v1/perception/detect";
        
        PerceptionRequest request = new PerceptionRequest();
        request.setImageUrl(imageUrl);
        request.setTaskId(taskId);
        request.setConfidenceThreshold(0.5);
        
        return restTemplate.postForObject(url, request, PerceptionResponse.class);
    }
}
```

### 与前端集成

在 Vue/React 中调用：

```typescript
// api.ts
export async function detectPig(imageUrl: string) {
  const response = await fetch('/api/v1/perception/detect', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      image_url: imageUrl,
      task_id: `TASK_${Date.now()}`,
      confidence_threshold: 0.5
    })
  });
  
  return response.json();
}
```

---

## 更多信息

- 详细 API 文档: [PERCEPTION_API.md](PERCEPTION_API.md)
- 项目说明: [README.md](README.md)
- 测试脚本: [test_perception.py](test_perception.py)
- 使用示例: [example_usage.py](example_usage.py)

---

## 联系支持

如有问题，请查看日志文件或联系开发团队。
