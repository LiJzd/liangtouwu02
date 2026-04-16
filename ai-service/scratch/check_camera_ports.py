import socket

def check_port(ip, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    try:
        s.connect((ip, port))
        print(f"[+] Port {port} is OPEN on {ip}")
        return True
    except Exception as e:
        print(f"[-] Port {port} is CLOSED or unreachable on {ip}: {e}")
        return False
    finally:
        s.close()

if __name__ == "__main__":
    check_port("192.168.1.64", 554)
    check_port("192.168.1.64", 80)
    check_port("192.168.1.64", 8000)
