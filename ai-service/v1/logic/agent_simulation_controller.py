# -*- coding: utf-8 -*-
from __future__ import annotations

from fastapi import APIRouter

from v1.logic.agent_simulation_service import AgentSimulationService
from v1.objects.agent_simulation_schemas import SimulatedAlertEvent, SimulationIngestResponse

router = APIRouter()
_service = AgentSimulationService()


@router.post("/simulations/ingest", response_model=SimulationIngestResponse)
async def ingest_simulation(payload: SimulatedAlertEvent) -> SimulationIngestResponse:
    """
    接收并处理仿真告警事件的接入点。
    
    接收模拟的异常事件数据，并调用仿真服务进行深度异常检测与分析。
    """
    return await _service.ingest(payload)
