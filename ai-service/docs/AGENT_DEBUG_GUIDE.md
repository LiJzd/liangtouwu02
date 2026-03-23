# Agent 调试指南

## 概述

本系统实现了多智能体 ReAct 循环的高透明度追踪机制，包括：

1. **Rich 控制台追踪**：彩色格式化的 Agent 内部状态输出
2. **SSE 调试流**：实时推送 Agent 推理过程到前端
3. **极简调试网页**：独立的 HTML 页面，无需 Vue 框架

## 核心原则

### 输出隔离（防止思考链污染）

**红线规则**：Agent 的 `Thought`、`Action`、`Observation` 绝对禁止进入 `final_answer`。

实现机制：
- `_extract_final_answer()` 函数使用正则提取 "Final Answer: xxx"
- 所有思考过程仅记录到日志和调试流
- 用户只看到最终结论

### 可观测性分层

```
┌─────────────────────────────────────┐
│  用户层：只看 Final Answer          │
├─────────────────────────────────────┤
│  开发者层：Rich 控制台 + SSE 流     │
│  - Thought (思考)                   │
│  - Action (工具调用)                │
│  - Observation (工具返回)           │
├─────────────────────────────────────┤
│  日志层：完整的 JSON 状态           │
└─────────────────────────────────────┘
```

## 使用方法

### 1. Rich 控制台追踪

启动服务后，Agent 执行时会自动在控制台输出彩色追踪信息：

```bash
cd ai-service
python main.py
```

控制台输出示例：
```
============================================================
🚀 ReAct 推理引擎启动
============================================================

╭─────────── 用户问题 ───────────╮
│ 我的猪场有哪些猪？              │
╰─────────────────────────────────╯

╭─────────── Agent 决策 ──────────╮
│ 🤖 Action: list_pigs            │
│ 📝 Input: {"limit": 50}         │
╰─────────────────────────────────╯

🔧 工具启动: list_pigs

╭─────────── 工具返回 ────────────╮
│ ✅ Output: {"pigs": [...]}      │
╰─────────────────────────────────╯

╭─────────── ✨ Final Answer ─────╮
│ 您的猪场目前有 12 头猪...       │
╰─────────────────────────────────╯

============================================================
✅ ReAct 推理完成
============================================================
```

### 2. SSE 调试流

#### 方式 A：使用调试网页（推荐）

1. 启动服务
2. 浏览器访问：`http://localhost:8000/static/debug.html`
3. 点击"连接"按钮
4. 在另一个窗口发送 Agent 请求，调试页面会实时显示内部状态

#### 方式 B：使用 Python 脚本

```bash
cd ai-service/tests
python test_agent_debug.py
```

#### 方式 C：使用 curl

```bash
curl -N http://localhost:8000/api/v1/agent/debug/agent-trace?client_id=my_debug
```

### 3. API 调用示例

```python
import httpx
import asyncio

async def chat_with_debug():
    # 发送对话请求
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/agent/chat",
            json={
                "user_id": "user_123",
                "messages": [
                    {"role": "user", "content": "我的猪场有哪些猪？"}
                ]
            }
        )
        print(response.json())

asyncio.run(chat_with_debug())
```

同时在浏览器打开 `http://localhost:8000/static/debug.html?client_id=user_user_123` 查看调试信息。

## 调试事件类型

| 事件类型 | 说明 | 数据结构 |
|---------|------|---------|
| `connected` | SSE 连接成功 | `{"message": "..."}` |
| `thought` | Agent 思考过程 | `{"content": "..."}` |
| `action` | 工具调用决策 | `{"tool": "...", "input": "..."}` |
| `observation` | 工具返回结果 | `{"output": "..."}` |
| `final_answer` | 最终答案 | `{"answer": "..."}` |
| `error` | 执行错误 | `{"message": "..."}` |
| `heartbeat` | 心跳包（30秒） | `{}` |

## 配置选项

### 环境变量

```bash
# .env 文件
DASHSCOPE_API_KEY=sk-xxx  # 阿里百炼 API Key
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
DASHSCOPE_MODEL=qwen-plus
```

### 代码配置

```python
# v1/logic/central_agent_core.py

# 修改 ReAct 最大迭代次数
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    max_iterations=5,  # 默认 5 次，可调整
    ...
)
```

## 故障排查

### 问题 1：控制台没有彩色输出

**原因**：Rich 库未安装或 Windows 终端不支持

**解决**：
```bash
pip install rich
# Windows 用户建议使用 Windows Terminal
```

### 问题 2：SSE 连接立即断开

**原因**：Nginx 缓冲导致

**解决**：在 Nginx 配置中添加
```nginx
location /api/v1/agent/debug/ {
    proxy_buffering off;
    proxy_cache off;
    proxy_set_header Connection '';
    proxy_http_version 1.1;
    chunked_transfer_encoding off;
}
```

### 问题 3：思考链污染用户回复

**检查**：查看日志中是否有警告
```
WARNING: 检测到思考链污染，原始回复: Thought: ...
```

**解决**：检查 `_extract_final_answer()` 函数是否正常工作

## 性能影响

- **Rich 控制台**：几乎无性能影响（仅格式化输出）
- **SSE 调试流**：每个连接占用 ~1MB 内存，建议生产环境关闭
- **日志记录**：使用 `logger.debug()`，生产环境自动禁用

## 生产环境建议

1. **关闭 SSE 调试端点**：在 `main.py` 中注释掉 `agent_debug_router` 的挂载
2. **保留 Rich 控制台**：便于运维人员排查问题
3. **日志级别设为 INFO**：避免 debug 日志过多

## 下一步

- [ ] 实现 Supervisor-Worker 多智能体架构（阶段 1）
- [ ] Java 后端 API 改造（阶段 6）
- [ ] 添加 WebSocket 支持（双向通信）
- [ ] 集成 LangSmith 追踪（可选）
