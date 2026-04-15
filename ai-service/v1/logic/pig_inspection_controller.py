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

from fastapi import APIRouter, Body, HTTPException, status
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
        f"请注意，本系统专注的生猪生长分析。"
        f"⚠️ 禁止在报告中出现任何真实地名（如具体省、市、县、区、街道等）或真实人名。"
        f"此请求来自生长曲线分析模块，"
        f"必须调用数据工具获取真实指标，禁止生成虚假数据。"
    )


def _build_briefing_intent() -> str:
    """构建每日简报生成的智能体指令（Intent）。"""
    today = datetime.now().strftime("%Y-%m-%d")
    return (
        f"请生成 {today} 智慧养殖场每日简报。"
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


async def _run_briefing_via_agent(trace_id: Optional[str] = None) -> str:
    """调用智能体调度器生成每日养殖简报。"""
    client_id = trace_id or f"briefing_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
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
    trace_id = request.trace_id or f"growth_curve_{request.pig_id}_{datetime.now().strftime('%H%M%S')}"
    
    async def _gen():
        try:
            from v1.logic.agent_debug_controller import get_or_create_queue, cleanup_queue
            queue = await get_or_create_queue(trace_id)
            
            # 开启异步任务执行业务逻辑
            task = asyncio.create_task(_run_growth_curve_via_agent(request.pig_id, trace_id=trace_id))
            
            yield _fmt_sse("status", {"message": "正在路由至生长曲线专家..."})
            
            # 监听队列中的事件并转发
            full_report = ""
            while not task.done() or not queue.empty():
                try:
                    # 获取事件，带较短超时以便检查 task 状态
                    event = await asyncio.wait_for(queue.get(), timeout=1.0)
                    
                    if event["type"] == "final_answer_chunk":
                        # 转发令牌
                        text = event["data"].get("text", "")
                        full_report += text
                        yield _fmt_sse("chunk", {"text": text})
                        # 后端应尽快将队列排空送往前端，打字机节奏由前端 Vue 组件统一控制
                    elif event["type"] == "curve_data":
                        # [Speed Optimization] 直接转发曲线原始数据包
                        yield _fmt_sse("curve_data", event["data"])
                    elif event["type"] in ["thought", "observation", "connected", "debug_event"]:
                        # 转发思维链追踪事件
                        yield _fmt_sse("trace", {
                            "message": event["data"].get("content") or event["data"].get("output") or event["data"].get("message") or "AI 正在分析...",
                            "level": "DEBUG" if event["type"] == "thought" else "INFO",
                            "agent": event.get("agent")
                        })
                except asyncio.TimeoutError:
                    continue
            
            # 任务完成后确保清理
            report = await task
            if not full_report and (not report or report.startswith("error:")):
                yield _fmt_sse("error", {
                    "code": 500, "message": "Analysis failed",
                    "detail": report or "Empty response",
                    "pig_id": request.pig_id,
                })
                return
            
            # 如果流中没有收到 chunk（例如非 LangChain 降级路径），则进行最后的一口气补偿
            if not full_report:
                yield _fmt_sse("status", {"message": "正在同步报告帧..."})
                chunk_size = 100
                for i in range(0, len(report), chunk_size):
                    yield _fmt_sse("chunk", {"text": report[i:i+chunk_size]})
                    await asyncio.sleep(0.01)

            yield _fmt_sse("done", {
                "code": 200, "message": "Stream completed",
                "pig_id": request.pig_id,
                "timestamp": datetime.now().isoformat(),
            })
            
        except Exception as exc:
            logger.error(f"Stream generation error: {exc}")
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
async def generate_farm_briefing_stream(request_data: dict = Body(None)):
    """流式生成全场养殖每日简报（SSE）。"""
    trace_id = request_data.get("trace_id") if request_data else f"briefing_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    async def _gen():
        try:
            from v1.logic.agent_debug_controller import get_or_create_queue, cleanup_queue
            queue = await get_or_create_queue(trace_id)
            
            # [Optimization] 立即发送连接确认，保障前端 SSE 监听器立即激活
            yield _fmt_sse("connected", {"trace_id": trace_id, "status": "established"})
            yield _fmt_sse("status", {"message": "正在路由至简报分析专家..."})
            
            # 开启异步任务，并传入相同的 trace_id
            task = asyncio.create_task(_run_briefing_via_agent(trace_id=trace_id))
            
            full_report = ""
            while not task.done() or not queue.empty():
                try:
                    # 获取事件，带较短超时
                    event = await asyncio.wait_for(queue.get(), timeout=2.0)
                    
                    if event["type"] == "final_answer_chunk":
                        text = event["data"].get("text", "")
                        full_report += text
                        yield _fmt_sse("chunk", {"text": text})
                        await asyncio.sleep(0.02) # 微调打字机流速
                    elif event["type"] in ["thought", "observation", "connected", "debug_event"]:
                        # 转发简报生产过程中的思维链
                        yield _fmt_sse("trace", {
                            "message": event["data"].get("content") or event["data"].get("output") or event["data"].get("message") or "AI 思考中...",
                            "level": "DEBUG" if event["type"] == "thought" else "INFO",
                            "agent": event.get("agent")
                        })
                    elif event["type"] == "error":
                        yield _fmt_sse("error", {
                            "code": 500, "message": "简报生成失败", "detail": event["data"].get("message"),
                        })
                except asyncio.TimeoutError:
                    continue
            
            # 最终补偿
            report = await task
            if not full_report and (not report or report.startswith("error:")):
                yield _fmt_sse("error", {
                    "code": 500, "message": "Briefing failed",
                    "detail": report or "Empty response",
                })
                return
            
            if not full_report:
                yield _fmt_sse("status", {"message": "正在同步简报帧..."})
                chunk_size = 80
                for i in range(0, len(report), chunk_size):
                    yield _fmt_sse("chunk", {"text": report[i:i+chunk_size]})
                    await asyncio.sleep(0.01)
                
            yield _fmt_sse("done", {
                "code": 200, "message": "简报流传输完成",
                "timestamp": datetime.now().isoformat(),
            })
        except Exception as exc:
            logger.error(f"Briefing stream error: {exc}")
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
