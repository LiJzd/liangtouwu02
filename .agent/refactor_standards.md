# 🐖 掌上明猪多智能体系统 - 终极重构编码规范与约束文件 (Refactor Standards)

> **核心诫律**：本文件是本项目全局重构与后续功能开发的**最高技术红线**。无论后续由何种 AI 智能体或开发人员承接编码，必须无条件遵循本规范中的所有硬性约束，违者视为开发失败！

---

## 🏛️ 规约一： LangGraph 图网络与节点开发约束 (LangGraph Constraints)

所有智能体逻辑必须脱离 LangChain Blackbox，全面拥抱 **LangGraph** 状态图计算网络。

### 1. 状态空间 (State Definition) 强类型约束
*   图的状态空间必须声明为强类型的 `TypedDict` 或 `Pydantic` 结构，且包含如下标准控制字：
    ```python
    from typing import TypedDict, Annotated, Sequence
    from langchain_core.messages import BaseMessage
    
    class AgentState(TypedDict):
        messages: Annotated[Sequence[BaseMessage], add_messages]  # 消息流轨迹 (自动追加)
        current_agent: str                                         # 当前执行的智能体标识
        schema_metadata: dict                                      # 数据库表元数据 (Text-to-SQL 用)
        query_context: dict                                        # RAG 召回与上下文暂存区
        errors: list[dict]                                         # 运行期错误轨迹记录 (安全审计用)
    ```
*   **严禁** 在 Node 节点内部直接更改全局可变变量，所有状态变更必须且只能通过 Node 的 `return` 结构化 Dict，由 LangGraph 的 State Manager 进行原子合并。

### 2. 节点 (Node) 纯函数化约束
*   每一个图节点（Node）都必须是一个**无状态的（Stateless）纯异步函数**：
    ```python
    async def expert_veterinary_node(state: AgentState) -> dict:
        # 1. 从 state 中只读获取参数与上下文
        # 2. 调用大模型或执行工具
        # 3. 通过 return 返回新的状态增量，严禁向外抛出未捕获异常
        return {"messages": [AIMessage(content="...")], "current_agent": "veterinary"}
    ```
*   **路由决策 (Conditional Edges)**：图的分支跳转必须定义显式的条件路由函数，禁止在 Node 节点内部强行修改执行流。
*   **异常防御 (Fallback)**：每一个大模型调用节点和工具执行节点，都必须通过 `on_error` 分支或 try-catch 拦截，降级路由至本地规则兜底节点，严禁整个图运行死锁或异常中断。

---

## 🛠️ 规约二： 智能体工具强类型注册与沙箱执行约束 (Tool Constraints)

彻底废弃单体文件 `bot_tools.py` 内部杂乱的手动字符串切割与解析逻辑。

### 1. 强类型入参 (Pydantic Schema) 约束
*   所有新开发或重构的工具，其入参必须通过 Pydantic (V2) BaseModel 进行声明，严禁接收无结构化的裸字符串：
    ```python
    from pydantic import BaseModel, Field
    
    class ListPigsInput(BaseModel):
        limit: int = Field(default=10, description="限制返回生猪条数，必须为正整数")
        abnormal_only: bool = Field(default=False, description="是否仅过滤健康状态异常的生猪")
    ```
*   定义工具时，必须绑定强类型声明，使大模型执行 Tool Calling 时能精准感知参数类型、约束与描述，极大降低幻觉率。

### 2. 沙箱安全与异常屏蔽规约
*   所有暴露给智能体调用的底层工具函数，必须在其外层挂载**异常安全装饰器**：
    ```python
    import functools
    
    def safe_tool_sandbox(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as exc:
                # 屏蔽异常，返回大模型可读并理解的 JSON 错误提示
                return f'{{"status": "error", "message": "工具调用故障：{str(exc)}，已自动降级处理"}}'
        return wrapper
    ```
*   **写操作与高并发事务约束**：凡涉及生猪数据写入、物联网状态写操作的工具，在底层操作 MySQL 时必须强制包裹事务，严禁使用非原子操作。

---

## ⚡ 规约三： Kafka 双栈异构异步推流规约 (MQ Constraints)

微服务之间的长耗时大模型推理，必须由阻塞 HTTP 升级为高可用 Kafka 消息队列解耦异步推流。

