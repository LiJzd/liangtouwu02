import asyncio
import os
import sys

# Add the project root to sys.path
sys.path.append(r"C:\Users\lost\Desktop\两头乌\ai-service")

from v1.logic.multi_agent_core import DashScopeNativeChat, HumanMessage
from dotenv import load_dotenv

load_dotenv(r"C:\Users\lost\Desktop\两头乌\ai-service\.env")

async def verify_fix():
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    model = os.environ.get("DASHSCOPE_MODEL")
    
    print(f"Verifying with model: {model}")
    
    llm = DashScopeNativeChat(
        model=model,
        api_key=api_key,
        temperature=0.1
    )
    
    messages = [HumanMessage(content="你好，请介绍一下你自己。")]
    
    try:
        print("Calling DashScopeNativeChat._agenerate...")
        result = await llm._agenerate(messages)
        print("\nSuccess!")
        print(f"Response: {result.generations[0].message.content}")
    except Exception as e:
        print(f"\nFailed: {e}")

if __name__ == "__main__":
    asyncio.run(verify_fix())
