# 🐖 两头乌 (掌上明猪) - AI 项目约束规范 (CLAUDE.md)

> **⚠️ 钢律**：本项目实施极严格的双栈重构及物理隔离。AI 必须无条件遵循本约束，并**按需读取**子规范以节省 Token。

---

## 🛠️ 构建、测试与启动命令 (Build & Test Commands)

在 Windows 11 开发环境下，必须前置开启 UTF-8 编码，命令固化如下：
*   **启动 AI 服务**：`$env:PYTHONUTF8=1; .\venv\Scripts\python.exe -m ai-service.main` (在 `ai-service` 或根目录下启动)
*   **运行服务测试**：`$env:PYTHONUTF8=1; .\venv\Scripts\pytest.exe` (在测试目录下)
*   **启动 Java 后端**：`mvn clean spring-boot:run` (在 `backend` 目录下)
*   **进程清理(锁死重编前置)**：`Stop-Process -Name "进程名" -Force -ErrorAction SilentlyContinue`

---

## 🔒 渐进式开发约束指引 (Style & Guard Guidelines)

为保障高内聚低耦合，请根据您当前执行的任务，使用 `view_file` **按需读取**对应的子规范文档：

1. 🏗️ **[技术底座与开发环境约束](file:///c:/Users/lost/Desktop/两头乌/.agent/tech_stack.md)**
   - 包含：微服务架构、Python 虚拟环境 (`venv`) 准则、Windows 物理环境及类型提示向下兼容防御。
2. 🔒 **[工程律令与安全防御规约](file:///c:/Users/lost/Desktop/两头乌/.agent/engineering_rules.md)**
   - 包含：根目录唯一启动、租户物理隔离 (`X-User-ID`)、LLM 空解析物理级联回滚、前端 DOMPurify 与长列表优化。
3. 🧪 **[LangGraph重构与技术红线](file:///c:/Users/lost/Desktop/两头乌/.agent/refactor_standards.md)**
   - 包含：LangGraph 强类型节点、Pydantic V2 工具注册、Kafka 双栈异步推流、Milvus 混合 RAG、Text-to-SQL 只读沙箱。
4. 🐛 **[项目级历史痛点避坑指南](file:///c:/Users/lost/Desktop/两头乌/.agent/lessons_learned.md)**
   - 包含：WSL2/drvfs 物理部署防挂起（废弃 SFTP）、Kafka 协议冲突 (Error 23) 隔离、Httpx ASGITransport 兼容性。
5. 🤖 **[多智能体托管与技能管线](file:///c:/Users/lost/Desktop/两头乌/.agent/agents_workflow.md)**
   - 包含：Antigravity 调度大脑、Coder/Reviewer 协作、22阶段学术流水线、智能体与技能物理路径固化。

---
*规范确立版本：V1.1 (2026-05-20) | 核心准则：杜绝 Token 污染，精准按需加载。*
