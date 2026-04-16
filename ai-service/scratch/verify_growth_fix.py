import asyncio
import json
import math
import sys
import os

# Set PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), ".")))

# Mock the environment so multi_agent_core can import
os.environ["DASHSCOPE_API_KEY"] = "mock_key"

from v1.logic.multi_agent_core import GrowthCurveAgent, AgentContext

async def test_growth_logic():
    agent = GrowthCurveAgent()
    context = AgentContext(
        user_id="test_user",
        user_input="查看 PIG001 的生长曲线",
        chat_history=[],
        metadata={},
        client_id="test_client"
    )
    
    # We want to see the MD generated in the execute method
    # Since execute is complex and sends debug events, we might need to mock push_debug_event
    
    import v1.logic.agent_debug_controller
    async def mock_push(*args, **kwargs):
        pass
    v1.logic.agent_debug_controller.push_debug_event = mock_push
    
    result = await agent.execute(context)
    print("--- Generated MD ---")
    print(result.answer)

if __name__ == "__main__":
    asyncio.run(test_growth_logic())
