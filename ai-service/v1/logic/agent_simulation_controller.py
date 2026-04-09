from __future__ import annotations

from fastapi import APIRouter

from v1.logic.agent_simulation_service import AgentSimulationService
from v1.objects.agent_simulation_schemas import SimulatedAlertEvent, SimulationIngestResponse

router = APIRouter()
_service = AgentSimulationService()


@router.post("/simulations/ingest", response_model=SimulationIngestResponse)
async def ingest_simulation(payload: SimulatedAlertEvent) -> SimulationIngestResponse:
    """
    模拟告警的“收件箱”。
    
    收到模拟的异常事件（比如猪发烧了）后，直接丢给后台模拟服务去深度分析。
    """
    return await _service.ingest(payload)
