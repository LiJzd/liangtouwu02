# 掌上明猪 - 智慧农业生猪监测系统

## 项目简介

基于多智能体架构的生猪养殖智能监测系统，提供：
- 🤖 多智能体对话（兽医诊断、数据查询、视觉识别）
- 📊 实时监控与数据分析
- 🔒 租户隔离与安全防护
- 🎯 精准的健康预警

## 技术栈

### 前端
- Vue 3 + TypeScript
- Element Plus
- ECharts

### 后端
- **Java**: Spring Boot + MyBatis-Plus
- **Python AI**: FastAPI + LangChain + 阿里百炼
- **数据库**: MySQL 8.0
- **向量数据库**: ChromaDB

## 快速开始

### 前置条件
- Java 17+
- Maven 3.6+
- MySQL 8.0+
- Node.js 16+（前端）
- Python 3.10+（AI 服务，可选）

### 一键启动（推荐）

#### Windows
```bash
# 启动 Java 后端
cd backend
start.bat

# 启动前端（新终端）
cd frontend
npm install
npm run dev
```

#### Linux/Mac
```bash
# 启动 Java 后端
cd backend
chmod +x start.sh
./start.sh

# 启动前端（新终端）
cd frontend
npm install
npm run dev
```

### 手动启动

#### 1. 数据库准备
```bash
cd backend/migrations
chmod +x run_migration.sh
./run_migration.sh 001_add_user_id_to_pig.sql
```

### 2. 启动 Java 后端
```bash
cd backend
mvn clean package -DskipTests
java -jar liangtouwu-app/target/liangtouwu-app-1.0.0.jar
```

### 3. 启动 Python AI 服务
```bash
cd ai-service
pip install -r requirements.txt
cp .env.example .env  # 配置 DASHSCOPE_API_KEY
python main.py
```

### 4. 启动前端（可选）
```bash
cd frontend
npm install
npm run dev
```

## 服务端口

- 前端: http://localhost:5173
- Java 后端: http://localhost:8080
- Python AI: http://localhost:8000
- 调试页面: http://localhost:8000/static/debug.html

## 核心功能

### 多智能体对话
```bash
curl -X POST "http://localhost:8000/api/v1/agent/chat/v2" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "demo_user_001",
    "messages": [{"role": "user", "content": "我的猪场有哪些猪？"}]
  }'
```

### AI Tool API
```bash
curl -X POST "http://localhost:8080/api/v1/ai-tool/pigs/list" \
  -H "X-User-ID: demo_user_001" \
  -H "Content-Type: application/json" \
  -d '{"limit": 10, "abnormalOnly": false}'
```

## 项目结构

```
.
├── frontend/              # Vue 3 前端
├── backend/               # Spring Boot 后端
│   ├── liangtouwu-app/   # 应用启动模块
│   ├── liangtouwu-business/  # 业务逻辑层
│   ├── liangtouwu-domain/    # 领域模型层
│   ├── liangtouwu-common/    # 通用工具层
│   └── migrations/       # 数据库迁移脚本
├── ai-service/           # Python AI 服务
│   ├── v1/logic/         # 多智能体核心
│   ├── pig_rag/          # RAG 系统
│   ├── docs/             # 架构文档
│   ├── static/           # 调试页面
│   └── tests/            # 测试套件
├── QUICK_START.md        # 快速启动指南
├── DEPLOYMENT_CHECKLIST.md  # 部署清单
└── README.md             # 本文件
```

## 文档

- [快速启动指南](QUICK_START.md) - 详细的部署步骤
- [部署验证清单](DEPLOYMENT_CHECKLIST.md) - 部署前后检查
- [测试结果报告](ai-service/tests/TEST_RESULTS.md) - 功能和安全测试
- [重构总结](ai-service/REFACTOR_SUMMARY.md) - 架构设计说明
- [多智能体指南](ai-service/docs/MULTI_AGENT_GUIDE.md) - Agent 架构详解
- [调试指南](ai-service/docs/AGENT_DEBUG_GUIDE.md) - 调试工具使用
- [API 文档](backend/API_DOCS.md) - 接口说明

## 安全特性

- ✅ 租户隔离（强制 `X-User-ID` Header 校验）
- ✅ SQL 注入防护（参数化查询）
- ✅ 提示词注入防护（System Prompt 隔离）
- ✅ 输出过滤（思考链路不污染用户回复）

## 测试

```bash
# 运行多智能体测试
cd ai-service/tests
python test_multi_agent.py

# 查看测试报告
cat TEST_RESULTS.md
```

## 监控与调试

- **Rich 控制台**: 彩色格式化的 Agent 推理过程
- **SSE 调试流**: 实时查看 Agent 内部状态
- **调试页面**: http://localhost:8000/static/debug.html

## 常见问题

### Q: Java 服务启动失败
检查端口占用和数据库连接：
```bash
netstat -ano | findstr :8080
mysql -u root -p -e "SELECT 1"
```

### Q: Python 调用 Java API 超时
确保 Java 服务已启动：
```bash
curl http://localhost:8080/actuator/health
```

### Q: 多智能体路由不准确
检查 API Key 和日志：
```bash
echo $DASHSCOPE_API_KEY
tail -f ai-service/logs/algorithm.log
```

更多问题请查看 [快速启动指南](QUICK_START.md)

## 贡献

欢迎提交 Issue 和 Pull Request

## 许可证

MIT License
