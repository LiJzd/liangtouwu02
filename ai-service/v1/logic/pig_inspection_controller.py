# -*- coding: utf-8 -*-
"""
生猪检测报告业务控制器

负责生长曲线分析及每日简报生成逻辑。
通过多智能体协作系统（Orchestrator）分发任务，支持同步响应及 SSE 流式响应。
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from v1.logic.multi_agent_controller import get_orchestrator
from v1.logic.multi_agent_core import AgentContext

router = APIRouter()
logger = logging.getLogger("pig_inspection")


# --- 数据模型 ---

class InspectionRequest(BaseModel):
    """检测报告请求对象。"""
    pig_id: str = Field(..., min_length=1, max_length=64)
    trace_id: Optional[str] = Field(None, description="用于追踪 AI 推理过程的会话 ID")


class InspectionResponse(BaseModel):
    """检测报告响应对象。"""
    code: int = Field(default=200)
    message: str = Field(default="Report generated successfully")
    pig_id: str
    report: str
    timestamp: datetime = Field(default_factory=datetime.now)


class ErrorResponse(BaseModel):
    """错误响应对象。"""
    code: int
    message: str
    detail: Optional[str] = None
    pig_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


# --- 内部辅助函数 ---

def _fmt_sse(event: str, data: dict) -> str:
    """格式化 SSE 事件数据。"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _build_growth_curve_intent(pig_id: str) -> str:
    """构建生长曲线分析的智能体指令（Intent）。"""
    return (
        f"请为猪只 {pig_id} 生成生长曲线报告。"
        f"请注意，本系统专注的品种统称为【两头乌】。"
        f"⚠️ 禁止在报告中出现任何真实地名（如具体省、市、县、区、街道等）或真实人名。"
        f"此请求来自生长曲线分析模块，"
        f"必须调用数据工具获取真实指标，禁止生成虚假数据。"
    )


def _build_briefing_intent() -> str:
    """构建每日简报生成的智能体指令（Intent）。"""
    today = datetime.now().strftime("%Y-%m-%d")
    return (
        f"请生成 {today} 两头乌智能养殖场每日简报。"
        f"⚠️ 禁止在简报中出现任何真实地名或真实人名。"
        f"此请求来自每日简报模块，"
        f"必须聚合统计数据、环境参数及健康预警信息。"
    )


# --- 核心执行逻辑 ---

async def _run_growth_curve_via_agent(pig_id: str, trace_id: Optional[str] = None) -> str:
    """调用智能体调度器执行生长曲线分析任务。"""
    context = AgentContext(
        user_id=f"growth_curve_{pig_id}",
        user_input=_build_growth_curve_intent(pig_id),
        chat_history=[],
        metadata={
            "source": "growth_curve_page",
            "report_type": "growth_curve",
            "pig_id": pig_id,
        },
        client_id=trace_id or f"growth_curve_{pig_id}",
        image_urls=None,
    )
    logger.info("growth_curve: routing via orchestrator, pig_id=%s", pig_id)
    result = await get_orchestrator().execute(context)
    
    answer = (result.answer or "").strip()
    if not result.success or not answer:
        logger.error("growth_curve execution failed: %s", result.error)
        return f"error: {result.error or 'agent returned empty answer'}"
    return answer


async def _run_briefing_via_agent() -> str:
    """调用智能体调度器生成每日养殖简报。"""
    client_id = f"briefing_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    context = AgentContext(
        user_id="briefing_system",
        user_input=_build_briefing_intent(),
        chat_history=[],
        metadata={
            "source": "briefing_page",
            "report_type": "daily_briefing",
        },
        client_id=client_id,
        image_urls=None,
    )
    logger.info("briefing: routing via orchestrator")
    result = await get_orchestrator().execute(context)
    
    answer = (result.answer or "").strip()
    if not result.success or not answer:
        logger.error("briefing execution failed: %s", result.error)
        return f"error: {result.error or 'agent returned empty answer'}"
    return answer


# --- 接口端点：生长曲线 ---

