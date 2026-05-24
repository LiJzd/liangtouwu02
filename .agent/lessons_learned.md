# 🐖 掌上明猪 - 项目本地工程记忆 (Lessons Learned)

## 📌 环境与上下文准则
- **根目录唯一原则**：本项目包含前端 (`frontend`)、后端 (`backend`) 以及 AI 服务 (`ai-service`) 三个独立子系统。
  - 所有后端/AI 服务的启动、测试和环境管理，均必须在其各自的子系统目录或根目录下以绝对路径/相对根路径清晰定位，禁止硬编码宿主机特定路径。
  - Python AI 服务 (`ai-service`) 的虚拟环境管理：在对 AI 服务进行重构或新增依赖前，必须优先确认 `venv` 虚拟环境已建立。
- **Windows 编码防御**：在 Windows 平台下运行 Python 脚本或测试时，为了防御 GBK 编码崩溃，命令行前置必须加上 `$env:PYTHONUTF8=1` pennies。

## 🚀 局域网/WSL2/NTFS 挂载盘（drvfs）物理级部署终极避坑准则（2026-05-20 新增，强制遵循）
1. **彻底摒弃 SFTP 同步大文件**：
   - **现象**：在宿主机 Windows 与远程局域网 WSL2 之间使用 Paramiko SFTP 传输文件容易在握手包阶段发生死锁挂起，导致整个 AI 执行链永远卡死。
   - **钢律**：**禁止使用 SFTP 传输任何大文件或部署包**。应在本地动态计算与远程通信的出站 IP，拉起轻量 HTTP 服务器，远程利用 `curl -sSf` 极速拖拽拉取文件，实现零死锁与几十倍的速度提升。
2. **Paramiko 异步后台进程被杀与挂起陷阱**：
   - **现象**：通过非交互式 `ssh.exec_command` 执行 `nohup ... &` 或 `setsid ... &`，由于没有 PTY 分配，且现代 Linux/WSL2 默认开启 `KillUserProcesses=yes`，一旦 Paramiko 连接关闭，后台进程将瞬间被挂断信号（SIGHUP）无声强杀；且重定向到 NTFS 挂载盘（`/mnt/c` drvfs）的文件容易因为文件锁死锁导致重定向失败而静默崩溃。
   - **钢律**：**必须通过交互式 PTY 键盘模拟拉起**！一律使用 `ssh.invoke_shell()` 交互式管道分配真实 PTY 终端，模拟人工敲击键盘将 `setsid <cmd> > log 2>&1 &` 注入，并物理睡眠 1 秒后主动 `chan.close()` detached。这可以让进程彻底挂接在 Systemd 根进程下，即使连接断开也能 100% 顽强存活。
3. **Kafka 消费者组协议冲突（Error 23）**：
   - **现象**：AI 消费者和 Java 端（或残留消费者）使用相同的消费者组 ID 接入时，由于 `aiokafka` 默认分配策略与 Java 发生冲突，会抛出 `InconsistentGroupProtocolError` 导致不断退避重试。
   - **对策**：将 Python 消费者的 `kafka_group_id` 从默认的 `pig-farm-ai-group` 修改为 **`pig-farm-ai-python-group`**，实现协议完全隔离解耦，秒速完成 Rebalance！

## 🔒 安全与隔离规约
- **租户隔离**：后端与 AI 服务之间的交互以及前端请求，必须强制携带并校验 `X-User-ID` (或 `user_id` 参数)，严格执行租户级数据隔离。
- **输入输出防护**：AI 服务的 System Prompt 必须具备防注入隔离。大模型的思考链 (Reasoning chain) 在返回给前端前，应在协议层进行过滤/剥离，不可污染最终的用户回复。
- **XSS 防御**：前端在渲染 AI 生成 of 富文本或 Markdown 时，必须引入 `DOMPurify` 进行清理。

## ⚡ 性能与高并发避坑
- **前端长列表渲染**：养殖场生猪监控数据长列表中，严禁使用重度 CSS 滤镜（如高斯模糊），改用透明背景以防止 Chrome 渲染卡顿。
- **高频操作防抖**：搜索、监控状态轮询等高频 UI 事件必须配合 `debounce` 防抖。
- **数据库事务**：多智能体交互的历史记录、设备状态更新等关键写操作，必须使用数据库事务 (`BEGIN`/`COMMIT`)，禁止非原子性的“先删后插”高并发漏洞。

## 🧪 接口与测试准则
- **Httpx 兼容性**：Python AI 服务的 API 异步测试客户端 `AsyncClient` 必须使用 `transport = httpx.ASGITransport(app=app)` 进行挂载，弃用旧版 `app` 直接传参。
- **测试路径防错**：自动化测试 (如 Playwright 模拟) 中若涉及路径输入，必须保证物理路径为纯英文，规避键盘模拟按键输入非 ASCII 字符导致的挂起异常。
- **API 相对路径**：前端所有请求在打包部署时，必须使用相对路径（如 `/api/v1/...`），由反向代理平滑接管，规避跨域 CORS 问题。
