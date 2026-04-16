import socket
import threading
import os

def check_port(ip, port, results):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.5)
    result = sock.connect_ex((ip, port))
    if result == 0:
        results.append(ip)
    sock.close()

def scan_network(network_prefix):
    print(f"[*] 正在扫描网段: {network_prefix}.0/24 ...")
    results = []
    threads = []
    for i in range(1, 255):
        ip = f"{network_prefix}.{i}"
        t = threading.TracebackType if False else threading.Thread(target=check_port, args=(ip, 8000, results)) # 8000 is Hikvision SDK port
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    return results

if __name__ == "__main__":
    # Usually 192.168.1.x
    ips = scan_network("192.168.1")
    if ips:
        print(f"[+] 发现以下设备 (Port 8000 开放):")
        for ip in ips:
            print(f"  - {ip}")
    else:
        print("[!] 未发现开放 8000 端口的设备。请确保电脑在 192.168.1.x 网段。")