@router.post("/generate", response_model=InspectionResponse, tags=["Inspection"])
async def generate_inspection_report(request: InspectionRequest):
    """生成指定猪只的生长曲线分析报告（同步接口）。"""
    try:
        report = await _run_growth_curve_via_agent(request.pig_id, trace_id=request.trace_id)
        if not report or report.startswith("error:"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Report generation failed: {report}",
            )
        return InspectionResponse(
            code=200, message="Success",
            pig_id=request.pig_id, report=report,
            timestamp=datetime.now(),
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inspection service exception: {exc}",
        ) from exc


@router.post("/generate/stream", tags=["Inspection"])
async def generate_inspection_report_stream(request: InspectionRequest):
    """流式生成生长曲线分析报告（SSE）。"""
    async def _gen():
        try:
            yield _fmt_sse("status", {"message": "Routing to GrowthCurve Specialist..."})
            report = await _run_growth_curve_via_agent(request.pig_id, trace_id=request.trace_id)
            if not report or report.startswith("error:"):
                yield _fmt_sse("error", {
                    "code": 500, "message": "Analysis failed",
                    "detail": report or "Empty response",
                    "pig_id": request.pig_id,
                })
                return
            
            yield _fmt_sse("status", {"message": "Pushing report content..."})
            chunk_size = 120
            logger.info("growth_curve: starting stream delivery for pig_id=%s", request.pig_id)
            
            for i in range(0, len(report), chunk_size):
                chunk = report[i: i + chunk_size]
                yield _fmt_sse("chunk", {"text": chunk})
                await asyncio.sleep(0.01)
                
            yield _fmt_sse("done", {
                "code": 200, "message": "Stream completed",
                "pig_id": request.pig_id,
                "timestamp": datetime.now().isoformat(),
            })
        except Exception as exc:
            yield _fmt_sse("error", {
                "code": 500, "message": "Algorithm node unavailable",
                "detail": str(exc),
                "pig_id": request.pig_id,
            })

    return StreamingResponse(
        _gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


# --- 接口端点：每日简报 ---

@router.post("/briefing", tags=["Briefing"])
async def generate_farm_briefing():
    """生成全场养殖每日简报（同步接口）。"""
    try:
        report = await _run_briefing_via_agent()
        if not report or report.startswith("error:"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Briefing generation failed: {report}",
            )

        today = datetime.now().strftime("%Y-%m-%d")
        # 提取首段非标题文字作为摘要
        summary = ""
        for line in report.split("\n"):
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and not stripped.startswith("*"):
                summary = stripped[:120]
                break

        return {
            "code": 200,
            "message": "Success",
            "data": {
                "report": report,
                "summary": summary or f"{today} Farm Briefing generated",
                "timestamp": datetime.now().isoformat(),
            },
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Briefing service exception: {exc}",
        ) from exc


@router.post("/briefing/stream", tags=["Briefing"])
async def generate_farm_briefing_stream():
    """流式生成全场养殖每日简报（SSE）。"""
    async def _gen():
        try:
            yield _fmt_sse("status", {"message": "Routing to Briefing Specialist..."})
            report = await _run_briefing_via_agent()
            if not report or report.startswith("error:"):
                yield _fmt_sse("error", {
                    "code": 500, "message": "Briefing failed",
                    "detail": report or "Empty response",
                })
                return
            
            yield _fmt_sse("status", {"message": "Pushing briefing content..."})
            chunk_size = 80
            logger.info("briefing: starting stream delivery, report_len=%d", len(report))
            
            for i in range(0, len(report), chunk_size):
                chunk = report[i: i + chunk_size]
                yield _fmt_sse("chunk", {"text": chunk})
                await asyncio.sleep(0.01)
                
            logger.info("briefing: stream delivery completed")
            yield _fmt_sse("done", {
                "code": 200, "message": "简报流传输完成",
                "timestamp": datetime.now().isoformat(),
            })
        except Exception as exc:
            yield _fmt_sse("error", {
                "code": 500, "message": "算法节点不可用", "detail": str(exc),
            })

    return StreamingResponse(
        _gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


# ─── 健康检查 ────────────────────────────────────────────────────


@router.get("/health", tags=["系统监控"])
async def health_check():
    """报个平安。"""
    return {
        "status": "UP",
        "service": "Liangtouwu-Report-Engine",
        "arch": "Supervisor→Agent routing",
        "workers": ["growth_curve_agent", "briefing_agent"],
        "timestamp": datetime.now(),
    }
