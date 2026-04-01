from __future__ import annotations

from fastapi import APIRouter

from v1.logic.agent_simulation_service import AgentSimulationService
from v1.objects.agent_simulation_schemas import SimulatedAlertEvent, SimulationIngestResponse

router = APIRouter()
_service = AgentSimulationService()


@router.post("/simulations/ingest", response_model=SimulationIngestResponse)
async def ingest_simulation(payload: SimulatedAlertEvent) -> SimulationIngestResponse:
    return await _service.ingest(payload)
