import requests
import json
import sys

def test_iot_api():
    base_url = "http://localhost:8000/api/v1/iot"
    
    print("\n" + "="*50)
    print("两头乌 IOT 模块集成测试")
    print("="*50)

    # 1. 检查健康状况
    try:
        health = requests.get("http://localhost:8000/health", timeout=2)
        if health.status_code == 200:
            print("[INFO] AI 服务正在运行")
        else:
            print(f"[ERROR] AI 服务响应异常: {health.status_code}")
            return
    except Exception:
        print("[ERROR] 无法连接到 AI 服务。请先运行: cd ai-service && python main.py")
        return

    # 2. 测试开启风扇
    print("\n[测试任务 1] 尝试开启风扇...")
    try:
        resp = requests.post(f"{base_url}/device/control", json={"state": True}, timeout=5)
        print(f"响应: {resp.json()}")
        if resp.status_code == 200:
            print("[SUCCESS] 指令已送达 API 层")
        else:
            print("[ERROR] API 返回错误")
    except Exception as e:
        print(f"[ERROR] 请求失败: {e}")

    # 3. 测试查询状态
    print("\n[测试任务 2] 查询当前状态...")
    try:
        resp = requests.get(f"{base_url}/device/status", timeout=5)
        print(f"响应: {resp.json()}")
        if resp.status_code == 200:
            print("[SUCCESS] 状态查询成功")
        else:
            print("[ERROR] 状态查询失败")
    except Exception as e:
        print(f"[ERROR] 请求失败: {e}")

    print("\n" + "="*50)
    print("测试脚本执行完毕。请检查 AI 服务控制台的串口日志。")
    print("="*50)

if __name__ == "__main__":
    test_iot_api()
