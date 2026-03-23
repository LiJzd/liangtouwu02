# 服务启动指南

## 当前状态
✅ 前端已启动：http://localhost:5173  
❌ Java 后端未启动（8080 端口）  
❌ Python AI 未启动（8000 端口）

## 快速启动步骤

### 1. 启动 Java 后端（必需）

#### 方式 1: 使用 Maven（推荐）
```bash
cd backend
mvn clean package -DskipTests
java -jar liangtouwu-app/target/liangtouwu-app-1.0.0.jar
```

#### 方式 2: 使用 IDE
1. 打开 IDEA
2. 找到 `LiangtouwuApplication.java`
3. 右键 → Run

#### 验证
```bash
curl http://localhost:8080/actuator/health
# 预期返回: {"status":"UP"}
```

### 2. 启动 Python AI 服务（可选）

```bash
cd ai-service
python main.py
```

#### 验证
```bash
curl http://localhost:8000/health
# 预期返回: {"status":"ok"}
```

### 3. 访问前端

浏览器打开：http://localhost:5173

## 常见问题

### Q1: Java 编译失败 - Swagger 依赖缺失

**已修复**：所有 Swagger 注解已移除，现在可以正常编译。

重新编译：
```bash
cd backend
mvn clean package -DskipTests
```

### Q2: 端口被占用

**8080 端口被占用**：
```bash
# Windows
netstat -ano | findstr :8080
taskkill /PID <PID> /F

# Linux/Mac
lsof -i :8080
kill -9 <PID>
```

**5173 端口被占用**：
```bash
# 修改 frontend/vite.config.ts 中的端口
server: {
  port: 5174  // 改为其他端口
}
```

### Q3: 数据库连接失败

检查 `backend/liangtouwu-app/src/main/resources/application.yml`：
```yaml
spring:
  datasource:
    url: jdbc:mysql://localhost:3306/liangtouwu
    username: root
    password: your-password  # 修改为实际密码
```

### Q4: 前端代理错误（ECONNREFUSED）

**原因**：Java 后端未启动

**解决**：先启动 Java 后端，再刷新前端页面

## 服务端口总览

| 服务 | 端口 | 状态 | 访问地址 |
|-----|------|------|---------|
| 前端 | 5173 | ✅ 运行中 | http://localhost:5173 |
| Java 后端 | 8080 | ❌ 未启动 | http://localhost:8080 |
| Python AI | 8000 | ❌ 未启动 | http://localhost:8000 |
| 调试页面 | 8000 | ❌ 未启动 | http://localhost:8000/static/debug.html |

## 最小启动配置

如果只想看前端界面（不需要 AI 功能）：

1. 启动 Java 后端（必需）
2. 前端已启动（已完成）

如果需要 AI 对话功能：

1. 启动 Java 后端（必需）
2. 启动 Python AI 服务（必需）
3. 前端已启动（已完成）

## 下一步

1. 启动 Java 后端
2. 刷新前端页面
3. 测试功能是否正常

## 完整启动命令（Windows）

```bash
# 终端 1: Java 后端
cd backend
mvn clean package -DskipTests
java -jar liangtouwu-app/target/liangtouwu-app-1.0.0.jar

# 终端 2: Python AI（可选）
cd ai-service
python main.py

# 终端 3: 前端（已启动）
cd frontend
npm run dev
```

## 完整启动命令（Linux/Mac）

```bash
# 终端 1: Java 后端
cd backend
mvn clean package -DskipTests
java -jar liangtouwu-app/target/liangtouwu-app-1.0.0.jar

# 终端 2: Python AI（可选）
cd ai-service
python main.py

# 终端 3: 前端（已启动）
cd frontend
npm run dev
```
