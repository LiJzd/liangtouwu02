# 🏗️ 两头乌项目 - 技术底座与开发环境规范 (Tech Stack & Environment)

> **注意**：本文件是 AI 处理环境搭建、多端调试、依赖引入及 Windows 物理层兼容时的行为红线。

---

## 1. 系统微服务技术栈 (Microservices Stack)
本项目由三个核心子系统组成，遵循异构解耦开发原则：
*   **后端网关 (backend)**：基于 Java 生态，作为核心业务流转、物联传感器消息路由以及 SSE 推流网关。
*   **人工智能服务 (ai-service)**：基于 Python 生态。核心技术栈为：**FastAPI + Pydantic (V2) + Uvicorn**。
*   **前端展示层 (frontend)**：极简轻量，基于 HTML5 + Vanilla JS (原生 CSS / CDN 挂载)；为防止渲染进程卡顿，严禁滥用 Tailwind CSS 及重度高斯模糊等特效。
*   **时序与向量检索**：基于 Milvus 分布式向量数据库与 MySQL 物理只读隔离沙箱。

---

## 2. Python 虚拟环境与依赖管理 (Venv & Dependencies)
*   **环境先行钢律**：任何新项目初始化或对 `ai-service` 进行依赖重构前，**第一步必须是 `python -m venv venv`** 并确认虚拟环境状态。
*   **类型提示兼容规范**：在开发核心底层库或高兼容性模块时，**类型提示统一从 `typing` 导入大写 `Tuple`、`List`、`Dict` 等，并在代码中使用大写声明（如 `Tuple[bool, str]`）**。
    > [!WARNING]
    > 严禁直接使用 Python 3.9+ 的小写 `tuple` / `list` 等做泛型标注（例如 `from typing import tuple`），以防御低版本运行环境下抛出 `ImportError` 导致服务收集崩溃。

---

## 3. Windows 物理环境与编码防御 (Windows Compatibility & Encoding)

针对 Windows 11 开发宿主机，必须贯彻以下物理级兼容防御，防止系统进程锁死或编码解析异常：

### 📥 命令行 UTF-8 编码锁定
*   在所有 Windows 环境下的 `run_command` 任务中，如果涉及文本打印、日志输出或启动服务，**前置命令必须强制加上 `$env:PYTHONUTF8=1`**，例如：
    ```powershell
    $env:PYTHONUTF8=1; python main.py
    ```
*   Python 的所有 `open()` 函数及文件读写操作，必须显式声明 `encoding="utf-8"` 或 `encoding="utf-8-sig"` (防御带 BOM 配置文件解码报错)。

### ⌨️ Playwright 自动化测试非 ASCII 路径兼容
*   **现象**：使用 Playwright 键盘按键模拟工具向文件浏览器输入包含中文（如“生猪监控”）的绝对路径时，会抛出 `playwright: Unknown key` 错误挂起。
*   **对策**：在测试或自动上传流程中，**一律将测试资产搬运至纯英文物理路径**，确保键盘模拟按键指令的绝对兼容性与高成功率。

### 🔒 常驻进程锁与 Spec 相对路径 (WinError 5 防御)
*   **静默后台进程清理**：在进行 Windows 常驻/隐藏后台服务打包（如 PyInstaller）或物理覆盖 `.exe` 前，**必须前置引入物理进程清理指令**，例如：
    ```powershell
    Stop-Process -Name "进程名" -Force -ErrorAction SilentlyContinue
    ```
    强行释放文件锁，彻底防御 `PermissionError: [WinError 5] 拒绝访问` 编译报错。
*   **Spec 相对化**：PyInstaller `.spec` 文件中**严禁硬编码绝对路径**。一致采用主入口相对路径（如 `['shutdown_assistant.py']`），保障项目在多开发环境与多用户下的无缝迁移。
