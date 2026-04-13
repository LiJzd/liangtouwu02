# 两头乌 AI 服务

基于 FastAPI 的智能猪场管理 AI 服务，集成 ReAct 智能体、YOLO 视觉识别和 RAG 知识库。

## 快速启动

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务
python main.py
```

服务地址: http://localhost:8000

API 文档: http://localhost:8000/docs

## 主要功能

### 1. ReAct 智能体
- 中文对话理解
- 工具调用能力
- 思考过程可视化

### 2. YOLO 视觉识别
- 猪只检测
- 视频帧分析
- 实时监控

### 3. RAG 知识库
- 猪只档案查询
- 生长曲线预测
- 历史数据分析

### 4. QQ Bot 集成
- 自动回复
- 定时推送
- 工具调用

## 目录结构

```
ai-service/
├── v1/                    # API v1
│   ├── logic/            # 业务逻辑
│   ├── objects/          # 数据模型
│   └── common/           # 公共配置
├── pig_rag/              # RAG 系统
│   ├── math_engine/      # 数学引擎
│   └── mysql_tool.py     # 数据库工具
├── docs/                 # 文档
├── tests/                # 测试
├── mock_data/            # 模拟数据
├── models/               # YOLO 模型
├── .env                  # 环境配置
├── main.py               # 入口文件
└── bot_runner.py         # QQ Bot 启动器
```

## 环境配置

编辑 `.env` 文件：

```env
# 服务配置
PORT=8000
DEBUG=true

# YOLO 模型
YOLO_MODEL_PATH=../resources/assets/yolov10m_train_312/weights/best.pt

# 数据库
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=liangtowwu

# LLM API
DASHSCOPE_API_KEY=your_api_key
DASHSCOPE_MODEL=qwen3.5-plus

# QQ Bot
BOT_APP_ID=your_app_id
BOT_APP_SECRET=your_app_secret
```

## API 端点

- `POST /api/v1/agent/chat` - 智能对话
- `POST /api/v1/perception/detect` - YOLO 检测
- `GET /api/v1/perception/snapshot` - 视频截图
- `GET /health` - 健康检查

## 开发

### 运行测试

```bash
python -m pytest tests/
```

### 启动 QQ Bot

```bash
python bot_runner.py
```

## 文档

- [ReAct 模式说明](docs/REACT_MODE.md)
- [ReAct 快速开始](docs/REACT_QUICKSTART.md)
- [Bot 工作流程](docs/BOT_WORKFLOW.md)
- [视频截图工具](docs/SNAPSHOT_TOOL_GUIDE.md)
- [YOLO 检测指南](docs/YOLO_DETECTION_GUIDE.md)
