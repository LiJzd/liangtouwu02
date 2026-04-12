import asyncio
import sys
import os
import json

# 添加项目根目录到 Python 路径
sys.path.insert(0, r"c:\Users\lost\Desktop\两头乌\ai-service")

from v1.logic.multi_agent_core import AgentContext, VetAgent
from v1.logic.agent_debug_controller import get_or_create_queue

async def mock_sse_listener(client_id):
    queue = await get_or_create_queue(client_id)
    print(f"--- SSE Listener started for {client_id} ---")
    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=20.0)
                etype = event.get("type")
                data = event.get("data", {})
                if etype == "final_answer_chunk":
                    print(data.get("text"), end="", flush=True)
                elif etype in ["thought", "action", "observation"]:
                    print(f"\n[{etype.upper()}] {data.get('thought') or data.get('content') or data.get('tool') or data.get('output')}")
            except asyncio.TimeoutError:
                break
    except Exception as e:
        print(f"Listener error: {e}")

async def test_streaming():
    client_id = "test_stream_123"
    agent = VetAgent()
    context = AgentContext(
        user_id="test_user",
        user_input="我的猪今天不爱吃食，还有点咳嗽，是怎么回事？",
        chat_history=[],
        metadata={"trace_id": client_id},
        client_id=client_id
    )
    
    # 启动异步监听器
    listener_task = asyncio.create_task(mock_sse_listener(client_id))
    
    print("--- Starting Agent Execution ---")
    result = await agent.execute(context)
    print("\n--- Agent Execution Finished ---")
    print(f"Final Answer: {result.answer}")
    
    # 等待一会儿让剩余消息传完
    await asyncio.sleep(2)
    listener_task.cancel()

if __name__ == "__main__":
    asyncio.run(test_streaming())
