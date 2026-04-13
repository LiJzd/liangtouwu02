import asyncio
import time
from unittest.mock import patch, MagicMock

# Mock push_debug_event
captured_times = []
async def mock_push_event(event_type, data, client_id=None, agent=None, status=None):
    if event_type == "thought":
        captured_times.append(time.time())
        print(f"Pushed thought: {len(data.get('content'))} chars at {captured_times[-1]}")

async def test_throttling():
    from v1.logic.agent_debug_controller import RichTraceHandler
    
    with patch("v1.logic.agent_debug_controller.push_debug_event", side_effect=mock_push_event):
        handler = RichTraceHandler("client", "agent")
        
        print("Starting rapid token simulation...")
        start = time.time()
        for i in range(50):
            await handler.on_llm_new_token("token ")
            # Simulate very fast tokens (e.g. 10ms each)
            await asyncio.sleep(0.01)
        
        print(f"\nTotal tokens: 50")
        print(f"Total pushes: {len(captured_times)}")
        
        # Expecting around 3-4 pushes for 500ms total duration with 150ms throttle
        if len(captured_times) < 10:
            print("Throttling confirmed!")
        else:
            print(f"Throttling FAILED! Too many pushes: {len(captured_times)}")

if __name__ == "__main__":
    asyncio.run(test_throttling())
