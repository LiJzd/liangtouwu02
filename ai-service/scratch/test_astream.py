import asyncio
import os
import sys

# Setup paths
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'ai-service'))

from v1.logic.multi_agent_core import DashScopeNativeChat
from langchain_core.messages import HumanMessage

async def test_streaming():
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        print("Error: DASHSCOPE_API_KEY not found. Please provide it for testing.")
        # Try to find it in the project if possible, but for now we assume it exists in environment
        # or we manually mock it if needed.
        return

    llm = DashScopeNativeChat(model="qwen-max", api_key=api_key, streaming=True)
    print("Starting stream...")
    async for chunk in llm.astream([HumanMessage(content="你好，请介绍一下你自己。")]):
        print(f"Chunk received: {chunk.content}")

if __name__ == "__main__":
    asyncio.run(test_streaming())
