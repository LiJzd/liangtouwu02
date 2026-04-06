"""
Inspection report controller.

The growth-curve page still calls `/api/v1/inspection/*`, but report generation
now routes through the shared agent pipeline so central/multi-agent logs and
debug traces are emitted consistently.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from v1.logic.multi_agent_controller import get_orchestrator
from v1.logic.multi_agent_core import AgentContext

# Keep pig_rag importable for the legacy daily briefing entrypoint below.
sys.path.append(os.path.join(os.path.dirname(__file__), "../../pig_rag"))

router = APIRouter()
logger = logging.getLogger("pig_inspection")


class InspectionRequest(BaseModel):
    pig_id: str = Field(..., min_length=1, max_length=64, description="Pig ID")


class InspectionResponse(BaseModel):
    code: int = Field(default=200, description="Business status code")
    message: str = Field(default="Report generated successfully")
    pig_id: str
    report: str
    timestamp: datetime = Field(default_factory=datetime.now)


class ErrorResponse(BaseModel):
    code: int
    message: str
    detail: Optional[str] = None
    pig_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


def _format_sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _build_growth_curve_prompt(pig_id: str) -> str:
    """Ask the data agent for a UI-compatible markdown report with historical + prediction data."""
    return f"""
请为猪只 {pig_id} 生成一份"生长曲线预测报告"。

这是 growth-curve 页面发起的内部请求，必须走 agent 工具链，不要跳过工具直接回答。

执行要求：
1. 先调用 get_pig_info_by_id 查询该猪只档案，获取 lifecycle 数据（含喂食/饮水记录）。
2. 再调用 query_pig_growth_prediction，优先使用 {{"pig_id":"{pig_id}"}} 这种入参，获取未来预测轨迹。
3. 如果工具返回的是 JSON，请你自己整理成 Markdown，不要把原始 JSON 直接贴给用户。

输出格式必须严格按以下结构：

## 基本信息
- **猪只ID**：{pig_id}
- **品种**：（从工具结果填写）
- **当前月龄**：（从工具结果填写）月
- **当前体重**：（从工具结果填写）kg

## 生长趋势分析
（2到4条简短的预测结论和建议）

### 历史实测数据 (Historical)
| 月份 | 实测体重(kg) | 喂食次数 | 喂食时长(min) | 饮水次数 | 饮水时长(min) |
| --- | --- | --- | --- | --- | --- |
（从 get_pig_info_by_id 返回的 lifecycle 字段逐月填写，有几个月填几行，绝不编造）
（月份只写数字，体重只写数字，喂食/饮水字段写整数）

### 预测生长曲线数据 (Monthly)
| 月份 (Month) | 拟合/预测体重 (kg) | 状态 |
| --- | --- | --- |
（从 query_pig_growth_prediction 获取，历史月份标注"已记录"，未来月份标注"预测"，当前月标注"当前"；按月份升序排列）

## AI 建议
（3条针对该猪只当前状态的具体建议，结合喂食/饮水数据给出）

严格要求：
- 必须同时输出以上两个表格，缺一不可。
- 不要返回 JSON 格式内容。
- 所有数字列只写纯数字，不含单位。
- 回复全程使用中文。
- lifecycle 有几个月的数据就填几行，不要编造不存在月份的数据。
""".strip()


async def _run_inspection_via_agent(pig_id: str) -> str:
    client_id = f"growth_curve_{pig_id}"
    context = AgentContext(
        user_id=f"growth_curve_{pig_id}",
        user_input=_build_growth_curve_prompt(pig_id),
        chat_history=[],
        metadata={
            "source": "growth_curve_page",
            "report_type": "growth_curve",
            "pig_id": pig_id,
        },
        client_id=client_id,
        image_urls=None,
    )

    logger.info("growth_curve request routed to multi-agent pig_id=%s client_id=%s", pig_id, client_id)
    result = await get_orchestrator().execute(context)
    logger.info(
        "growth_curve multi-agent finished pig_id=%s success=%s worker=%s error=%s",
        pig_id,
        result.success,
        result.worker_name,
        result.error,
    )

    answer = (result.answer or "").strip()
    if not result.success or not answer:
        detail = result.error or "agent returned empty answer"
        return f"error: {detail}"
    return answer


@router.post("/generate", response_model=InspectionResponse, tags=["生猪检测"])
async def generate_inspection_report(request: InspectionRequest):
    try:
        report = await _run_inspection_via_agent(request.pig_id)

        if not report or report.startswith("error:"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"agent report generation failed: {report}",
            )

        return InspectionResponse(
            code=200,
            message="报告生成成功",
            pig_id=request.pig_id,
            report=report,
            timestamp=datetime.now(),
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"inspection service failed: {exc}",
        ) from exc


@router.post("/generate/stream", tags=["生猪检测"])
async def generate_inspection_report_stream(request: InspectionRequest):
    async def event_generator():
        try:
            yield _format_sse("status", {"message": "正在唤起中央 agent..."})
            yield _format_sse("status", {"message": "正在路由到数据专家并拉取生长预测..."})

            report = await _run_inspection_via_agent(request.pig_id)

            if not report or report.startswith("error:"):
                yield _format_sse(
                    "error",
                    {
                        "code": 500,
                        "message": "分析过程失败",
                        "detail": report or "生成内容为空",
                        "pig_id": request.pig_id,
                    },
                )
                return

            yield _format_sse("status", {"message": "正在整理生长曲线报告..."})

            chunk_size = 120
            for i in range(0, len(report), chunk_size):
                yield _format_sse("chunk", {"text": report[i : i + chunk_size]})
                await asyncio.sleep(0.01)

            yield _format_sse(
                "done",
                {
                    "code": 200,
                    "message": "分析流传输完成",
                    "pig_id": request.pig_id,
                    "timestamp": datetime.now().isoformat(),
                },
            )
        except Exception as exc:
            yield _format_sse(
                "error",
                {
                    "code": 500,
                    "message": "算法节点不可用",
                    "detail": str(exc),
                    "pig_id": request.pig_id,
                },
            )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/briefing", tags=["生猪检测"])
async def generate_farm_briefing():
    try:
        from pig_agent import run_farm_daily_briefing

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, run_farm_daily_briefing)

        if not result or (isinstance(result, dict) and result.get("report", "").startswith("error")):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"briefing engine failed: {result}",
            )

        return {
            "code": 200,
            "message": "每日简报生成成功",
            "data": {
                "report": result["report"],
                "summary": result["summary"],
                "timestamp": datetime.now().isoformat(),
            },
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"briefing generation failed: {exc}",
        ) from exc


@router.get("/health", tags=["系统监控"])
async def health_check():
    return {
        "status": "UP",
        "service": "Liangtouwu-Report-Engine-v1",
        "arch": "Agent-driven growth-curve reporting",
        "timestamp": datetime.now(),
    }
