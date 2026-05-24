# 🤖 两头乌项目 - 多智能体托管工作流规范 (Agents & Workflow)

> **注意**：本文件定义了多智能体协同开发、学术协作以及常驻技能管线的核心调度与物理路径规范。

---

## 1. 双核协同编码闭环 (Coder & Reviewer Flow)
在执行重大重构与代码修改时，系统一律采用**极松耦合的双智能体防污染闭环**：
*   **调度大脑 (orchestrator.md)**：作为全局中控，负责宏观任务的子集拆解、分配与 Fail-Retry 状态机闭环控制。
*   **构建核心 (coder.md) & 评审核心 (reviewer.md)**：
    *   两端通过独立的无污染实例运行，严禁共享内部运行时上下文。
    *   必须通过约定的物理中转文件实现松耦合通信，遵循“代码生成 -> 静态审查 -> 编译测试 -> 反馈重构 -> 最终一致性物理校验”的闭环，防范单体 LLM 产生“过度自信”而遗漏边界情况。

---

## 2. 论文写作多管线流水线 (Academic Paper Pipeline)
*   **22个智能体管线协作架构**：系统内置了一套覆盖需求分析、框架设计、文献检索、分学科写作（数模/CS/历史）、最终一致性验证、格式自动化检查的 22 阶段学术协作管线。
*   **任务编织原则**：在承接大型论文撰写、大纲设计、论证扩展时，主智能体将直接读取对应物理路径下的专职提示词文件，动态编织子智能体团队，并行完成多维度的学术流水线作业。
*   **历史因果一致性**：在实现分支推演时，必须通过“溯源历史链”将父节点的所有事件日志作为 Context 喂给 LLM，保证历史逻辑和因果一致性。

---

## 3. 智能体与通用生产力技能物理路径 (Stateless Assets)
为了保证各微服务在多机器或 Windows/WSL2 双栈环境下能 100% 成功调用内置智能体与高级技能，其物理路径固化如下：

### 📂 多智能体提示词路径
*   **路径**：[C:\Users\lost\.antigravity\agents\ ](file:///C:/Users/lost/.antigravity/agents/)
*   **核心配置**：`orchestrator.md`（调度大脑）、`coder.md`（编码核心）、`reviewer.md`（审查核心）。

### 🛠️ 通用生产力技能路径
*   **路径**：[C:\Users\lost\.antigravity\skills\ ](file:///C:/Users/lost/.antigravity/skills/)
*   **内置模块**：
    *   `code-review.md` (代码评审规范) | `code-standards.md` (代码标准)
    *   `memory-manager.md` (工程记忆管理) | `task-breakdown.md` (任务拆解)
    *   `word-document-processor` (Word深度解析器) | `literature-search` (文献检索)

### 🌿 自然系列顶级学术技能套件 (Nature Skills)
*   **路径**：[C:\Users\lost\.antigravity\skills\nature-skills\ ](file:///C:/Users/lost/.antigravity/skills/nature-skills/)
*   **特种学术模块**：
    *   `nature-academic-search`（顶刊文献检索） | `nature-citation`（高标准引用）
    *   `nature-data`（数据挖掘与高级图表） | `nature-figure`（Nature级论文配图）
    *   `nature-polishing`（Nature级精修润色） | `nature-reader`（精细化论文深度研析）
    *   `nature-response`（审稿意见完美答复） | `nature-writing`（Nature级规范写作）
    *   `nature-paper2ppt`（高阶论文快速转 PPT）
