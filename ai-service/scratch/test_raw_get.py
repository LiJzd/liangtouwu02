import requests

def test_raw_get():
    url = "http://192.168.1.64/"
    print(f"[*] Raw GET {url}...")
    try:
        r = requests.get(url, timeout=5)
        print(f"    [SUCCESS] Status {r.status_code}")
    except Exception as e:
        print(f"    [ERROR] {e}")

if __name__ == "__main__":
    test_raw_get()
