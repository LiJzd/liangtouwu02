# 猪BOT智能体工作流程详解

## 概述

猪BOT是一个基于QQ机器人的智能对话系统，集成了工具调用能力（Tool Calling）和RAG知识库，能够处理用户关于猪场管理的各种查询。

## 整体架构

```
用户（QQ）
    ↓
QQ官方服务器
    ↓
bot_runner.py (QQ Bot客户端)
    ↓
bot_controller.py (FastAPI端点)
    ↓
bot_agent.py (消息处理逻辑)
    ↓
central_agent_controller.py (Agent端点)
    ↓
central_agent_core.py (LangChain Agent)
    ↓
bot_tools.py (工具注册表)
    ↓
[各种工具实现]
```

## 详细工作流程

### 1. 消息接收阶段

```python
# bot_runner.py
@client.on_c2c_message_create
async def on_c2c_message_create(event: C2CMessageEvent):
    # 接收QQ用户的私聊消息
    user_openid = event.author.user_openid
    content = event.content
    
    # 调用bot_controller处理
    response = await handle_message(user_openid, content)
```

**关键点**：
- 使用QQ官方Bot SDK (botpy)
- 监听C2C（用户对机器人）消息事件
- 提取用户ID和消息内容

### 2. 消息路由阶段

```python
# bot_controller.py
@router.post("/handle")
async def handle_message_api(payload: BotHandleRequest):
    # 路由到bot_agent处理
    reply = await handle_message(session, payload.qq_user_id, payload.message)
    return BotHandleResponse(reply=reply)
```

**关键点**：
- FastAPI端点：`POST /api/v1/bot/handle`
- 提供HTTP接口供bot_runner调用
- 管理数据库会话

### 3. 消息预处理阶段

```python
# bot_agent.py
async def _handle_message_locked(session, qq_user_id, message, guild_id):
    # 1. 确保用户存在
    await ensure_user(session, qq_user_id, guild_id)
    
    # 2. 判断话题类型
    is_pig = _is_pig_topic(message)  # 检查是否包含"猪"、"养殖"等关键词
    
    # 3. 选择系统提示词
    system_prompt = _SYSTEM_PROMPT if is_pig else _SYSTEM_PROMPT_GENERAL
    
    # 4. 获取历史对话
    history = await _get_history(session, qq_user_id, max_history=6)
    
    # 5. 构建消息列表
    messages = _build_messages(system_prompt, history, message)
```

**关键点**：
- 用户锁机制：防止并发消息冲突
- 话题识别：区分猪场话题和普通聊天
- 历史管理：保留最近6轮对话
- 系统提示词：根据话题选择不同的角色设定

### 4. Agent调用阶段

```python
# bot_agent.py
async def _call_central_agent(qq_user_id, messages):
    # 调用Central Agent的HTTP端点
    url = "http://127.0.0.1:8000/api/v1/agent/chat"
    payload = {
        "user_id": qq_user_id,
        "messages": messages,
        "metadata": {"channel": "c2c", "source": "qq_bot"}
    }
    
    response = await client.post(url, json=payload)
    return response.json()["reply"]
```

**关键点**：
- HTTP调用：bot_agent通过HTTP调用central_agent
- 超时设置：默认20秒超时
- 降级策略：如果调用失败，返回fallback回复

### 5. Central Agent处理阶段

```python
# central_agent_controller.py
@router.post("/chat")
async def chat(payload: AgentChatRequest):
    # 调用核心逻辑
    reply = generate_reply(payload.messages)
    return AgentChatResponse(reply=reply)
```

```python
# central_agent_core.py
def generate_reply(messages: List[dict]) -> str:
    # 1. 尝试使用Agent（带工具调用）
    agent_reply = _call_agent(messages)
    if agent_reply:
        return agent_reply
    
    # 2. 降级到纯LLM（不带工具）
    llm_reply = _call_llm(messages)
    if llm_reply:
        return llm_reply
    
    # 3. 最终降级
    return "系统繁忙，您先说情况，我马上回复。"
```

**关键点**：
- 三层降级策略：Agent → LLM → Fallback
- 确保系统高可用性

### 6. Agent工具调用阶段

```python
# central_agent_core.py
def _call_agent(messages: List[dict]) -> Optional[str]:
    # 1. 解析消息
    system_prompt, chat_history, user_input = _split_messages(messages)
    
    # 2. 判断是否需要工具
    needs_tool = _requires_tool(user_input)
    
    # 3. 创建LangChain Agent
    llm = _build_llm(api_key, base_url, model)
    tools = _build_lc_tools()  # 从bot_tools.py加载工具
    agent = create_agent(model=llm, tools=tools, system_prompt=system_prompt)
    
    # 4. 执行Agent
    result = agent.invoke({"messages": chat_history + [user_input]})
    
    # 5. 如果需要工具但未调用，强制重试
    if needs_tool and not tool_outputs:
        # 添加强制工具调用提示
        system_prompt += "\n必须调用工具获取结果，禁止凭空编造"
        result = agent.invoke(...)  # 重试
    
    return result
```

