# ReAct 模式智能体说明

## 什么是 ReAct？

ReAct（Reasoning + Acting）是一种让AI智能体更透明、更可控的推理模式。它要求Agent明确展示：

1. **Thought（思考）**：Agent在思考什么
2. **Action（行动）**：Agent决定采取什么行动
3. **Action Input（行动输入）**：行动的具体参数
4. **Observation（观察）**：行动的结果
5. **Final Answer（最终答案）**：基于观察得出的答案

## ReAct vs 传统模式

### 传统模式（Tool Calling）

```
用户: 我想看看猪场情况
Agent: [内部黑盒处理]
      [调用工具]
      [生成回复]
回复: 师傅，刚看了监控，检测到3只猪...
```

**问题**：
- 看不到Agent的思考过程
- 不知道为什么调用某个工具
- 难以调试和优化

### ReAct模式

```
用户: 我想看看猪场情况

[智能体] ========== ReAct 推理开始 ==========
Thought: 用户想查看猪场的当前情况，我需要使用视频截图工具来获取实时画面
Action: capture_pig_farm_snapshot
Action Input: {"confidence": 50}
Observation: {"success": true, "detection_count": 3, "summary": "检测到 3只pig"}
Thought: 我现在知道最终答案了
Final Answer: 师傅，刚看了监控 📸 检测到3只猪，都在活动，状态看着挺正常的 👍
[智能体] ========== ReAct 推理结束 ==========

回复: 师傅，刚看了监控 📸 检测到3只猪...
```

**优势**：
- ✅ 思考过程透明
- ✅ 工具调用有理有据
- ✅ 便于调试和优化
- ✅ 可以追踪推理链路

## 实现细节

### 1. ReAct 提示词模板

```python
REACT_PROMPT_TEMPLATE = """你是一个智能助手，可以使用工具来回答问题。

你可以使用以下工具：

{tools}

使用以下格式进行推理和行动：

Question: 用户的问题
Thought: 你应该思考要做什么
Action: 要采取的行动，必须是 [{tool_names}] 中的一个
Action Input: 行动的输入参数
Observation: 行动的结果
... (这个 Thought/Action/Action Input/Observation 可以重复N次)
Thought: 我现在知道最终答案了
Final Answer: 对原始问题的最终答案

重要规则：
1. 必须严格按照上述格式输出
2. Action 必须是工具列表中的一个
3. 如果不需要工具，直接给出 Final Answer
4. 回答要简洁、通俗易懂
5. 使用表情符号让回答更友好

开始！

Question: {input}
Thought: {agent_scratchpad}"""
```

### 2. Agent 创建

```python
# 创建ReAct Agent
agent = create_react_agent(llm=llm, tools=tools, prompt=react_prompt)

# 创建Agent Executor（带详细日志）
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,  # 启用详细日志，显示思考过程
    handle_parsing_errors=True,  # 处理解析错误
    max_iterations=5,  # 最大迭代次数
    return_intermediate_steps=True,  # 返回中间步骤
)
```

### 3. 执行和日志

```python
# 执行Agent
result = agent_executor.invoke({"input": input_text})

# 提取中间步骤
intermediate_steps = result.get("intermediate_steps", [])
for step in intermediate_steps:
    action, observation = step[0], step[1]
    print(f"Action: {action.tool}")
    print(f"Action Input: {action.tool_input}")
    print(f"Observation: {observation}")
```

## 使用示例

### 示例1：查看猪场情况

**用户输入**：
```
我想看看猪场情况，给我张图片
```

**ReAct推理过程**：
```
[智能体] ========== ReAct 推理开始 ==========
[智能体] 思考过程:
  Action: capture_pig_farm_snapshot
  Action Input: 
  Observation: {
    "success": true,
    "video_file": "pig_farm_video.mp4",
    "detection_count": 3,
    "detections": [
      {
        "class_name": "pig",
        "confidence": 0.856,
        "bbox": {"x1": 0.234, "y1": 0.456, "x2": 0.567, "y2": 0.789}
      },
      {
        "class_name": "pig",
        "confidence": 0.823,
        "bbox": {"x1": 0.123, "y1": 0.234, "x2": 0.345, "y2": 0.567}
      },
      {
        "class_name": "pig",
        "confidence": 0.791,
        "bbox": {"x1": 0.678, "y1": 0.345, "x2": 0.890, "y2": 0.678}
      }
    ],
    "summary": "检测到 3只pig"
  }
[智能体] ========== ReAct 推理结束 ==========
```

**最终回复**：
```
师傅，刚看了监控 📸
检测到3只猪，都在活动
状态看着挺正常的 👍
```

### 示例2：查询猪只信息

**用户输入**：
```
帮我查一下PIG001的档案
```

