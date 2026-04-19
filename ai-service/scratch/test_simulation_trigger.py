import httpx
import asyncio
import json

async def trigger_mock():
    url = "http://localhost:8000/api/v1/agent/simulations/mock"
    params = {
        "pig_id": "TEST-PIG-999",
        "area": "测试猪舍",
        "type": "模拟环境异常",
        "force": True
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, timeout=10.0)
            print(f"Status: {response.status_code}")
            print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(trigger_mock())
