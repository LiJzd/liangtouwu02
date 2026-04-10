import httpx
import json
import asyncio
import os

async def test_multimodal_chat():
    url = "http://localhost:8000/api/v1/agent/chat/v2"
    
    # Text message
    messages = [
        {"role": "user", "content": "这头猪看起来怎么样？"}
    ]
    
    # Create a dummy audio file if not exists
    audio_path = "test_audio.webm"
    if not os.path.exists(audio_path):
        with open(audio_path, "wb") as f:
            f.write(b"fake audio data")
            
    files = {
        'audio': ('test_audio.webm', open(audio_path, 'rb'), 'audio/webm'),
    }
    
    data = {
        'user_id': 'test_user',
        'messages': json.dumps(messages),
        'image_urls': json.dumps([]),
        'metadata': json.dumps({})
    }
    
    print(f"Sending multimodal request to {url}...")
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(url, data=data, files=files)
        
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        print(f"Response: {resp.json().get('reply')}")
    else:
        print(f"Error: {resp.text}")

if __name__ == "__main__":
    asyncio.run(test_multimodal_chat())
