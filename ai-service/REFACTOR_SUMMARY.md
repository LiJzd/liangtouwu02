# 掌上明猪 AI 服务重构总结

## 概述

本次重构将系统从单轮问答升级为多智能体自主决策系统，实现了：
- **Supervisor-Worker 多智能体架构**：智能路由 + 专家分工
- **严格输出隔离**：思考链路不污染用户回复
- **Rich 控制台追踪**：彩色格式化调试输出
- **SSE 调试流**：实时查看 Agent 内部状态
- **安全加固**：Python AI → Java API → MySQL，租户隔离

## 已完成阶段

### ✅ 阶段 1：Supervisor-Worker 多智能体架构

**新增文件**：
- `v1/logic/multi_agent_core.py`：多智能体核心实现
  - `SupervisorAgent`：意图路由（LLM + 规则引擎）
  - `WorkerAgent`：专家基类（独立 ReAct 循环）
  - `VetAgent`：兽医诊断专家
  - `DataAgent`：数据查询专家（3个工具）
  - `PerceptionAgent`：视觉识别专家（1个工具）
  - `MultiAgentOrchestrator`：协调器
- `v1/logic/multi_agent_controller.py`：V2 API 控制器
- `tests/test_multi_agent.py`：多智能体测试脚本
- `docs/MULTI_AGENT_GUIDE.md`：多智能体架构文档

**修改文件**：
- `main.py`：挂载 V2 多智能体路由
- `v1/logic/bot_agent.py`：优先使用 V2 接口，V1 兜底

**架构设计**：
```
用户请求
    ↓
SupervisorAgent (意图路由)
    ├─ LLM 路由（准确率高）
    └─ 规则引擎（兜底）
    ↓
    ├─→ VetAgent (兽医诊断)
    ├─→ DataAgent (数据查询)
    ├─→ PerceptionAgent (视觉识别)
    └─→ DirectReply (直接回复)
    ↓
返回结果
```

**核心特性**：
1. **工具隔离**：每个 Worker 只暴露必要工具，减少 LLM 选择负担
2. **专家分工**：不同领域由专门 Agent 处理，提升专业性
3. **双重路由**：LLM 路由 + 规则引擎兜底，确保稳定性
4. **独立 ReAct**：每个 Worker 独立执行 ReAct 循环，互不干扰

**API 接口**：
- V2：`POST /api/v1/agent/chat/v2`（多智能体）
- V1：`POST /api/v1/agent/chat`（单智能体，兼容）

### ✅ 阶段 3：Rich 控制台追踪（立即可见效果）

**修改文件**：
- `requirements.txt`：添加 `rich==13.7.0` 依赖
- `v1/logic/central_agent_core.py`：
  - 引入 Rich 库（Console, Panel, Text）
  - 重写 `RichTraceHandler` 类，使用彩色 Panel 显示 Agent 状态
  - 在 `_call_agent()` 中添加美化的开始/结束标记

**效果**：
- Agent 执行时控制台输出彩色格式化的推理过程
- 思考、工具调用、返回结果分别用不同颜色高亮
- 与普通日志严格区分

### ✅ 阶段 2：严格输出隔离（防止思考链污染）

**修改文件**：
- `v1/logic/central_agent_core.py`：
  - 新增 `_extract_final_answer()` 函数，使用正则提取 "Final Answer"
  - 修改 `_run_agent_once()`，强制提取干净输出
  - 思考过程仅记录到 `logger.debug()`，不返回给用户
- `v1/logic/bot_agent.py`：
  - 修改 `_postprocess_reply()`，检测并过滤思考链标记

**效果**：
- 用户回复中绝不包含 "Thought:", "Action:", "Observation:" 等标记
- 如果检测到污染，自动返回兜底回复并记录警告日志

### ✅ 阶段 4：SSE 调试流 + 极简调试网页

**新增文件**：
- `v1/logic/agent_debug_controller.py`：SSE 端点实现
  - `/api/v1/agent/debug/agent-trace`：实时推送 Agent 状态
  - 支持多客户端隔离（client_id）
  - 自动心跳包（30秒）
- `static/debug.html`：独立调试网页
  - 纯 HTML + 原生 JS，无需 Vue 框架
  - 实时显示 Agent 内部状态
  - 彩色事件分类（thought/action/observation/final_answer/error）
- `tests/test_agent_debug.py`：测试脚本
- `docs/AGENT_DEBUG_GUIDE.md`：使用文档

**修改文件**：
- `main.py`：挂载调试路由和静态文件服务
- `v1/logic/central_agent_core.py`：
  - `RichTraceHandler` 增加 SSE 事件推送
  - `_run_agent_once()` 支持 `client_id` 参数
  - `generate_reply()` 支持 `client_id` 参数
- `v1/logic/central_agent_controller.py`：
  - `/chat` 接口使用 `user_id` 作为 `client_id`

**效果**：
- 开发者可通过浏览器实时查看 Agent "内心戏"
- 支持多用户并发调试（每个用户独立队列）
- 调试流失败不影响主流程

## 核心改进

### 1. 多智能体架构（新增）

**问题**：单一 Agent 处理所有问题，工具过多导致选择困难，专业性不足。

**解决**：
- **Supervisor 路由**：智能分发到专家 Agent
- **Worker 隔离**：每个专家只暴露必要工具
- **专业分工**：兽医、数据、视觉三大专家

**效果**：
- 工具调用准确率提升（从所有工具中选 → 从 3 个工具中选）
- 回复专业性提升（专属 System Prompt）
- 可扩展性提升（新增专家无需修改现有代码）

