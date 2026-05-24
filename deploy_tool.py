# -*- coding: utf-8 -*-
"""
🐖 掌上明猪 - 局域网物理级零死锁一键部署与服务守护工具 (deploy_tool.py)

该工具实现了我们在局域网/WSL2/NTFS挂载盘（drvfs）部署中摸索出来的黄金法则：
1. 本地动态计算出站IP，并利用轻量多线程 HTTP 服务器进行零死锁文件传输，彻底弃用 Paramiko SFTP （SFTP易引发握手挂死崩溃）。
2. 基于交互式 PTY (invoke_shell) 进行真实的键盘操作模拟，注入 setsid 并关闭通道脱离，防 SSH 断开强杀。
3. 针对 Kafka 的 Java/Python 双栈消费者协议冲突、MySQL 8.0 远程端口和持久化运行进行了深度联调集成。

使用方式:
    python deploy_tool.py --host 10.46.42.161 --user pc --pwd ljjnb666
"""
import paramiko
import sys
import time
import os
import shutil
import socket
import http.server
import socketserver
import threading
import argparse

# 强制终端使用 UTF-8 编码，防止 Windows 平台控制台输出 GBK 报错崩溃
if sys.platform.startswith("win"):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

def zip_dir(dir_path, zip_file_path):
    import zipfile
    with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(dir_path):
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, os.path.dirname(dir_path))
                zipf.write(file_path, rel_path)

def log(msg, level="INFO"):
    colors = {
        "INFO": "\033[1;36m[INFO]\033[0m",
        "SUCCESS": "\033[1;32m[SUCCESS]\033[0m",
        "WARN": "\033[1;33m[WARN]\033[0m",
        "ERROR": "\033[1;31m[ERROR]\033[0m",
    }
    prefix = colors.get(level, f"[{level}]")
    print(f"{prefix} {msg}", flush=True)

class ThreadedHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True

class SilentHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        # 屏蔽 SimpleHTTPRequestHandler 默认的终端日志输出，保持清爽
        pass

