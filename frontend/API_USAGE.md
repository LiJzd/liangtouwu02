# 生猪检测报告 API 使用说明

## 概述

本系统提供基于 AI Agent 的生猪生长轨迹预测和检测报告生成服务。

## 数据结构说明

### 猪只生命周期数据结构

每一条猪的数据是一个包含完整生命周期的 JSON 对象，具体字段包含：

```json
{
  "pig_id": "PIG001",
  "breed": "杜洛克",
  "lifecycle": [
    {
      "month": 1,
      "feed_count": 45,
      "feed_duration_mins": 280,
      "water_count": 80,
      "water_duration_mins": 160,
      "weight_kg": 28.5
    },
    {
      "month": 2,
      "feed_count": 50,
      "feed_duration_mins": 320,
      "water_count": 88,
      "water_duration_mins": 175,
      "weight_kg": 38.2
    },
    {
      "month": 3,
      "feed_count": 52,
      "feed_duration_mins": 340,
      "water_count": 92,
      "water_duration_mins": 185,
      "weight_kg": 45.0
    }
  ],
  "current_month": 3,
  "current_weight_kg": 45.0
}
```

**字段说明**：
- `pig_id`: 猪的唯一标识
- `breed`: 猪的品种（如：杜洛克、两头乌、长白、大白）
- `lifecycle`: 一个数组，按月记录生长数据，每个月的节点包含：
  - `month`: 第几个月（如 1, 2, 3...）
  - `feed_count`: 该月进食次数
  - `feed_duration_mins`: 该月进食总时长（分钟）
  - `water_count`: 该月喝水次数
  - `water_duration_mins`: 该月喝水总时长（分钟）
  - `weight_kg`: 该月体重（公斤）
- `current_month`: 当前月份（根据 lifecycle 数组长度计算）
- `current_weight_kg`: 当前体重（从最后一个月提取）

## 工作流程

```
前端请求（携带猪只ID）
    ↓
FastAPI 接口接收
    ↓
Agent 调用工具链
    ├─ 工具1: 从 MySQL 查询猪只完整生命周期信息
    │         返回：breed, lifecycle[], current_month
    └─ 工具2: RAG 检索相似历史案例
              输入：breed, current_month, lifecycle
              返回：future_trajectory（后续生长轨迹预测）
    ↓
生成 Markdown 检测报告
    ↓
返回给前端
```

## API 端点

### 1. 生成检测报告

**端点**: `POST /api/v1/inspection/generate`

**请求体**:
```json
{
  "pig_id": "PIG001"
}
```

**响应示例**:
```json
{
  "code": 200,
  "message": "报告生成成功",
  "pig_id": "PIG001",
  "report": "### 📊 猪只基本信息\n- **猪只 ID**: PIG001\n- **品种**: 杜洛克\n...",
  "timestamp": "2024-03-15T12:00:00"
}
```

**错误响应**:
```json
{
  "code": 500,
  "message": "报告生成失败",
  "detail": "未找到 ID 为 PIG999 的猪只信息",
  "pig_id": "PIG999",
  "timestamp": "2024-03-15T12:00:00"
}
```

### 2. 健康检查

**端点**: `GET /api/v1/inspection/health`

**响应**:
```json
{
  "status": "UP",
  "service": "生猪检测报告服务",
  "timestamp": "2024-03-15T12:00:00"
}
```

## 环境配置

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 MySQL 数据库

编辑 `.env` 文件：

```env
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=pig_farm
```

### 3. 初始化数据库

执行 `database_schema.sql` 创建表并插入示例数据：

```bash
mysql -u root -p pig_farm < database_schema.sql
```

### 4. 启动服务

```bash
python main.py
```

服务将在 `http://localhost:8000` 启动。

## API 文档

启动服务后，访问以下地址查看自动生成的 API 文档：

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 测试示例

### 使用 curl

```bash
curl -X POST "http://localhost:8000/api/v1/inspection/generate" \
  -H "Content-Type: application/json" \
  -d '{"pig_id": "PIG001"}'
```

### 使用 Python requests

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/inspection/generate",
    json={"pig_id": "PIG001"}
)

print(response.json())
```

### 使用 JavaScript fetch

```javascript
fetch('http://localhost:8000/api/v1/inspection/generate', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({ pig_id: 'PIG001' })
})
.then(response => response.json())
.then(data => console.log(data));
```

## Agent 工具说明

### 工具1: get_pig_info_by_id

- **功能**: 从 MySQL 数据库查询猪只完整生命周期信息
- **输入**: pig_id（猪只唯一标识）
- **输出**: JSON 格式的猪只信息
  - `pig_id`: 猪只ID
  - `breed`: 品种
  - `lifecycle`: 按月记录的生长数据数组
  - `current_month`: 当前月份
  - `current_weight_kg`: 当前体重

### 工具2: query_pig_growth_prediction

- **功能**: 从 RAG 向量库检索相似历史案例并预测生长轨迹
- **输入**: 
  - `breed`: 品种
  - `current_month`: 当前月份
  - `current_month_data`: 生命周期数据（支持单月dict或多月list）
  - `top_n`: 返回相似案例数量（默认3）
- **输出**: 相似历史猪只的后续生长轨迹数据
  - `future_trajectory`: 从 current_month+1 到出厂的完整轨迹
  - `similarity_distance`: 相似度距离（越小越相似）
  - `matched_slice_month`: 匹配的历史截面月份

## 报告格式

生成的检测报告为 Markdown 格式，包含以下部分：

1. **目标评估**: 品种、当前月份、当前体重、状态评述
2. **历史镜像匹配**: 匹配数量、最优匹配对象、相似度距离
3. **未来生长轨迹预测**: 
   - 近期生长预期（下个月体重）
   - 出厂节点预测（预计出厂月份和体重）
   - 未来轨迹一览表（逐月体重和状态）
4. **饲养干预建议**: 基于历史数据的核心建议

## 注意事项

1. 确保 MySQL 数据库已正确配置并包含猪只生命周期数据（JSON 格式）
2. 首次运行时会初始化 RAG 向量库（需要调用阿里百炼 API）
3. 需要配置有效的阿里百炼 API Key（在 `pig_rag/pig_lifecycle_rag.py` 和 `pig_rag/pig_agent.py` 中）
4. Agent 会自动按顺序调用工具，无需手动干预
5. 生命周期数据采用时间序列切片策略，确保时间对齐和无数据穿越

## 故障排查

### 问题1: 数据库连接失败

检查 `.env` 文件中的 MySQL 配置是否正确，确保数据库服务已启动。

### 问题2: 未找到猪只信息

确认数据库中存在对应的 pig_id 记录。

### 问题3: RAG 检索无结果

检查向量库是否已正确初始化，品种名称是否匹配，当前月份是否有对应的历史截面数据。

### 问题4: 生命周期数据格式错误

确保 MySQL 中的 lifecycle 字段为 JSON 类型，且包含必需的字段（month, feed_count, feed_duration_mins, water_count, water_duration_mins, weight_kg）。

### 问题4: API Key 错误

确认阿里百炼 API Key 是否有效且有足够的配额。
