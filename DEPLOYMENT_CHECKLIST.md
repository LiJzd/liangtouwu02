# 部署验证清单

## 部署前检查

### 数据库
- [ ] MySQL 8.0+ 已安装
- [ ] 数据库 `liangtouwu` 已创建
- [ ] 执行迁移脚本 `001_add_user_id_to_pig.sql`
- [ ] 验证 `pig` 表有 `user_id` 字段
- [ ] 验证索引已创建

### Java 后端
- [ ] Java 17+ 已安装
- [ ] Maven 3.6+ 已安装
- [ ] 项目编译成功 `mvn clean package`
- [ ] 配置文件正确 `application.yml`
- [ ] 端口 8080 未被占用

### Python AI 服务
- [ ] Python 3.10+ 已安装
- [ ] 依赖已安装 `pip install -r requirements.txt`
- [ ] `.env` 文件已配置
- [ ] `DASHSCOPE_API_KEY` 已设置
- [ ] `JAVA_API_BASE_URL` 已设置
- [ ] 端口 8000 未被占用

## 部署步骤

### 1. 数据库迁移
```bash
cd backend/migrations
chmod +x run_migration.sh
./run_migration.sh 001_add_user_id_to_pig.sql
```

### 2. 启动 Java 后端
```bash
cd backend
java -jar liangtouwu-app/target/liangtouwu-app-1.0.0.jar
```

### 3. 启动 Python AI 服务
```bash
cd ai-service
python main.py
```

## 部署后验证

### Java 后端验证
```bash
# 健康检查
curl http://localhost:8080/actuator/health

# 测试 AI Tool API
curl -X POST "http://localhost:8080/api/v1/ai-tool/pigs/list" \
  -H "X-User-ID: demo_user_001" \
  -H "Content-Type: application/json" \
  -d '{"limit": 10, "abnormalOnly": false}'

# 预期: 返回 200 和猪只列表
```

### Python AI 服务验证
```bash
# 健康检查
curl http://localhost:8000/health

# 测试多智能体接口
curl -X POST "http://localhost:8000/api/v1/agent/chat/v2" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "demo_user_001",
    "messages": [{"role": "user", "content": "我的猪场有哪些猪？"}]
  }'

# 预期: 返回 200 和 AI 回复
```

### 安全验证
```bash
# 测试缺少 Header（应返回 401）
curl -X POST "http://localhost:8080/api/v1/ai-tool/pigs/list" \
  -H "Content-Type: application/json" \
  -d '{"limit": 10}'

# 预期: 返回 401 Unauthorized
```

### 功能验证
- [ ] 访问调试页面 http://localhost:8000/static/debug.html
- [ ] 测试数据查询问题（如"列出猪只"）
- [ ] 测试诊断问题（如"PIG001 怎么了"）
- [ ] 测试视觉识别问题（如"截图看看"）
- [ ] 验证输出无思考链污染
- [ ] 验证 Supervisor 路由正确

## 监控检查

### 日志检查
```bash
# Python AI 日志
tail -f ai-service/logs/algorithm.log

# Java 后端日志
tail -f backend/logs/application.log
```

### 资源监控
```bash
# 查看进程
ps aux | grep python
ps aux | grep java

# 查看内存
free -h

# 查看数据库连接
mysql -u root -p -e "SHOW PROCESSLIST"
```

## 回滚方案

如遇严重问题，执行回滚：

### 1. 停止服务
```bash
# 停止 Python AI
pkill -f "python main.py"

# 停止 Java 后端
pkill -f "liangtouwu-app"
```

### 2. 回滚数据库
```bash
cd backend/migrations
mysql -u root -p liangtouwu < 001_rollback.sql
```

### 3. 恢复旧版本代码
```bash
git checkout <previous_commit>
```

## 部署完成确认

- [ ] 所有服务正常启动
- [ ] 健康检查通过
- [ ] API 调用正常
- [ ] 安全机制生效
- [ ] 日志无错误
- [ ] 资源占用正常
- [ ] 监控告警配置完成

## 生产环境额外检查

- [ ] 配置 HTTPS
- [ ] 配置 Nginx 反向代理
- [ ] 配置防火墙规则
- [ ] 配置日志轮转
- [ ] 配置自动重启（systemd）
- [ ] 配置监控告警
- [ ] 配置备份策略
- [ ] 配置灾难恢复计划

## 联系方式

如遇问题，请查看：
- 快速启动指南: `QUICK_START.md`
- 测试结果: `ai-service/tests/TEST_RESULTS.md`
- 重构总结: `ai-service/REFACTOR_SUMMARY.md`
