import asyncio
import httpx
import json

async def test_ammonia_simulation():
    url = "http://localhost:8000/api/v1/agent/simulations/ingest"
    payload = {
        "pigId": "PIG-TEST-99",
        "area": "实验舍 A 区",
        "type": "氨气浓度预警",
        "ammonia_ppm": 32.0,
        "forceMode": False
    }
    
    print(f"Sending simulation request to {url}...")
    try:
        async with httpx.AsyncClient(timeout=40.0) as client:
            response = await client.post(url, json=payload)
            print(f"Status Code: {response.status_code}")
            result = response.json()
            with open("scratch/simulation_response.json", "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=4)
            print("\n✅ Verification SUCCESS: Response saved to scratch/simulation_response.json")
                
    except Exception as e:
        print(f"Error during verification: {e}")

if __name__ == "__main__":
    asyncio.run(test_ammonia_simulation())
