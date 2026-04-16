import requests
from requests.auth import HTTPDigestAuth

def check_hikvision_api():
    ip = "192.168.1.64"
    user = "admin"
    password = "jhc20260414"
    
    urls = [
        f"http://{ip}/ISAPI/System/deviceInfo",
        f"http://{ip}/ISAPI/Streaming/channels"
    ]
    
    for url in urls:
        print(f"[*] Checking: {url}")
        try:
            # Try Digest Auth (Standard for Hikvision)
            response = requests.get(url, auth=HTTPDigestAuth(user, password), timeout=5)
            if response.status_code == 200:
                print(f"    [SUCCESS] Status 200. Credentials are CORRECT.")
                print(f"    [INFO] Content: {response.text[:200]}...")
                return True
            else:
                print(f"    [WARN] Status {response.status_code}. Content: {response.text}")
                
            # Try Basic Auth (Optional for some models)
            response = requests.get(url, auth=(user, password), timeout=5)
            if response.status_code == 200:
                print(f"    [SUCCESS] Status 200 (Basic Auth). Credentials are CORRECT.")
                return True
        except Exception as e:
            print(f"    [ERROR] Connection failed: {e}")
            
    return False

if __name__ == "__main__":
    check_hikvision_api()
