import asyncio
import json
import os
import sys

# 关键：确保项目根目录在 path 中
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from v1.logic.agent_simulation_service import AgentSimulationService
from v1.objects.agent_simulation_schemas import SimulatedAlertEvent

async def debug_crash():
    service = AgentSimulationService()
    payload = SimulatedAlertEvent(
        pigId="DEBUG-PIG",
        area="DebugArea",
        type="环境异常",
        forceMode=True,
        ammoniaPpm=30.0,
        announcementText="调试报警"
    )
    
    print("--- Starting ingest test ---")
    try:
        # 模拟 ingest 调用
        result = await service.ingest(payload)
        print("--- Ingest completed successfully ---")
        print(f"Result: {result}")
    except Exception as e:
        print(f"--- Ingest CRASHED with error: {e} ---")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_crash())
