import socket
import os

def test_force_source():
    target_ip = "192.168.1.64"
    local_ip = "192.168.1.13" # 用户的局域网固定网卡 IP
    port = 554
    
    # 清理环境变量，防止 Python 内部代理干扰
    for key in ['HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'http_proxy', 'https_proxy']:
        os.environ.pop(key, None)
        
    print(f"[*] 诊断开始...")
    print(f"[*] 强制绑定本地网卡: {local_ip}")
    print(f"[*] 目标摄像机地址: {target_ip}:{port}")
    
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(10)
    try:
        # 强制从 192.168.1.13 发起连接
        s.bind((local_ip, 0))
        s.connect((target_ip, port))
        print("[SUCCESS] TCP 连接成功！链路本身没问题。")
        
        # 发送 OPTIONS 探测 RTSP 协议握手
        msg = f"OPTIONS rtsp://{target_ip}:{port} RTSP/1.0\r\nCSeq: 1\r\n\r\n"
        s.send(msg.encode())
        data = s.recv(1024)
        print(f"[SUCCESS] 收到协议响应:")
        print("-" * 20)
        print(data.decode(errors='ignore'))
        print("-" * 20)
        
    except Exception as e:
        print(f"[ERROR] 连接失败: {e}")
        print("\n[?] 可能原因:")
        print("1. 192.168.1.13 这个源 IP 被摄像头防火墙/黑名单屏蔽了。")
        print("2. 您电脑上的防火墙（Windows Defender）拦截了 Python.exe 的出站流量。")
        print("3. 摄像头禁用了 RTSP (554) 端口的协议响应，虽然端口是开着的。")
    finally:
        s.close()

if __name__ == "__main__":
    test_force_source()