### 2. 输出隔离机制

**问题**：原系统可能将 Agent 思考过程直接返回给用户，导致回复冗长且不专业。

**解决**：
```python
def _extract_final_answer(agent_output: str) -> str:
    """严格提取 Final Answer，丢弃所有思考过程"""
    match = re.search(r"Final Answer:\s*(.+)", agent_output, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    # 兜底逻辑...
```

### 2. 可观测性分层

```
用户层：只看结论
  ↓
开发者层：Rich 控制台 + SSE 流（思考过程）
  ↓
日志层：完整 JSON 状态
```

### 3. 防崩溃容错

- 工具调用失败时，错误作为 `Observation` 传回 LLM 重试
- SSE 推送失败不影响主流程（`try-except` 包裹）
- 队列满时自动丢弃旧事件

## 核心架构

**目标**：
- 为 AI Tool 调用设计扁平化 API
- 强制租户隔离（拦截器校验 `user_id`）
- Swagger 注解极其清晰

**新增文件**：
- `backend/liangtouwu-business/src/main/java/com/liangtouwu/business/controller/AiToolController.java`：AI Tool 专用控制器
- `backend/liangtouwu-business/src/main/java/com/liangtouwu/business/dto/ai/*.java`：8 个扁平化 DTO
- `backend/liangtouwu-business/src/main/java/com/liangtouwu/business/service/AiToolService.java`：服务接口
- `backend/liangtouwu-business/src/main/java/com/liangtouwu/business/service/impl/AiToolServiceImpl.java`：服务实现
- `backend/liangtouwu-business/src/main/java/com/liangtouwu/business/interceptor/AiToolAuthInterceptor.java`：安全拦截器
- `backend/liangtouwu-business/src/main/java/com/liangtouwu/business/config/WebMvcConfig.java`：拦截器配置

**修改文件**：
- `backend/liangtouwu-business/src/main/java/com/liangtouwu/business/mapper/PigMapper.java`：添加租户隔离方法
- `backend/liangtouwu-business/src/main/resources/mapper/PigMapper.xml`：添加租户隔离 SQL
- `backend/liangtouwu-domain/src/main/java/com/liangtouwu/domain/entity/Pig.java`：添加 `userId` 字段
- `ai-service/v1/logic/bot_tools.py`：改为调用 Java API（移除直连 MySQL）
- `ai-service/v1/logic/multi_agent_core.py`：DataAgent 新增 2 个工具

**架构改进**：
```
【旧架构 - 安全漏洞】
Python AI → MySQL 直连
  ↓
绕过租户隔离，可能越权查询

【新架构 - 安全加固】
Python AI → Java API → MySQL
  ↓
拦截器强制校验 X-User-ID
  ↓
Service 层租户隔离查询
```

**API 设计示例**：
```java
@PostMapping("/api/v1/ai-tool/pigs/list")
@Operation(summary = "列出猪只列表 (AI Tool 专用)")
public ApiResponse<PigListResponse> listPigs(
    @RequestHeader("X-User-ID") String userId,
    @RequestBody @Valid PigListRequest request
) {
    // 拦截器已校验 userId
    return ApiResponse.success(aiToolService.listPigs(userId, request));
}
```

**安全机制**：
1. **拦截器强制校验**：所有 `/api/ai-tool/**` 路径必须携带 `X-User-ID` Header
2. **Service 层隔离**：所有 SQL 查询强制带 `user_id = #{userId}` 条件
3. **双重防护**：Controller 参数校验 + Mapper 租户过滤

**Python 工具改造**：
```python
# 旧实现（直连 MySQL）
from mysql_tool import get_pig_info_by_id

# 新实现（调用 Java API）
async with httpx.AsyncClient() as client:
    response = await client.post(
        f"{JAVA_API_BASE_URL}/api/v1/ai-tool/pigs/info",
        headers={"X-User-ID": user_id},
        json={"pigId": pig_id}
    )
```

**DataAgent 工具扩展**：
- `list_pigs`：列出猪只列表
- `get_pig_info_by_id`：查询猪只档案
- `get_abnormal_pigs`：查询异常猪只（新增）
- `get_farm_stats`：猪场统计概览（新增）
- `query_pig_growth_prediction`：生长曲线预测

## 技术栈

### Python AI 层
- FastAPI：异步 Web 框架
- LangChain：ReAct Agent 框架
- Rich：控制台美化
- OpenAI SDK：调用阿里百炼（兼容模式）

### 前端调试层
- 纯 HTML + 原生 JS
- Server-Sent Events (SSE)

### Java 后端层（待改造）
- Spring Boot
- MyBatis-Plus
- Swagger/OpenAPI

## 安全机制

1. **租户隔离**：拦截器强制校验 `X-User-ID`，SQL 层面过滤 `user_id`
2. **输出过滤**：严格提取 Final Answer，过滤思考链标记
3. **防注入**：参数化查询防 SQL 注入，System Prompt 防提示词注入

## 快速开始

详见 `QUICK_START.md` 和 `DEPLOYMENT_CHECKLIST.md`

## 参考文档

- [快速启动指南](../../QUICK_START.md)
- [部署验证清单](../../DEPLOYMENT_CHECKLIST.md)
- [测试结果报告](../tests/TEST_RESULTS.md)
- [多智能体架构指南](docs/MULTI_AGENT_GUIDE.md)
- [Agent 调试指南](docs/AGENT_DEBUG_GUIDE.md)
- [API 文档](../../backend/API_DOCS.md)

