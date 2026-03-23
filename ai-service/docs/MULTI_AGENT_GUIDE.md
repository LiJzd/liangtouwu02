# 多智能体架构指南

## 架构概览

系统采用 **Supervisor-Worker** 模式，实现意图路由和专家分工。

```
用户请求
    ↓
SupervisorAgent (意图路由)
    ↓
    ├─→ VetAgent (兽医诊断)
    ├─→ DataAgent (数据查询)
    ├─→ PerceptionAgent (视觉识别)
    └─→ DirectReply (直接回复)
    ↓
返回结果
```

## 核心组件

### 1. SupervisorAgent（调度中心）

**职责**：根据用户问题，选择最合适的 Worker 处理。

**路由策略**：
1. **LLM 路由**（优先）：使用 LLM 理解意图，准确率高
2. **规则引擎**（兜底）：基于关键词匹配，稳定可靠

**路由目标**：
- `vet_agent`：兽医诊断、疾病分析、用药建议
- `data_agent`：猪只档案、生长曲线、数据统计
- `perception_agent`：视频监控、图像识别、现场情况
- `direct_reply`：闲聊、问候（不需要专家）

**示例**：
```python
supervisor = SupervisorAgent()
worker_name = supervisor.route("我的猪拉稀了怎么办？")
# 返回: "vet_agent"
```

### 2. WorkerAgent（专家基类）

**职责**：执行具体任务，独立的 ReAct 循环。

**核心方法**：
- `get_tools()`：返回该 Worker 可用的工具列表
- `execute(context)`：执行 ReAct 循环，返回结果

**执行流程**：
1. 接收任务上下文（用户问题、历史对话）
2. 构建专属的 System Prompt
3. 调用工具完成任务
4. 返回 Final Answer（思考过程隔离）

### 3. 具体 Worker 实现

#### VetAgent（兽医诊断专家）

**专长**：
- 疾病诊断
- 用药建议
- 健康评估
- 风险预警

**System Prompt 特点**：
- 通俗化表达
- 使用表情符号
- 称呼"老乡/师傅"
- 回复极简（1-3句）

**可用工具**：暂无（基于知识库诊断）

**示例**：
```
用户: 猪不吃食，精神不好
VetAgent: 老乡，这可能是消化不良或发烧。
先量下体温，超过39.5度要打退烧针。
不吃食超过1天，联系兽医站。🩺
```

#### DataAgent（数据查询专家）

**专长**：
- 猪只列表查询
- 档案信息检索
- 生长曲线预测
- 数据统计分析

**可用工具**：
- `list_pigs`：列出猪场所有猪只
- `get_pig_info_by_id`：查询指定猪只档案
- `query_pig_growth_prediction`：生成生长曲线预测

**示例**：
```
用户: 我的猪场有哪些猪？
DataAgent: [调用 list_pigs 工具]
您的猪场目前有 12 头猪：
PIG001、PIG002、PIG003...
```

#### PerceptionAgent（视觉识别专家）

**专长**：
- 视频截图分析
- 猪只数量识别
- 现场状况评估

**可用工具**：
- `capture_pig_farm_snapshot`：截取视频并进行 YOLO 识别

**示例**：
```
用户: 看看猪场现场情况
PerceptionAgent: [调用 capture_pig_farm_snapshot 工具]
现场检测到 8 只猪，分布均匀。
未发现异常行为。📹
```

### 4. MultiAgentOrchestrator（协调器）

**职责**：统一入口，协调 Supervisor 和 Workers。

**执行流程**：
```python
orchestrator = MultiAgentOrchestrator()

context = AgentContext(
    user_id="user_123",
    user_input="我的猪拉稀了",
    chat_history=[],
    metadata={},
    client_id="user_user_123"
)

result = await orchestrator.execute(context)
# result.answer: "老乡，先停食半天，喂点蒙脱石散..."
# result.worker_name: "vet_agent"
```

## API 接口

### V2 多智能体接口

**端点**：`POST /api/v1/agent/chat/v2`

**请求**：
```json
{
  "user_id": "user_123",
  "messages": [
    {
      "role": "system",
      "content": "你是掌上明猪的智能助手"
    },
    {
      "role": "user",
      "content": "我的猪场有哪些猪？"
    }
  ],
  "metadata": {
    "channel": "web",
    "source": "frontend"
  }
}
```

**响应**：
```json
{
  "reply": "您的猪场目前有 12 头猪：PIG001、PIG002..."
}
```

### V1 单智能体接口（兼容）

**端点**：`POST /api/v1/agent/chat`

保持向后兼容，使用原有的单智能体架构。

## 配置与扩展

### 添加新 Worker

1. 继承 `WorkerAgent` 基类
2. 实现 `get_tools()` 方法
3. 定义专属 System Prompt
4. 在 `MultiAgentOrchestrator` 中注册

