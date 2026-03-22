# ReAct模式快速启动指南

## 1. 确认改动

已完成的改动：

✅ 导入 `create_react_agent` 和 `AgentExecutor`  
✅ 添加 ReAct 提示词模板  
✅ 改造 `_run_agent_once` 函数  
✅ 更新 `_call_agent` 函数  
✅ 添加详细日志输出  

## 2. 重启服务

```bash
# 停止当前运行的服务
Ctrl+C

# 重新启动
cd 两头乌ai端
python bot_runner.py
```

## 3. 测试ReAct模式

### 测试1：视频截图识别

**发送消息**：
```
我想看看猪场情况，给我张图片
```

**预期日志**：
```
[智能体] ========== ReAct 推理开始 ==========

> Entering new AgentExecutor chain...

Thought: 用户想查看猪场的当前情况，我需要使用视频截图识别工具

Action: capture_pig_farm_snapshot
Action Input: 

Observation: {"success": true, "detection_count": 3, ...}

Thought: 我现在知道最终答案了

Final Answer: 师傅，刚看了监控 📸 检测到3只猪...

> Finished chain.

[智能体] ========== ReAct 推理结束 ==========
```

### 测试2：查询猪只列表

**发送消息**：
```
我的猪场有哪些猪？
```

**预期日志**：
```
[智能体] ========== ReAct 推理开始 ==========

Thought: 用户想知道猪场有哪些猪，我需要使用list_pigs工具

Action: list_pigs
Action Input: limit=50

Observation: [{"pig_id": "PIG001", ...}, ...]

Thought: 我现在知道最终答案了

Final Answer: 师傅，猪场现在有5只猪...

[智能体] ========== ReAct 推理结束 ==========
```

### 测试3：多步推理

**发送消息**：
```
帮我看看猪场有多少猪，然后查一下第一只的详细信息
```

**预期日志**：
```
[智能体] ========== ReAct 推理开始 ==========

Thought: 用户想知道猪场有多少猪，并且要查看第一只的详细信息

Action: list_pigs
Action Input: limit=50

Observation: [{"pig_id": "PIG001", ...}, ...]

Thought: 现在我知道猪场有5只猪，第一只是PIG001。接下来我需要查询详细信息

Action: get_pig_info_by_id
Action Input: pig_id=PIG001

Observation: {"pig_id": "PIG001", "breed": "杜洛克", ...}

Thought: 我现在知道最终答案了

Final Answer: 师傅，猪场现在有5只猪...

[智能体] ========== ReAct 推理结束 ==========
```

## 4. 验证成功标志

✅ 日志中出现 `========== ReAct 推理开始 ==========`  
✅ 看到 `Thought:` 思考过程  
✅ 看到 `Action:` 和 `Action Input:`  
✅ 看到 `Observation:` 工具输出  
✅ 看到 `Final Answer:` 最终答案  
✅ 日志中出现 `========== ReAct 推理结束 ==========`  

## 5. 常见问题

### Q1: 看不到ReAct日志？

**检查**：
1. 是否重启了服务？
2. 是否在正确的终端查看日志？
3. 日志级别是否设置为INFO？

**解决**：
```bash
# 确保在运行bot_runner.py的终端查看
# 日志会实时输出
```

### Q2: Agent不按ReAct格式输出？

**可能原因**：
1. LLM模型不支持（需要qwen-plus或更高版本）
2. 提示词模板有问题

**解决**：
```python
# 检查 .env 文件
DASHSCOPE_MODEL=qwen-plus  # 或 qwen-max
```

### Q3: 工具调用失败？

**检查日志**：
```
[智能体][工具开始] tool_name 输入=...
[智能体][工具结束] 输出=...
```

如果看到错误，说明工具本身有问题，不是ReAct的问题。

### Q4: 响应变慢了？

**正常现象**：
- ReAct模式会增加约0.5秒响应时间
- 因为需要生成更详细的推理过程
- 用户体验不受影响（用户看到的回复相同）

**优化**：
```python
# 减少最大迭代次数
max_iterations=3  # 从5降到3
```

## 6. 调试技巧

### 查看完整推理链

```bash
# 在日志中搜索
grep "ReAct 推理" logs/algorithm.log
```

### 查看工具调用

```bash
# 在日志中搜索
grep "工具开始\|工具结束" logs/algorithm.log
```

### 查看思考过程

```bash
# 在日志中搜索
grep "Thought:\|Action:\|Observation:" logs/algorithm.log
```

## 7. 性能监控

### 响应时间

```python
import time

start = time.time()
result = agent_executor.invoke({"input": input_text})
elapsed = time.time() - start

print(f"响应时间: {elapsed:.2f}秒")
```

### 工具调用次数

```python
intermediate_steps = result.get("intermediate_steps", [])
print(f"工具调用次数: {len(intermediate_steps)}")
```

### 迭代次数

```python
# 在日志中统计 "Thought:" 出现次数
```

## 8. 下一步

- ✅ 测试所有工具是否正常工作
- ✅ 优化提示词模板
- ✅ 调整最大迭代次数
- ✅ 监控性能指标
- ✅ 收集用户反馈

## 9. 回滚方案

如果ReAct模式有问题，可以快速回滚：

```python
# 在 central_agent_core.py 中
# 注释掉 ReAct 相关代码
# 恢复原来的 create_agent 方式

# 或者直接使用 git
git checkout HEAD -- v1/logic/central_agent_core.py
```

## 10. 参考文档

- [ReAct模式详细说明](./REACT_MODE.md)
- [ReAct vs 传统模式对比](./REACT_COMPARISON.md)
- [BOT工作流程](./BOT_WORKFLOW.md)

---

## 快速检查清单

启动前：
- [ ] 代码已更新
- [ ] 依赖已安装（langchain, langchain-openai）
- [ ] 环境变量已配置（DASHSCOPE_API_KEY）
- [ ] 模型版本正确（qwen-plus或更高）

启动后：
- [ ] 服务正常启动
- [ ] 日志中出现ReAct标记
- [ ] 工具调用正常
- [ ] 用户回复正常

测试：
- [ ] 视频截图识别
- [ ] 猪只列表查询
- [ ] 猪只详情查询
- [ ] 多步推理
- [ ] 错误处理

---

**准备好了吗？重启服务，开始体验ReAct模式吧！** 🚀
