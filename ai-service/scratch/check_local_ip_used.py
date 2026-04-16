import socket

def check_port_info(ip, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(3)
    try:
        s.connect((ip, port))
        local_addr = s.getsockname()
        print(f"[+] Connected to {ip}:{port} successfully!")
        print(f"[+] Local address used: {local_addr}")
        return True
    except Exception as e:
        print(f"[-] Failed to connect to {ip}:{port}: {e}")
        return False
    finally:
        s.close()

if __name__ == "__main__":
    check_port_info("192.168.1.64", 554)
    check_port_info("192.168.1.64", 80)