**关键点**：
- 关键词匹配：`_requires_tool` 函数检查用户输入
- 强制工具调用：如果检测到需要工具但Agent没调用，会强制重试
- 工具输出验证：检查工具返回的错误信息

### 7. 工具执行阶段

```python
# central_agent_core.py
def _build_lc_tools() -> list[LCTool]:
    from v1.logic.bot_tools import list_tools
    
    tools = []
    for tool in list_tools().values():
        def _call(arg: str) -> str:
            # 异步工具在同步上下文中执行
            result = _run_async(tool.handler(arg))
            return result
        
        tools.append(LCTool(
            name=tool.name,
            description=tool.description,
            func=_call
        ))
    return tools
```

```python
# bot_tools.py
@tool(name="capture_pig_farm_snapshot", description="截取猪场视频图像...")
async def tool_capture_pig_farm_snapshot(arg: str) -> str:
    # 1. 解析参数
    data = _parse_args(arg)
    
    # 2. 查找视频文件
    video_file = find_video_file()
    
    # 3. 截取视频帧
    cap = cv2.VideoCapture(video_file)
    success, frame = cap.read()
    
    # 4. YOLO检测
    model = get_yolo_model()
    results = model(frame, conf=confidence)
    
    # 5. 解析结果
    detections = parse_yolo_results(results, frame.shape, confidence)
    
    # 6. 返回JSON
    return json.dumps({
        "success": True,
        "detection_count": len(detections),
        "detections": [...],
        "summary": "检测到 3只pig"
    })
```

**关键点**：
- 工具注册：使用装饰器 `@tool` 注册
- 参数解析：支持多种格式（JSON、键值对、纯文本）
- 异步执行：工具是异步的，但在同步Agent中通过线程执行
- 结构化输出：返回JSON格式便于Agent理解

### 8. 回复生成阶段

```python
# central_agent_core.py
def _call_agent(messages):
    # ... Agent执行 ...
    
    # 提取最终回复
    for msg in reversed(messages_out):
        if isinstance(msg, AIMessage) and msg.content:
            output = msg.content
            break
    
    # 检查工具错误
    for msg in messages_out:
        if isinstance(msg, ToolMessage):
            err = _extract_tool_error(msg.content)
            if err:
                return f"工具调用失败：{err}"
    
    return output
```

**关键点**：
- 消息类型：区分AIMessage（Agent回复）和ToolMessage（工具输出）
- 错误处理：优先返回工具错误，避免Agent编造信息

### 9. 回复后处理阶段

```python
# bot_agent.py
def _postprocess_reply(text: str) -> str:
    # 1. 去除固定前缀
    text = _strip_canned_prefix(text)
    
    # 2. 缩短过长回复
    text = _shorten_reply(text, max_lines=3, max_sentences=3, max_chars=120)
    
    return text
```

**关键点**：
- 去除模板化开头（如"掌上明猪"、"猪BOOT"等）
- 限制回复长度（适应QQ消息场景）
- 保持语气通俗易懂

### 10. 消息发送阶段

```python
# bot_agent.py
async def _handle_message_locked(...):
    # ... 处理逻辑 ...
    
    # 保存对话历史
    await _save_turn(session, qq_user_id, "user", text)
    await _save_turn(session, qq_user_id, "assistant", reply)
    
    return reply
```

```python
# bot_runner.py
async def _handle_and_reply(event, content):
    # 调用处理逻辑
    response = await handle_message(user_openid, content)
    
    # 发送回复
    await client.api.post_c2c_message(
        openid=user_openid,
        msg_type=0,
        content=response["reply"]
    )
```

**关键点**：
- 历史保存：存入数据库供下次对话使用
- QQ消息发送：通过官方API发送

## 为什么刚刚没有调用工具？

根据日志分析：

```
[INFO] c2c received: content='我想看看猪场情况，给我张图片'
[INFO] handle status=200 body={"reply":"猪舍西南角摄像头拍到空画面..."}
```

**可能的原因**：

### 1. 关键词未匹配（已修复）

**问题**：`_requires_tool` 函数中缺少"图片"、"情况"等关键词

**修复前**：
```python
keywords = [
    "工具", "功能", "查", "查询", "看看", "猪场", ...
]
```

**修复后**：
```python
keywords = [
    # ... 原有关键词 ...
    "图片", "照片", "视频", "监控", "摄像", "现场", 
    "情况", "状态", "现在", "当前", "截图", "截取",
    "识别", "检测", "有多少", "多少只"
]
```

### 2. 系统提示词未更新（已修复）

