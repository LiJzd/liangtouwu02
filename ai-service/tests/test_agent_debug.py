"""
测试 Agent 调试功能
验证 Rich 控制台追踪和 SSE 调试流
"""
import asyncio
import httpx


async def test_agent_chat():
    """测试 Agent 对话并观察调试输出"""
    url = "http://localhost:8000/api/v1/agent/chat"
    
    payload = {
        "user_id": "test_user_001",
        "messages": [
            {
                "role": "system",
                "content": "你是掌上明猪的智能助手"
            },
            {
                "role": "user",
                "content": "我的猪场有哪些猪？"
            }
        ],
        "metadata": {
            "channel": "test",
            "source": "pytest"
        }
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("📤 发送请求到 Agent...")
        response = await client.post(url, json=payload)
        print(f"📥 响应状态: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Agent 回复: {data.get('reply')}")
        else:
            print(f"❌ 请求失败: {response.text}")


async def test_sse_stream():
    """测试 SSE 调试流"""
    url = "http://localhost:8000/api/v1/agent/debug/agent-trace?client_id=test_debug"
    
    print("🔌 连接到 SSE 调试流...")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream("GET", url) as response:
            print(f"📡 连接状态: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ SSE 流已连接，等待事件...\n")
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        event_data = line[6:]  # 移除 "data: " 前缀
                        print(f"📨 收到事件: {event_data}\n")
            else:
                print(f"❌ 连接失败: {response.text}")


if __name__ == "__main__":
    print("=" * 60)
    print("🧪 Agent 调试功能测试")
    print("=" * 60)
    print("\n提示：请先启动 FastAPI 服务 (python main.py)\n")
    
    # 测试 1: Agent 对话
    print("\n【测试 1】Agent 对话")
    print("-" * 60)
    asyncio.run(test_agent_chat())
    
    # 测试 2: SSE 调试流（需要手动中断）
    print("\n【测试 2】SSE 调试流（按 Ctrl+C 中断）")
    print("-" * 60)
    try:
        asyncio.run(test_sse_stream())
    except KeyboardInterrupt:
        print("\n\n✅ 测试完成")