### 1. 协议通道解耦约束
*   **请求上行 (Request Queue)**：Java 后端网关在接收到前端发送的生猪咨询/监控请求后，必须仅执行“参数轻量校验”，将任务打包为 JSON 消息发布至 Kafka 主题 `liangtouwu-agent-requests`，并立即向前端返回 HTTP 202 (Accepted) 以及唯一的 `task_id`。
*   **推理执行 (AI Worker)**：Python FastAPI 作为常驻 Worker，基于 `aiokafka` 异步监听该队列，单次拉取任务，驱动 LangGraph 进行推理。
*   **推流下行 (Pushing Stream)**：
  - Python 服务在 LangGraph 计算流中，每产生一段流式 Token（打字机效果），必须立即发布至 Kafka 主题 `liangtouwu-agent-responses`，消息体需包含 `task_id`、`token` 以及是否结束标识 `is_finished`。
  - Java 后端订阅该主题，提取消息后，利用 `SseEmitter` (SSE) 或 WebSocket 物理通道实时、非阻塞地将 Token 推送至前端页面渲染。

---

## 🔍 规约四： Milvus 混合 RAG 双路召回与融合重排约束 (RAG Constraints)

彻底放弃单路 ChromaDB 稠密匹配，全面升级为分布式 Milvus + 稀疏关键词双路高精准召回。

### 1. 混合检索双通路架构 (Hybrid Search Channel)
*   **通路一 (Milvus Dense)**：利用 `pymilvus` 对文本分片抽取的高维语义向量（如 text-embedding-v2）在 Milvus 中进行 ANN 相似度检索，获取基于语义相似性的 Top-K 候选集。
*   **通路二 (BM25 Sparse)**：利用 `rank_bm25` 对相同的分片文本构建本地稀疏关键词索引库，获取基于硬性词频匹配的 Top-K 候选集。

### 2. 混合融合重排与缩编 (RFF & Reranker)
*   双路召回的候选列表，必须首先通过 **RRF (Reciprocal Rank Fusion)** 算法计算融合得分，融合得分公式硬性要求为：
    $$RRF\_Score(d) = \sum_{m \in M} \frac{1}{k + r_m(d)}$$
    （其中硬参数常数设定为 $k=60$，避免长尾偏差）。
*   融合后的前 10 个候选分片，必须调用统一的 `BGE-Reranker`（通过本地加载或模型服务 API）进行精细重排分数校准，截取最高的前 3~5 个事实分片喂给大模型 Context，确保严谨性。

---

## 🔒 规约五： Text-to-SQL 隔离沙箱约束 (SQL Sandbox Constraints)

允许大模型基于 Schema Metadata 自行拼装 SQL 以应对高弹性的养殖时序数据查询，但必须建立极度苛刻的安全沙箱。

### 1. 物理只读连接约束
*   Text-to-SQL 执行时底层的数据库连接，**必须且只能**采用物理隔离的**只读 MySQL 账户**（该账户在 MySQL 侧仅被授予特定表的 `SELECT` 权限，物理屏蔽 `INSERT`, `UPDATE`, `DELETE`, `DROP` 等操作）。

### 2. 语法静态防火墙约束
*   在执行大模型写出的 SQL 语句前，必须通过代码层面的正则表达式和静态解析器（如 `sqlparse` 或 ast）进行前置强力校验，凡是包含 `;` (防多语句注入)、`UNION`、`join` 到系统核心表、或者非 `SELECT` 起头的 SQL，必须**直接拦截并物理丢弃**，向大模型及前端抛出沙箱阻断异常。
*   **Schema 注入防护**：Pydantic 元数据下发引擎仅限下发 `pig_info`, `env_status` 等时序传感器与基本猪只信息表的 Schema，系统配置表、账号表 Schema 物理禁止泄露给大模型。

---

## 💻 规约六： Windows 物理兼容与编码防御准则 (Env Constraints)

针对 Windows 11 开发宿主机，必须贯彻以下物理兼容性策略以防御系统级崩溃：

1.  **命令行打印 UTF-8 锁定**：
    *   在任何脚本、测试调用或通过命令执行终端启动服务时，前置语句必须强制开启：
        ```powershell
        $env:PYTHONUTF8=1
        ```
    *   Python 的所有 `open()` 函数及文件读写操作，必须显式声明 `encoding="utf-8"` 或 `encoding="utf-8-sig"` (防御带 BOM 配置文件解码报错)。
2.  **绝对路径与环境纯净度**：
    *   在 Windows 平台下，任何自动化脚本在调用 Playwright 或文件物理移动时，路径中严禁包含中文，必须将资产置于纯英文物理路径下，防止键盘模拟按键输入非 ASCII 字符导致挂起。
    *   始终以项目根目录为唯一的执行上下文，禁止硬编码 Windows 的盘符路径（如 `C:\Users\lost\...`）。

---

*规范确立时间：2026-05-20 - 由 Antigravity 架构师及用户联署商议确立，后续所有开发和阶段自检必须严格对照本规范文件执行。*
