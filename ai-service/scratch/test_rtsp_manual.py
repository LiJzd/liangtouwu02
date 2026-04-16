import socket
import os
import sys

def test_rtsp_handshake(ip, port=554):
    print(f"[*] 手动测试 RTSP OPTIONS 握手 (TCP)...")
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect((ip, port))
        
        # 发送简单的 OPTIONS 请求
        msg = f"OPTIONS rtsp://{ip}:{port} RTSP/1.0\r\nCSeq: 1\r\nUser-Agent: test-script\r\n\r\n"
        s.send(msg.encode())
        
        data = s.recv(1024)
        print(f"    [SUCCESS] 收到服务器响应:")
        print(f"---")
        print(data.decode(errors='ignore'))
        print(f"---")
        return True
    except Exception as e:
        print(f"    [ERROR] 握手失败: {e}")
        return False
    finally:
        s.close()

if __name__ == "__main__":
    test_rtsp_handshake("192.168.1.64")