**示例**：
```python
class FeedAgent(WorkerAgent):
    """饲料管理专家"""
    
    def __init__(self):
        system_prompt = "你是饲料管理专家..."
        super().__init__(name="feed_agent", system_prompt=system_prompt, tools=[])
    
    def get_tools(self) -> List[LCTool]:
        return [
            # 饲料相关工具
        ]

# 注册到协调器
orchestrator.workers["feed_agent"] = FeedAgent()
```

### 修改 Supervisor 路由逻辑

**方式 1：修改 LLM Prompt**

编辑 `SUPERVISOR_PROMPT`，添加新 Worker 描述：
```python
SUPERVISOR_PROMPT = """...
可用专家：
- vet_agent: 兽医诊断...
- data_agent: 数据查询...
- perception_agent: 视觉识别...
- feed_agent: 饲料管理...  # 新增
"""
```

**方式 2：增强规则引擎**

编辑 `SupervisorAgent._rule_based_route()`：
```python
def _rule_based_route(self, user_input: str) -> str:
    text = user_input.lower()
    
    # 饲料管理关键词
    feed_keywords = ["饲料", "喂食", "配方", "营养"]
    if any(k in text for k in feed_keywords):
        return "feed_agent"
    
    # 其他规则...
```

## 调试与监控

### 1. Rich 控制台追踪

启动服务后，控制台会显示：
- Supervisor 路由决策
- Worker 启动信息
- 工具调用过程
- Final Answer

### 2. SSE 调试流

访问 `http://localhost:8000/static/debug.html`，实时查看：
- Supervisor 路由到哪个 Worker
- Worker 的思考过程
- 工具调用的输入输出

### 3. 日志记录

```python
import logging
logger = logging.getLogger("multi_agent")
logger.setLevel(logging.DEBUG)
```

## 性能优化

### 1. Worker 工具隔离

每个 Worker 只暴露必要的工具，减少 LLM 选择负担：
- VetAgent：0 个工具（纯知识库）
- DataAgent：3 个工具（数据相关）
- PerceptionAgent：1 个工具（视觉相关）

### 2. Supervisor 路由缓存

对于高频问题，可缓存路由结果：
```python
_route_cache = {}

def route(self, user_input: str) -> str:
    cache_key = user_input.lower()[:50]
    if cache_key in _route_cache:
        return _route_cache[cache_key]
    
    worker_name = self._llm_route(user_input)
    _route_cache[cache_key] = worker_name
    return worker_name
```

### 3. 并发执行（未来）

当需要多个 Worker 协作时，可并发执行：
```python
results = await asyncio.gather(
    data_agent.execute(context),
    perception_agent.execute(context)
)
```

## 故障排查

### 问题 1：Supervisor 路由错误

**症状**：用户问数据问题，却路由到 VetAgent

**排查**：
1. 检查 `SUPERVISOR_PROMPT` 是否清晰
2. 查看日志中的路由决策
3. 测试规则引擎是否正常

**解决**：
- 优化 Prompt 描述
- 增强规则引擎关键词

### 问题 2：Worker 工具调用失败

**症状**：DataAgent 无法调用 `list_pigs`

**排查**：
1. 检查工具是否正确注册
2. 查看工具返回的错误信息
3. 验证异步工具包装是否正常

**解决**：
- 确保 `get_tools()` 返回正确的 LCTool 列表
- 检查 `_run_async_tool()` 是否正常执行

### 问题 3：思考链污染

**症状**：用户看到 "Thought: ..." 等内容

**排查**：
1. 检查 `_extract_final_answer()` 是否正常
2. 查看日志中的警告信息

**解决**：
- 确保 Worker 的 `execute()` 方法调用了 `_extract_final_answer()`
- 检查 ReAct Prompt 格式是否正确

## 测试

### 单元测试

```bash
cd ai-service/tests
python test_multi_agent.py
```

### 手动测试

```bash
# 启动服务
python main.py

# 另一个终端
curl -X POST http://localhost:8000/api/v1/agent/chat/v2 \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "messages": [
      {"role": "user", "content": "我的猪场有哪些猪？"}
    ]
  }'
```

## 对比：V1 vs V2

| 特性 | V1 单智能体 | V2 多智能体 |
|-----|-----------|-----------|
| 架构 | 单一 Agent | Supervisor + Workers |
| 工具数量 | 所有工具 | 按 Worker 隔离 |
| 路由逻辑 | 关键词触发 | Supervisor 智能路由 |
| 专业性 | 通用 | 专家分工 |
| 可扩展性 | 低 | 高 |
| 调试难度 | 中 | 低（分层清晰） |

## 下一步

- [ ] 添加更多 Worker（FeedAgent、EnvironmentAgent）
- [ ] 实现 Worker 协作（多 Worker 并发）
- [ ] 优化 Supervisor 路由准确率
- [ ] 添加 Worker 性能监控
- [ ] 实现路由缓存机制