**问题**：系统提示词中没有告诉Agent何时调用新工具

**修复前**：
```
10. 用户问生长曲线/预测/未来轨迹，调用 query_pig_growth_prediction
11. 只回答用户最后一句问题...
```

**修复后**：
```
10. 用户问生长曲线/预测/未来轨迹，调用 query_pig_growth_prediction
11. 用户问猪场情况/现场/图片/视频/监控/有多少猪，调用 capture_pig_farm_snapshot
12. 只回答用户最后一句问题...
```

### 3. 需要重启服务

**重要**：修改代码后必须重启服务才能生效！

```bash
# 停止当前运行的服务
Ctrl+C

# 重新启动
python main.py
# 或
python bot_runner.py
```

## 测试新功能

重启服务后，尝试以下对话：

```
用户: 我想看看猪场情况，给我张图片
预期: BOT调用 capture_pig_farm_snapshot 工具

用户: 现在猪场有多少只猪？
预期: BOT调用 capture_pig_farm_snapshot 工具

用户: 帮我看看监控
预期: BOT调用 capture_pig_farm_snapshot 工具
```

## 调试技巧

### 1. 查看Agent日志

```python
# central_agent_core.py 中会打印：
print(f"[智能体][工具开始] {tool_name} 输入={arg}")
print(f"[智能体][工具结束] 输出={result}")
```

### 2. 查看关键词匹配

```python
# 在 _requires_tool 函数中添加调试：
def _requires_tool(user_input: str) -> bool:
    text = (user_input or "").strip().lower()
    result = any(k in text for k in keywords)
    print(f"[DEBUG] 关键词匹配: {text} -> {result}")
    return result
```

### 3. 查看工具注册

```python
# 在 _build_lc_tools 函数中添加：
def _build_lc_tools():
    tools = list_tools()
    print(f"[DEBUG] 已注册工具: {list(tools.keys())}")
    # ...
```

## 工作流程图

```
┌─────────────┐
│  用户发消息  │
└──────┬──────┘
       │
       ↓
┌─────────────────┐
│  QQ Bot接收     │
│  (bot_runner)   │
└──────┬──────────┘
       │
       ↓
┌─────────────────┐
│  HTTP调用       │
│  /api/v1/bot/   │
│  handle         │
└──────┬──────────┘
       │
       ↓
┌─────────────────┐
│  消息预处理     │
│  - 话题识别     │
│  - 历史加载     │
│  - 提示词选择   │
└──────┬──────────┘
       │
       ↓
┌─────────────────┐
│  HTTP调用       │
│  /api/v1/agent/ │
│  chat           │
└──────┬──────────┘
       │
       ↓
┌─────────────────┐
│  关键词匹配     │
│  _requires_tool │
└──────┬──────────┘
       │
       ├─ 需要工具 ──→ ┌──────────────┐
       │              │ LangChain    │
       │              │ Agent        │
       │              │ (带工具)     │
       │              └──────┬───────┘
       │                     │
       │                     ↓
       │              ┌──────────────┐
       │              │ 工具调用     │
       │              │ - list_pigs  │
       │              │ - get_pig_   │
       │              │   info       │
       │              │ - capture_   │
       │              │   snapshot   │
       │              └──────┬───────┘
       │                     │
       │                     ↓
       │              ┌──────────────┐
       │              │ 工具执行     │
       │              │ - 视频截取   │
       │              │ - YOLO检测   │
       │              │ - 结果解析   │
       │              └──────┬───────┘
       │                     │
       └─ 不需要工具 ─┐      │
                      │      │
                      ↓      ↓
               ┌──────────────┐
               │  生成回复    │
               └──────┬───────┘
                      │
                      ↓
               ┌──────────────┐
               │  回复后处理  │
               │  - 去前缀    │
               │  - 缩短      │
               └──────┬───────┘
                      │
                      ↓
               ┌──────────────┐
               │  保存历史    │
               └──────┬───────┘
                      │
                      ↓
               ┌──────────────┐
               │  发送给用户  │
               └──────────────┘
```

## 总结

猪BOT的工作流程包含多个层次：

1. **消息接收层**：QQ Bot SDK
2. **路由层**：FastAPI端点
3. **业务逻辑层**：bot_agent消息处理
4. **Agent层**：LangChain Agent + 工具调用
5. **工具层**：各种业务工具实现
6. **数据层**：MySQL、向量库、YOLO模型

关键机制：
- **关键词触发**：通过 `_requires_tool` 判断是否需要工具
- **强制重试**：如果需要工具但未调用，会强制重试
- **三层降级**：Agent → LLM → Fallback
- **历史管理**：保留最近6轮对话
- **异步执行**：工具异步执行，通过线程桥接到同步Agent

修复后，BOT应该能正确识别用户意图并调用 `capture_pig_farm_snapshot` 工具了！
