import asyncio
import os
import sys
from unittest.mock import MagicMock, AsyncMock, patch

# Add the project root to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

async def verify_dual_channel():
    from v1.logic.multi_agent_core import VetAgent, AgentContext
    
    captured_events = []
    async def mock_push_event(event_type, data, client_id=None, agent=None, status=None):
        captured_events.append({"type": event_type, "data": data, "agent": agent, "status": status})
        content = data.get('content', data.get('text', ''))
        print(f"[{event_type}] {status or ''} -> {content[:30]}...")

    with patch("v1.logic.agent_debug_controller.push_debug_event", side_effect=mock_push_event), \
         patch("v1.logic.bot_tools.tool_query_pig_disease_rag", return_value=asyncio.Future()), \
         patch("v1.logic.bot_tools.tool_query_env_status", return_value=asyncio.Future()):
        
        from v1.logic.bot_tools import tool_query_pig_disease_rag, tool_query_env_status
        tool_query_pig_disease_rag.return_value.set_result("MOCK_RAG")
        tool_query_env_status.return_value.set_result("MOCK_ENV")
        
        agent = VetAgent()
        agent._preprocess_image = AsyncMock(return_value="dummy.jpg")
        
        # Mock MultiModalConversation response stream
        mock_it = iter([
            MagicMock(status_code=200, output=MagicMock(choices=[MagicMock(message=MagicMock(content=[{'text': '### 临床观察'}]))])),
            MagicMock(status_code=200, output=MagicMock(choices=[MagicMock(message=MagicMock(content=[{'text': '### 临床观察\n详细描述。'}]))]))
        ])
        
        with patch("dashscope.MultiModalConversation.call", return_value=mock_it):
            context = AgentContext(user_id="test", user_input="测试", chat_history=[], metadata={}, client_id="test", image_urls=["data:image/jpeg;base64,..."])
            result = await agent.execute(context)
            
            print("\nVerification Checklist:")
            types = [e["type"] for e in captured_events]
            has_chunks = "final_answer_chunk" in types
            has_thoughts = "thought" in types
            print(f"- 主窗口流式 (final_answer_chunk): {has_chunks}")
            print(f"- 侧边栏思维链 (thought): {has_thoughts}")
            
            # Check prompt construction
            call_kwargs = dashscope.MultiModalConversation.call.call_args[1]
            messages = call_kwargs['messages']
            user_msg = messages[0]['content']
            prompt_text = next((item['text'] for item in user_msg if 'text' in item), "")
            print(f"- Prompt 是否含任务指令: {'【任务指令】' in prompt_text}")

if __name__ == "__main__":
    os.environ["DASHSCOPE_API_KEY"] = "sk-test"
    asyncio.run(verify_dual_channel())