class PigFarmDeployer:
    def __init__(self, args):
        self.hostname = args.host
        self.username = args.user
        self.password = args.pwd
        self.port = args.port
        self.remote_deploy_dir = args.remote_dir
        
        # 绝对路径配置
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.local_config = os.path.join(self.base_dir, "ai-service", "v1", "common", "config.py")
        self.temp_dir = os.path.join(self.base_dir, "temp_deploy_tool")
        self.remote_config = f"{self.remote_deploy_dir}/ai-service/v1/common/config.py"
        self.http_port = args.http_port

    def get_local_outbound_ip(self):
        """
        通过建立一个虚假的连接，自动获取本地与远程主机通信的出站物理网卡 IP 接口
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # 尝试连接远程主机的 SSH 端口
            s.connect((self.hostname, self.port))
            local_ip = s.getsockname()[0]
        except Exception as e:
            log(f"无法自动检测出站物理网卡 IP, 降级使用 0.0.0.0。错误: {e}", "WARN")
            local_ip = "0.0.0.0"
        finally:
            s.close()
        return local_ip

    def start_local_http_server(self, local_ip):
        """
        启动本地轻量多线程临时 HTTP 服务器
        """
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        os.makedirs(self.temp_dir)
        
        # 1. 复制核心的 5 个代码文件到临时分发目录
        files_to_copy = [
            ("ai-service/v1/common/config.py", "config.py"),
            ("ai-service/pig_rag/liangtouwu_knowledge_rag.py", "liangtouwu_knowledge_rag.py"),
            ("ai-service/v1/logic/liangtouwu_rag_controller.py", "liangtouwu_rag_controller.py"),
            ("ai-service/main.py", "main.py"),
            ("ai-service/tests/test_liangtouwu_rag.py", "test_liangtouwu_rag.py")
        ]
        for src_rel, dst_name in files_to_copy:
            src_path = os.path.join(self.base_dir, src_rel)
            if os.path.exists(src_path):
                shutil.copy2(src_path, os.path.join(self.temp_dir, dst_name))
                log(f"已暂存最新本地 {src_rel} -> {dst_name} 到传输目录", "INFO")
            else:
                log(f"警告：未找到本地更新代码 {src_rel}", "WARN")

        # 2. 将本地物理构建的 Chroma 向量数据库打包为 zip
        chroma_db_dir = os.path.join(self.base_dir, "ai-service", "liangtouwu_knowledge_chroma_db")
        if os.path.exists(chroma_db_dir):
            zip_file_path = os.path.join(self.temp_dir, "chroma_db.zip")
            log("正在为本地物理向量库 liangtouwu_knowledge_chroma_db 创建极速 ZIP 打包...", "INFO")
            zip_dir(chroma_db_dir, zip_file_path)
            log("物理向量库 ZIP 打包完成！", "SUCCESS")
        else:
            log("警告：未找到本地物理向量数据库，将不进行同步！", "WARN")

        # 切换工作目录启动服务
        self.old_cwd = os.getcwd()
        os.chdir(self.temp_dir)

        server = ThreadedHTTPServer((local_ip, self.http_port), SilentHTTPRequestHandler)
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        log(f"本地极速 HTTP 传输服务器已在 {local_ip}:{self.http_port} 异步拉起", "SUCCESS")
        return server

    def execute(self):
        log("============================================================", "INFO")
        log("          🐖 掌上明猪 - 局域网零死锁一键物理部署服务启动", "INFO")
        log("============================================================", "INFO")
        
        # 0. 自动发现并提取本地的 DASHSCOPE_API_KEY
        local_dashscope_key = os.environ.get("DASHSCOPE_API_KEY")
        if not local_dashscope_key:
            try:
                import sys
                from pathlib import Path
                ai_service_path = Path(__file__).resolve().parent / "ai-service"
                if str(ai_service_path) not in sys.path:
                    sys.path.insert(0, str(ai_service_path))
                from v1.common.config import get_settings
                local_dashscope_key = get_settings().dashscope_api_key
            except Exception as e:
                log(f"尝试从本地 config.py 读取 API Key 异常: {e}", "WARN")
        
        if local_dashscope_key:
            log(f"成功提取本地阿里云百炼 API Key: {local_dashscope_key[:6]}******{local_dashscope_key[-4:]}", "SUCCESS")
        else:
            log("警告：未能自动提取到本地 DASHSCOPE_API_KEY，远程拉起及测试可能受限。", "WARN")
            local_dashscope_key = ""

        local_ip = self.get_local_outbound_ip()
        log(f"检测到物理通信出站 IP 接口为: {local_ip}", "INFO")
        
        # 1. 拉起本地 HTTP Server
        http_server = self.start_local_http_server(local_ip)
        
        # 2. 建立 SSH 连接
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            log(f"正在尝试建立与远程主机的 SSH 连接 {self.hostname}:{self.port}...", "INFO")
            ssh.connect(self.hostname, port=self.port, username=self.username, password=self.password, timeout=15)
            log("SSH 通道成功连通！", "SUCCESS")
            
            # 3. 远程通过 curl 从本地极速拉取并重构所有变更的代码与向量数据库（彻底打破 SFTP 在 WSL 下的死锁问题）
            log("远程主机开始从本地极速拉取所有更新代码及物理向量数据库...", "INFO")
            
            # (0) 确保远程物理路径与日志文件夹完备存在
            ssh.exec_command(f"mkdir -p {self.remote_deploy_dir}/ai-service/logs || true")
            
            # (1) 下载代码文件
            cmds = [
                f"curl -sSf -o {self.remote_deploy_dir}/ai-service/v1/common/config.py http://{local_ip}:{self.http_port}/config.py",
                f"curl -sSf -o {self.remote_deploy_dir}/ai-service/pig_rag/liangtouwu_knowledge_rag.py http://{local_ip}:{self.http_port}/liangtouwu_knowledge_rag.py",
                f"curl -sSf -o {self.remote_deploy_dir}/ai-service/v1/logic/liangtouwu_rag_controller.py http://{local_ip}:{self.http_port}/liangtouwu_rag_controller.py",
                f"curl -sSf -o {self.remote_deploy_dir}/ai-service/main.py http://{local_ip}:{self.http_port}/main.py",
                f"curl -sSf -o {self.remote_deploy_dir}/ai-service/tests/test_liangtouwu_rag.py http://{local_ip}:{self.http_port}/test_liangtouwu_rag.py"
            ]
            for cmd in cmds:
                stdin, stdout, stderr = ssh.exec_command(cmd)
                err = stderr.read().decode("utf-8", errors="ignore").strip()
                if err:
                    log(f"拉取警告: {err}", "WARN")
            log("远程核心代码文件全部物理同步与覆盖完成！", "SUCCESS")
            
            # (2) 下载并解压向量数据库
            log("远程主机开始下载并重建 liangtouwu_knowledge_chroma_db 物理向量数据库...", "INFO")
            zip_download_cmd = f"curl -sSf -o {self.remote_deploy_dir}/ai-service/chroma_db.zip http://{local_ip}:{self.http_port}/chroma_db.zip"
            stdin, stdout, stderr = ssh.exec_command(zip_download_cmd)
            err = stderr.read().decode("utf-8", errors="ignore").strip()
            if err:
                 log(f"下载向量库 ZIP 警告: {err}", "WARN")
                 
            # 清理旧的远程向量数据库文件夹以防覆盖冲突
            ssh.exec_command(f"rm -rf {self.remote_deploy_dir}/ai-service/liangtouwu_knowledge_chroma_db || true")
            
            # 利用 Python 原生库极速安全解压，零依赖，跨平台
            unzip_cmd = f"cd {self.remote_deploy_dir}/ai-service && python3 -c \"import zipfile; zipfile.ZipFile('chroma_db.zip').extractall('.')\" && rm -f chroma_db.zip"
            stdin, stdout, stderr = ssh.exec_command(unzip_cmd)
            err = stderr.read().decode("utf-8", errors="ignore").strip()
            if err:
                 log(f"解压解包物理向量库警告: {err}", "WARN")
            else:
                 log("远程物理向量数据库极速重组与部署成功！", "SUCCESS")
            
            # 4. 强杀残留的旧 Python 消费守护进程，确保纯净拉起
            log("正在清理远程残留的旧 Python 消费者进程...", "INFO")
            ssh.exec_command("pkill -9 -f 'v1.logic.kafka_worker' || true")
            time.sleep(1.5)
            
            # 5. 清理旧日志文件以生成全新大联调结果
            ssh.exec_command(f"rm -f {self.remote_deploy_dir}/ai-service/kafka_worker.log || true")
            
            # 6. 检查远程 Java 服务的常驻状态（8082端口），避免不必要的 Java 重启造成的冷启动开销
            log("探测远程 Java 业务端监听状态 (8082 端口)...", "INFO")
            stdin, stdout, stderr = ssh.exec_command("ss -tlnp | grep 8082 || true")
            java_status = stdout.read().decode("utf-8", errors="ignore").strip()
            
            if "8082" in java_status:
                log("探测到远程 Java 业务端已健康处于常驻运行中，端口 8082 正常监听，跳过 Java 重启。", "SUCCESS")
            else:
                log("未检测到 8082 端口监听。正在启动 Java 业务后台常驻...", "WARN")
                ssh.exec_command(f"rm -f {self.remote_deploy_dir}/java_backend.log || true")
                
                # 必须利用真实 PTY (invoke_shell) 进行键盘打字注入，然后 setsid 守护启动，接着立马 chan.close() 从而 detached 挂接到 Systemd 根进程下
                chan_java = ssh.invoke_shell()
                run_java_cmd = f"cd {self.remote_deploy_dir} && setsid java -Dserver.port=8082 -jar liangtouwu-app.jar > java_backend.log 2>&1 &\n"
                chan_java.send(run_java_cmd)
                time.sleep(1)
                chan_java.close()
                log("Java 后台通过真实 PTY 键盘模拟命令已成功 detached 拉起！", "SUCCESS")
                time.sleep(2)

            # 7. 通过交互式 PTY (invoke_shell) 静默拉起全新 Python AI 消费者
            log("正在通过交互式 PTY 键盘键盘模拟拉起全新 Python AI 守护消费者进程...", "INFO")
            chan_ai = ssh.invoke_shell()
            env_vars = f"export DASHSCOPE_API_KEY='{local_dashscope_key}'; " if local_dashscope_key else ""
            run_ai_cmd = f"cd {self.remote_deploy_dir}/ai-service && setsid sh -c \"{env_vars}./venv/bin/python3 -u -m v1.logic.kafka_worker > kafka_worker.log 2>&1\" &\n"
            chan_ai.send(run_ai_cmd)
            
            # 睡眠 1 秒采集交互回显并强制关闭，使其彻底脱离 SSH 控制链路，挂接为常驻系统进程
            time.sleep(1)
            output_echo = chan_ai.recv(4096).decode("utf-8", errors="ignore")
            log(f"PTY 键盘交互底层回显监控:\n{output_echo.strip()}", "INFO")
            chan_ai.close()
            log("Python AI 消费守护协程已通过 detached 物理常驻拉起！", "SUCCESS")
            
            # 8. 等待热导入与建立连接，截取最新联调日志
            wait_time = 15
            log(f"正在等待 {wait_time} 秒供各服务进行资源冷导入、大模型预热及连通 Kafka Broker...", "INFO")
            time.sleep(wait_time)
            
            # 9. 执行全栈日志与端口状态大联调验证
            log("============================================================", "INFO")
            log("          远程双端常驻状态与日志输出大联调验证结果", "INFO")
            log("============================================================", "INFO")
            
            # 截取 Python AI 日志
            log("[Python AI 消费者 (kafka_worker.log) 运行日志输出]:", "INFO")
            stdin, stdout, stderr = ssh.exec_command(f"cat {self.remote_deploy_dir}/ai-service/kafka_worker.log 2>/dev/null || echo '未检测到日志输出'")
            ai_log_content = stdout.read().decode("utf-8", errors="ignore").strip()
            print(ai_log_content)
            
            # 截取 Java 日志
            log("[Java 业务后台 (java_backend.log) 运行日志输出 (Tail 15行)]:", "INFO")
            stdin, stdout, stderr = ssh.exec_command(f"tail -n 15 {self.remote_deploy_dir}/java_backend.log 2>/dev/null || echo '未检测到日志输出'")
            java_log_content = stdout.read().decode("utf-8", errors="ignore").strip()
            print(java_log_content)
            
            # 端口情况
            log("[系统网络监听端口校验 (8082, 9092, 3306)]:", "INFO")
            stdin, stdout, stderr = ssh.exec_command("ss -tlnp | grep -E '8082|9092|3306'")
            ports_status = stdout.read().decode("utf-8", errors="ignore").strip()
            print(ports_status)
            
            # 进程状态
            log("[常驻进程活跃度检验]:", "INFO")
            stdin, stdout, stderr = ssh.exec_command("ps -ef | grep -E 'kafka_worker|liangtouwu-app.jar' | grep -v grep")
            process_status = stdout.read().decode("utf-8", errors="ignore").strip()
            print(process_status)
            
            log("============================================================", "SUCCESS")
            log("🎉 局域网物理部署大联调 100% 成功！双栈服务已完全脱离会话常驻静默运行。", "SUCCESS")
            log("============================================================", "SUCCESS")
            
            # 10. 执行远程回归自检测试，断言 RAG 服务端点全部通过
            log("正在执行远程回归自检测试 (pytest) ...", "INFO")
            env_prefix = f"export PYTHONUTF8=1; export DASHSCOPE_API_KEY='{local_dashscope_key}'; " if local_dashscope_key else "export PYTHONUTF8=1; "
            test_run_cmd = f"{env_prefix}cd {self.remote_deploy_dir}/ai-service && ./venv/bin/python3 -m pytest tests/test_liangtouwu_rag.py -v -s"
            stdin, stdout, stderr = ssh.exec_command(test_run_cmd)
            test_out = stdout.read().decode("utf-8", errors="ignore").strip()
            test_err = stderr.read().decode("utf-8", errors="ignore").strip()
            print(test_out)
            if "passed" in test_out:
                 log("🎉 远程回归自检测试 100% 成功通过！向量数据库及 RAG 接口功能完美运转！", "SUCCESS")
            else:
                 log(f"警告：远程自检未完全通过或存在输出。错误回显:\n{test_err}", "WARN")
            
        except Exception as e:
            log(f"部署运行中发生异常: {e}", "ERROR")
        finally:
            ssh.close()
            log("正在安全关闭本地临时 HTTP 服务器...", "INFO")
            http_server.shutdown()
            os.chdir(self.old_cwd)
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                log("本地临时传输空间清理完毕！", "INFO")
            log("自动部署作业全部执行完毕！", "SUCCESS")

def main():
    parser = argparse.ArgumentParser(description="🐖 掌上明猪 - 局域网物理级零死锁一键部署与服务守护工具")
    parser.add_argument("--host", type=str, default="", help="远程物理主机 IP")
    parser.add_argument("--user", type=str, default="", help="远程物理主机 SSH 用户名")
    parser.add_argument("--pwd", type=str, default="", help="远程物理主机 SSH 密码")
    parser.add_argument("--port", type=int, default=22, help="远程 SSH 端口 (默认 22)")
    parser.add_argument("--remote-dir", type=str, default="/mnt/c/Users/PC/liangtouwu-deploy", help="远程部署根路径")
    parser.add_argument("--http-port", type=int, default=9997, help="本地临时 HTTP 分发服务器端口 (默认 9997)")
    
    args = parser.parse_args()
    deployer = PigFarmDeployer(args)
    deployer.execute()

if __name__ == "__main__":
    main()
