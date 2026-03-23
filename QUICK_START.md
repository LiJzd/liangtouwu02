# 掌上明猪 AI 服务 - 快速启动指南

## 前置条件

- Python 3.10+
- Java 17+
- MySQL 8.0+
- Maven 3.6+

## 一、数据库准备

### 1. 执行迁移脚本

```bash
cd backend/migrations

# 方式 1: 使用脚本（推荐）
chmod +x run_migration.sh
./run_migration.sh 001_add_user_id_to_pig.sql

# 方式 2: 手动执行
mysql -u root -p liangtouwu < 001_add_user_id_to_pig.sql
```

### 2. 验证迁移

```sql
-- 检查字段是否添加成功
DESCRIBE pig;

-- 检查索引是否创建
SHOW INDEX FROM pig;

-- 检查数据分布
SELECT user_id, COUNT(*) FROM pig GROUP BY user_id;
```

## 二、Java 后端启动

### 1. 编译项目

```bash
cd backend
mvn clean package -DskipTests
```

### 2. 启动服务

```bash
java -jar liangtouwu-app/target/liangtouwu-app-1.0.0.jar
```

### 3. 验证服务

```bash
# 健康检查
curl http://localhost:8080/actuator/health

# 测试 AI Tool API
bash test_ai_tool_api.sh
```

### 4. 查看 API 文档

浏览器访问：http://localhost:8080/swagger-ui.html

## 三、Python AI 服务启动

### 1. 安装依赖

```bash
cd ai-service
pip install -r requirements.txt
```

### 2. 配置环境变量

创建 `.env` 文件：

```bash
# 阿里百炼 API Key
DASHSCOPE_API_KEY=sk-your-api-key-here

# Java 后端 API 地址
JAVA_API_BASE_URL=http://localhost:8080

# 数据库配置（如需直连）
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your-password
MYSQL_DATABASE=liangtouwu
```

### 3. 启动服务

```bash
python main.py
```

服务将在 http://localhost:8000 启动

### 4. 验证服务

```bash
# 健康检查
curl http://localhost:8000/health

# 测试多智能体接口
cd tests
python test_multi_agent.py

# 测试 Java API 集成
python test_java_api_integration.py
```

## 四、功能测试

### 1. 访问调试页面

浏览器打开：http://localhost:8000/static/debug.html

### 2. 测试对话接口

```bash
curl -X POST "http://localhost:8000/api/v1/agent/chat/v2" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "demo_user_001",
    "messages": [
      {"role": "user", "content": "我的猪场有哪些猪？"}
    ]
  }'
```

### 3. 运行测试套件

```bash
cd ai-service/tests

# 端到端测试
python test_e2e_validation.py

# 安全测试
python test_security_validation.py
```

## 五、常见问题

### Q1: Java 服务启动失败

**可能原因**：
- 端口 8080 被占用
- 数据库连接失败
- 配置文件错误

**解决方法**：
```bash
# 检查端口占用
netstat -ano | findstr :8080  # Windows
lsof -i :8080                 # Linux/Mac

# 检查数据库连接
mysql -u root -p -e "SELECT 1"

# 查看日志
tail -f logs/application.log
```

### Q2: Python 服务调用 Java API 超时

**可能原因**：
- Java 服务未启动
- 网络不通
- 环境变量配置错误

**解决方法**：
```bash
# 检查 Java 服务
curl http://localhost:8080/actuator/health

# 检查环境变量
echo $JAVA_API_BASE_URL

# 测试网络连通性
ping localhost
```

### Q3: 数据库迁移失败

**可能原因**：
- 字段已存在
- 权限不足
- 语法错误

**解决方法**：
```bash
# 检查字段是否已存在
mysql -u root -p -e "DESCRIBE liangtouwu.pig"

# 使用回滚脚本
mysql -u root -p liangtouwu < migrations/001_rollback.sql

# 重新执行迁移
mysql -u root -p liangtouwu < migrations/001_add_user_id_to_pig.sql
```

### Q4: 多智能体路由不准确

**可能原因**：
- LLM API Key 无效
- 网络延迟
- System Prompt 需要优化

**解决方法**：
```bash
# 检查 API Key
echo $DASHSCOPE_API_KEY

# 查看路由日志
tail -f logs/algorithm.log

# 运行路由测试
python tests/test_e2e_validation.py
```

## 六、生产环境部署

### 1. 环境变量配置

```bash
# Python AI 服务
export DASHSCOPE_API_KEY=sk-prod-key
export JAVA_API_BASE_URL=http://backend-service:8080
export LOG_LEVEL=INFO

# Java 后端服务
export SPRING_PROFILES_ACTIVE=prod
export MYSQL_HOST=prod-db-host
export MYSQL_PASSWORD=prod-password
```

### 2. 使用 systemd 管理服务（Linux）

创建 `/etc/systemd/system/liangtouwu-ai.service`：

```ini
[Unit]
Description=Liangtouwu AI Service
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/liangtouwu/ai-service
Environment="DASHSCOPE_API_KEY=sk-xxx"
Environment="JAVA_API_BASE_URL=http://localhost:8080"
ExecStart=/usr/bin/python3 main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable liangtouwu-ai
sudo systemctl start liangtouwu-ai
sudo systemctl status liangtouwu-ai
```

### 3. 使用 Nginx 反向代理

```nginx
upstream ai_backend {
    server 127.0.0.1:8000;
}

upstream java_backend {
    server 127.0.0.1:8080;
}

server {
    listen 80;
    server_name your-domain.com;

    location /api/v1/agent/ {
        proxy_pass http://ai_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api/ {
        proxy_pass http://java_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 七、监控与日志

### 1. 日志位置

- Python AI: `ai-service/logs/algorithm.log`
- Java 后端: `backend/logs/application.log`

### 2. 查看实时日志

```bash
# Python AI
tail -f ai-service/logs/algorithm.log

# Java 后端
tail -f backend/logs/application.log
```

### 3. 性能监控

```bash
# 查看进程资源占用
ps aux | grep python
ps aux | grep java

# 查看内存占用
free -h

# 查看数据库连接数
mysql -u root -p -e "SHOW PROCESSLIST"
```

## 八、下一步

- [ ] 阅读 [多智能体架构指南](ai-service/docs/MULTI_AGENT_GUIDE.md)
- [ ] 阅读 [Agent 调试指南](ai-service/docs/AGENT_DEBUG_GUIDE.md)
- [ ] 查看 [API 文档](backend/API_DOCS.md)
- [ ] 运行完整测试套件
- [ ] 配置生产环境监控

## 技术支持

如遇问题，请查看：
- [重构总结](ai-service/REFACTOR_SUMMARY.md)
- [部署指南](backend/AI_TOOL_API_DEPLOYMENT.md)
- [故障排查指南](docs/TROUBLESHOOTING.md)（待创建）
