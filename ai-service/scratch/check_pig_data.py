import asyncio
import os
import sys
import json

# Add the project root to sys.path
sys.path.append(r"C:\Users\lost\Desktop\两头乌\ai-service")

from v1.logic.bot_tools import tool_get_pig_info_by_id
from dotenv import load_dotenv

load_dotenv(r"C:\Users\lost\Desktop\两头乌\ai-service\.env")

async def check_data():
    pig_id = "PIG001"
    print(f"Checking data for {pig_id}...")
    
    try:
        result = await tool_get_pig_info_by_id(pig_id)
        print("\nTool Output:")
        print(result)
        
        data = json.loads(result)
        if "lifecycle" in data:
            print("\nReal Lifecycle Data:")
            for d in data["lifecycle"]:
                print(f"Month: {d.get('month')}, Weight: {d.get('weight_kg')}")
    except Exception as e:
        print(f"\nFailed: {e}")

if __name__ == "__main__":
    asyncio.run(check_data())
