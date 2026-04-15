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
    接收并处理仿真告警事件的接入层。
    
    接收模拟的异常数据（体温、环境指标等），并根据 force_mode 决定是走 Agent 智能路由还是直接触发告警。
    """
    return await _service.ingest(payload)


@router.get("/simulations/mock", response_model=SimulationIngestResponse)
async def trigger_mock_alert(
    pig_id: str = "SIM-PIG-001",
    area: str = "一号猪舍",
    type: str = "模拟环境异常",
    force: bool = True
) -> SimulationIngestResponse:
    """
    便捷接口：一键触发一次预设的模拟报警。
    主要用于前端演示和语音播报联调。
    """
    payload = SimulatedAlertEvent(
        pigId=pig_id,
        area=area,
        type=type,
        forceMode=force,
        bodyTemp=40.5,  # 设为一个明显的异常值
        description="这是一次由调试接口生成的模拟异常事件。"
    )
    return await _service.ingest(payload)

