"""
这里是生猪检测报告的“指挥部”。

现在的玩法变了：
1. 生长曲线分析：不再自己埋头干，而是发个口信让 Supervisor 指派 GrowthCurveAgent 去干活。
2. 每日简报：同样的套路，发个意图让 BriefingAgent 给咱出一份全场的日报。
3. 顺滑体验：支持 SSE 流式推送，报告是一个字一个字蹦出来的，体验更好。
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


# ─── 请求 / 响应模型 ────────────────────────────────────────────


class InspectionRequest(BaseModel):
    pig_id: str = Field(..., min_length=1, max_length=64)


class InspectionResponse(BaseModel):
    code: int = Field(default=200)
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


# ─── 工具函数 ────────────────────────────────────────────────────


def _fmt_sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _build_growth_curve_intent(pig_id: str) -> str:
    """拼一句话，告诉调度员我们要查哪头猪的生长曲线。"""
    return (
        f"请为猪只 {pig_id} 生成生长曲线报告。"
        f"这是来自生长曲线页面的内部请求（growth_curve），"
        f"必须通过工具链获取真实数据，不得跳过工具直接回答。"
    )


def _build_briefing_intent() -> str:
    """拼一句话，让调度员去生成今日的全场简报。"""
    today = datetime.now().strftime("%Y-%m-%d")
    return (
        f"请生成今日 {today} 的两头乌养殖场每日简报（briefing）。"
        f"这是来自每日简报页面的内部请求，"
        f"必须调用工具获取真实的全场统计、环境和健康数据。"
    )


# ─── 核心执行函数 ────────────────────────────────────────────────


async def _run_growth_curve_via_agent(pig_id: str) -> str:
    """把活儿甩给多智能体系统，让 GrowthCurveAgent 去折腾报告。"""
    context = AgentContext(
        user_id=f"growth_curve_{pig_id}",
        user_input=_build_growth_curve_intent(pig_id),
        chat_history=[],
        metadata={
            "source": "growth_curve_page",
            "report_type": "growth_curve",
            "pig_id": pig_id,
        },
        client_id=f"growth_curve_{pig_id}",
        image_urls=None,
    )
    logger.info("growth_curve: routing via SupervisorAgent pig_id=%s", pig_id)
    result = await get_orchestrator().execute(context)
    logger.info(
        "growth_curve: worker=%s success=%s error=%s",
        result.worker_name, result.success, result.error,
    )
    answer = (result.answer or "").strip()
    if not result.success or not answer:
        return f"error: {result.error or 'agent returned empty answer'}"
    return answer


async def _run_briefing_via_agent() -> str:
    """通过多智能体系统，找 BriefingAgent 要一份简报。"""
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
    logger.info("briefing: routing via SupervisorAgent")
    result = await get_orchestrator().execute(context)
    logger.info(
        "briefing: worker=%s success=%s error=%s",
        result.worker_name, result.success, result.error,
    )
    answer = (result.answer or "").strip()
    if not result.success or not answer:
        return f"error: {result.error or 'agent returned empty answer'}"
    return answer


# ─── 生长曲线端点 ────────────────────────────────────────────────


@router.post("/generate", response_model=InspectionResponse, tags=["生猪检测"])
async def generate_inspection_report(request: InspectionRequest):
    try:
        report = await _run_growth_curve_via_agent(request.pig_id)
        if not report or report.startswith("error:"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"agent report generation failed: {report}",
            )
        return InspectionResponse(
            code=200, message="成功",
            pig_id=request.pig_id, report=report,
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
    async def _gen():
        """打字机效果的推送逻辑：先把专家请出来，再把它的答案一截截喂给前端。"""
        try:
            yield _fmt_sse("status", {"message": "正在路由到生长曲线分析专家..."})
            report = await _run_growth_curve_via_agent(request.pig_id)
            if not report or report.startswith("error:"):
                yield _fmt_sse("error", {
                    "code": 500, "message": "分析过程失败",
                    "detail": report or "生成内容为空",
                    "pig_id": request.pig_id,
                })
                return
            yield _fmt_sse("status", {"message": "正在推送生长曲线报告..."})
            chunk_size = 120
            logger.info("growth_curve: starting stream delivery for pig_id=%s, report_len=%d", request.pig_id, len(report))
            
            for i in range(0, len(report), chunk_size):
                chunk = report[i: i + chunk_size]
                yield _fmt_sse("chunk", {"text": chunk})
                await asyncio.sleep(0.01)
                
            logger.info("growth_curve: stream delivery completed for pig_id=%s", request.pig_id)
            yield _fmt_sse("done", {
                "code": 200, "message": "分析流传输完成",
                "pig_id": request.pig_id,
                "timestamp": datetime.now().isoformat(),
            })
        except Exception as exc:
            yield _fmt_sse("error", {
                "code": 500, "message": "算法节点不可用",
                "detail": str(exc),
                "pig_id": request.pig_id,
            })

    return StreamingResponse(
        _gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


# ─── 每日简报端点 ────────────────────────────────────────────────


@router.post("/briefing", tags=["每日简报"])
async def generate_farm_briefing():
    """
    手动生成全场日报。
    除了拿回完整的报告，咱们还会顺手帮前端从第一段里抠出个简短的摘要。
    """
    try:
        report = await _run_briefing_via_agent()
        if not report or report.startswith("error:"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"briefing generation failed: {report}",
            )

        today = datetime.now().strftime("%Y-%m-%d")
        # 提取简报第一段作为 summary
        first_para = ""
        for line in report.split("\n"):
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and not stripped.startswith("*"):
                first_para = stripped[:120]
                break

        return {
            "code": 200,
            "message": "每日简报生成成功",
            "data": {
                "report": report,
                "summary": first_para or f"{today} 每日简报已生成",
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


@router.post("/briefing/stream", tags=["每日简报"])
async def generate_farm_briefing_stream():
    """流式日报推送，让用户看着更有“正在分析”的感觉。"""
    async def _gen():
        try:
            yield _fmt_sse("status", {"message": "正在路由到每日简报生成专家..."})
            report = await _run_briefing_via_agent()
            if not report or report.startswith("error:"):
                yield _fmt_sse("error", {
                    "code": 500, "message": "简报生成失败",
                    "detail": report or "生成内容为空",
                })
                return
            yield _fmt_sse("status", {"message": "正在推送今日简报..."})
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
