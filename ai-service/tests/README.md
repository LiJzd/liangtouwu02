# 测试文件说明

## 概述

本文件夹包含所有测试相关的脚本和示例代码。

## 测试文件列表

### 1. 视觉感知测试

- **`test_perception.py`** - 完整的视觉感知 API 测试脚本
  - 测试所有 API 端点
  - 支持三种图像输入方式
  - 详细的错误处理和结果展示

- **`quick_test.py`** - 快速验证脚本
  - 快速检查服务是否正常运行
  - 验证模型加载状态
  - 使用公开测试图像进行推理

- **`example_usage.py`** - 使用示例
  - Python 客户端使用示例
  - 包含多种调用方式
  - 结果解析和展示

### 2. Agent 测试

- **`test_agent.py`** - Agent 功能测试
- **`test_api.py`** - API 接口测试
- **`test_direct.py`** - 直接调用测试
- **`test_dual_track.py`** - 双轨架构测试
- **`test_mysql.py`** - MySQL 数据库测试
- **`test_simple.py`** - 简单功能测试

## 使用方法

### 快速测试

```bash
# 确保服务已启动
python main.py

# 在另一个终端运行快速测试
python tests/quick_test.py
```

### 完整测试

```bash
# 运行所有视觉感知测试
python tests/test_perception.py

# 运行 Agent 测试
python tests/test_agent.py
```

### 使用示例

```bash
# 查看使用示例
python tests/example_usage.py
```

## 测试数据

### 公开测试图像

测试脚本使用以下公开图像进行测试：
- https://ultralytics.com/images/bus.jpg

### 本地测试图像

如需测试本地图像，请修改脚本中的图像路径：

```python
# 在 example_usage.py 中修改
image_path = "path/to/your/pig_image.jpg"
```

## 测试结果说明

### 成功响应

```json
{
  "code": 200,
  "message": "推理成功",
  "task_id": "TEST_001",
  "detections": [...],
  "detection_count": 3,
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
  "detail": "无法加载图像",
  "task_id": "TEST_001",
  "timestamp": "2024-03-15T12:00:00"
}
```

## 常见问题

### 1. 连接失败

```
错误: 无法连接到服务
```

**解决方案**:
- 确保服务已启动：`python main.py`
- 检查端口是否被占用
- 查看日志文件：`./logs/algorithm.log`

### 2. 模型加载失败

```
错误: 模型加载失败
```

**解决方案**:
- 检查模型文件：`./yolo模型/best.pt`
- 确认依赖已安装：`pip install -r requirements.txt`
- 查看详细错误信息

### 3. 推理超时

```
错误: 请求超时
```

**解决方案**:
- 增加超时时间
- 检查网络连接
- 减小图像分辨率

## 测试覆盖率

### API 端点测试

- [x] 健康检查
- [x] 模型信息
- [x] URL 图像检测
- [x] Base64 图像检测
- [x] 文件上传检测

### 错误场景测试

- [x] 无效 URL
- [x] 无效 Base64
- [x] 无效文件格式
- [x] 网络超时
- [x] 参数验证

## 性能测试

### 推理时间

- 首次加载：1-2 秒
- 后续推理：30-100ms
- GPU 加速：10-30ms

### 并发测试

- 支持多并发请求
- 异步处理机制
- 内存管理优化

## 扩展测试

如需添加新的测试：

1. 创建新的测试文件
2. 遵循现有命名规范
3. 包含完整的错误处理
4. 添加详细的日志输出

## 联系支持

如有测试相关问题，请查看：
- 日志文件：`./logs/algorithm.log`
- API 文档：`../docs/PERCEPTION_API.md`
- 使用指南：`../docs/YOLO_DETECTION_GUIDE.md`