**ReAct推理过程**：
```
[智能体] ========== ReAct 推理开始 ==========
[智能体] 思考过程:
  Action: get_pig_info_by_id
  Action Input: pig_id=PIG001
  Observation: {
    "pig_id": "PIG001",
    "breed": "杜洛克",
    "current_month": 3,
    "current_weight_kg": 45.0,
    "lifecycle": [...]
  }
[智能体] ========== ReAct 推理结束 ==========
```

**最终回复**：
```
师傅，PIG001的档案找到了 📋
品种：杜洛克
当前：3个月，45公斤
长势不错 👍
```

### 示例3：多步推理

**用户输入**：
```
帮我看看猪场有多少猪，然后查一下第一只的详细信息
```

**ReAct推理过程**：
```
[智能体] ========== ReAct 推理开始 ==========
[智能体] 思考过程:
  Action: list_pigs
  Action Input: limit=50
  Observation: [{"pig_id": "PIG001", ...}, {"pig_id": "PIG002", ...}, ...]
  
  Action: get_pig_info_by_id
  Action Input: pig_id=PIG001
  Observation: {"pig_id": "PIG001", "breed": "杜洛克", ...}
[智能体] ========== ReAct 推理结束 ==========
```

**最终回复**：
```
师傅，猪场现在有5只猪 🐷
第一只是PIG001，杜洛克品种
3个月大，45公斤，长势不错 👍
```

## 配置选项

### 1. 详细日志

```python
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,  # True: 显示详细日志, False: 静默模式
)
```

### 2. 最大迭代次数

```python
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    max_iterations=5,  # 最多执行5次工具调用
)
```

防止Agent陷入无限循环。

### 3. 错误处理

```python
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    handle_parsing_errors=True,  # 自动处理格式解析错误
)
```

当Agent输出格式不正确时，自动重试。

## 调试技巧

### 1. 查看完整推理过程

在日志中搜索：
```
[智能体] ========== ReAct 推理开始 ==========
```

### 2. 检查工具调用

查看 `Action` 和 `Action Input`：
```
Action: capture_pig_farm_snapshot
Action Input: {"confidence": 50}
```

### 3. 验证观察结果

查看 `Observation`：
```
Observation: {"success": true, "detection_count": 3, ...}
```

### 4. 追踪思考链路

完整的推理链：
```
Question → Thought → Action → Observation → Thought → Final Answer
```

## 性能优化

### 1. 减少迭代次数

```python
max_iterations=3  # 从5降到3，加快响应
```

### 2. 简化提示词

移除不必要的说明，保留核心格式要求。

### 3. 缓存工具结果

对于相同的工具调用，缓存结果避免重复执行。

## 常见问题

### Q1: Agent不按ReAct格式输出怎么办？

**A**: 检查以下几点：
1. 提示词模板是否正确
2. LLM是否支持指令遵循（推荐使用qwen-plus或更高版本）
3. 是否启用了 `handle_parsing_errors=True`

### Q2: Agent一直循环调用工具？

**A**: 设置合理的 `max_iterations`：
```python
max_iterations=5  # 最多5次迭代
```

### Q3: 如何关闭详细日志？

**A**: 设置 `verbose=False`：
```python
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=False,  # 关闭详细日志
)
```

### Q4: 思考过程太长，影响性能？

**A**: 思考过程只在服务端日志中显示，不会发送给用户，不影响用户体验。

## 与传统模式对比

| 特性 | 传统Tool Calling | ReAct模式 |
|------|-----------------|-----------|
| 透明度 | ❌ 黑盒 | ✅ 白盒 |
| 可调试性 | ❌ 困难 | ✅ 容易 |
| 推理链路 | ❌ 不可见 | ✅ 可见 |
| 多步推理 | ⚠️ 支持但不透明 | ✅ 清晰展示 |
| 性能 | ✅ 稍快 | ⚠️ 稍慢（因为输出更多） |
| 错误追踪 | ❌ 困难 | ✅ 容易 |

## 最佳实践

1. **开发阶段**：启用 `verbose=True`，便于调试
2. **生产环境**：可以保持 `verbose=True`，日志只在服务端
3. **复杂任务**：增加 `max_iterations`
4. **简单任务**：减少 `max_iterations` 提高性能
5. **监控日志**：定期检查推理过程，优化提示词

## 总结

ReAct模式让猪BOT智能体的推理过程变得透明可控：

- ✅ 每一步思考都有记录
- ✅ 每一次工具调用都有理由
- ✅ 每一个决策都可追溯
- ✅ 便于调试和优化

这对于生产环境的AI系统尤其重要，因为我们需要知道AI为什么做出某个决策，而不是盲目信任黑盒输出。
