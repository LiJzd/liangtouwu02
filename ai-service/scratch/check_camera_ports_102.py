import socket

def check_ports(ip, ports):
    for port in ports:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        try:
            s.connect((ip, port))
            print(f"[+] Port {port} is OPEN on {ip}")
        except Exception as e:
            print(f"[-] Port {port} is CLOSED on {ip}: {e}")
        finally:
            s.close()

if __name__ == "__main__":
    check_ports("192.168.1.102", [80, 554, 8000, 37777])
