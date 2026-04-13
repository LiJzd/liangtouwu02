import asyncio
import json
import os
import sys
from unittest.mock import MagicMock, AsyncMock, patch

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

async def verify_streaming():
    from v1.logic.multi_agent_core import VetAgent, AgentContext
    from v1.logic.agent_debug_controller import push_debug_event
    
    # Mock push_debug_event to capture calls
    captured_events = []
    async def mock_push_event(event_type, data, client_id=None, agent=None, status=None):
        captured_events.append({"type": event_type, "data": data, "agent": agent, "status": status})
        print(f"Captured Event: {event_type} - {status or ''} - {data.get('content')[:50] if 'content' in data else ''}")

    # Mock tools to return predictable strings
    with patch("v1.logic.agent_debug_controller.push_debug_event", side_effect=mock_push_event), \
         patch("v1.logic.bot_tools.tool_query_pig_disease_rag", return_value=asyncio.Future()), \
         patch("v1.logic.bot_tools.tool_query_env_status", return_value=asyncio.Future()):
        
        # Setup mocks
        from v1.logic.bot_tools import tool_query_pig_disease_rag, tool_query_env_status
        tool_query_pig_disease_rag.return_value.set_result("MOCK_RAG_DATA")
        tool_query_env_status.return_value.set_result("MOCK_ENV_DATA")
        
        agent = VetAgent()
        # Mock dashscope call
        mock_it = iter([
            MagicMock(status_code=200, output=MagicMock(choices=[MagicMock(message=MagicMock(content=[{'text': '### 🔍 临床观察'}]))])),
            MagicMock(status_code=200, output=MagicMock(choices=[MagicMock(message=MagicMock(content=[{'text': '### 🔍 临床观察\n发现猪只精神不振。'}]))]))
        ])
        
        with patch("dashscope.MultiModalConversation.call", return_value=mock_it):
            context = AgentContext(user_id="test", user_input="测试诊断", chat_history=[], metadata={}, client_id="test_client", image_urls=["data:image/jpeg;base64,..."])
            # Bypass image preprocessing for test
            agent._preprocess_image = AsyncMock(return_value="dummy.jpg")
            
            result = await agent.execute(context)
            
            print("\nFinal Result Answer:")
            print(result.answer)
            
            print("\nCaptured Sequence Checklist:")
            types = [e["type"] for e in captured_events]
            print(f"Thought events count: {types.count('thought')}")
            print(f"Observation events count: {types.count('observation')}")
            print(f"Thinking end event: {'thinking_end' in types}")

if __name__ == "__main__":
    # Mock environment
    os.environ["DASHSCOPE_API_KEY"] = "sk-test"
    asyncio.run(verify_streaming())
