"""
生猪检测报告控制器 — 双轨架构 (Numerical + Cognitive) 核心编排
(等效于 SpringBoot 的 InspectionController)

功能说明：
1. 业务编排：协调 MySQL 工具、数值引擎（曲线拟合）与认知引擎（LLM/RAG）生成检测报告。
2. 双模式输出：支持传统的同步 JSON 返回及现代的 SSE (Server-Sent Events) 流式返回。
3. 容错处理：包含完善的 JSON 解析校验、数据库空值处理及异常状态捕获。

调用链路：
前端页面 → Java 后端 (Spring Boot) → POST /api/v1/inspection/generate → 本控制器
本控制器流程：
[数据层] MySQL 查询猪只档案 -> 
[逻辑层] 提取体重序列与生命周期数据 -> 
[算法层] 调用 pig_agent 进行双轨分析 (数值拟合 + 专家系统推导) -> 
[展现层] 返回 Markdown 格式的详细检测报告
"""

from datetime import datetime
import asyncio
import json
import os
import sys
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# 动态扩展 Python 搜索路径，以便导入同级的算法核心模块
# 这种方式允许控制器直接访问位于 ../../pig_rag 目录中的逻辑
sys.path.append(os.path.join(os.path.dirname(__file__), '../../pig_rag'))

# 导入业务层核心函数
# run_dual_track_inspection: 数值与认知双轨分析引擎
# get_pig_info_by_id_sync: 数据库同步查询工具
from pig_agent import run_dual_track_inspection
from mysql_tool import get_pig_info_by_id_sync

router = APIRouter()


# ==================== 请求与响应 DTO 定义 ====================

class InspectionRequest(BaseModel):
    """报告生成请求体"""
    pig_id: str = Field(..., min_length=1, max_length=64, description="生猪唯一识别码")


class InspectionResponse(BaseModel):
    """同步响应结构体 (标准 JSON)"""
    code: int = Field(default=200, description="业务状态码")
    message: str = Field(default="报告生成成功")
    pig_id: str
    report: str # 包含 Markdown 格式的分析报告内容
    timestamp: datetime = Field(default_factory=datetime.now)


class ErrorResponse(BaseModel):
    """统一错误返回 DTO"""
    code: int
    message: str
    detail: Optional[str] = None
    pig_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


# ==================== 辅助工具函数 ====================

def _format_sse(event: str, data: dict) -> str:
    """
    格式化 SSE (Server-Sent Events) 数据帧
    
    SSE 格式要求：
    event: 事件名称
    data: JSON 序列化后的数据
    \n\n (必须以双换行结束)
    """
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _run_inspection(pig_id: str) -> str:
    """
    核心业务流编排：MySQL 查询 → 逻辑提取 → 算法调用
    
    该函数封装了整个报告生成的计算密集型过程。
    """
    # ── 步骤 1: 从 MySQL 获取生猪原始档案 ──
    # 使用同步工具获取 JSON 字符串格式的猪只数据
    pig_raw = get_pig_info_by_id_sync(pig_id)

    try:
        pig_info = json.loads(pig_raw)
    except Exception:
        pig_info = {"error": f"数据库返回数据解析失败: {pig_raw}"}

    if "error" in pig_info:
        return f"error: {pig_info['error']}"

    # 提取基本属性
    breed = str(pig_info.get("breed") or "两头乌")
    lifecycle = pig_info.get("lifecycle")
    if not isinstance(lifecycle, list) or not lifecycle:
        return "error: 数据库中该猪只无生命周期历史数据"

    # ── 步骤 2: 数据预处理 ──
    # 获取最后一个记录的月份作为当前月份
    current_month = int(pig_info.get("current_month") or len(lifecycle))
    
    # 将 lifecycle (月级时序数据) 转换为算法所需的体重序列数组
    weight_series = [float(m.get("weight_kg", 0)) for m in lifecycle if isinstance(m, dict)]

    # 简单的日龄估算模型 (1个月约等于30天)
    current_day_age = current_month * 30

    # ── 步骤 3: 启动算法引擎 ──
    # 进入双轨内核：数值轨道进行 Gompertz 曲线拟合；认知轨道利用 RAG 进行专家知识推导。
    report = run_dual_track_inspection(
        pig_id=pig_id,
        breed=breed,
        current_day_age=current_day_age,
        current_weight_series=weight_series,
        verbose=False, # 关闭详细调试日志，生产环境更整洁
    )

    return report


# ==================== API 端点实现 ====================

@router.post("/generate", response_model=InspectionResponse, tags=["生猪检测"])
async def generate_inspection_report(request: InspectionRequest):
    """
    接口 1：标准同步报告生成接口
    
    由于算法推理是计算密集型同步任务，使用 run_in_executor 将其放入线程池执行，
    避免长时间的计算阻塞 FastAPI 的异步主事件循环。
    """
    try:
        loop = asyncio.get_running_loop()
        # 在独立的线程池中运行同步阻塞的 _run_inspection
        report = await loop.run_in_executor(
            None,
            lambda: _run_inspection(pig_id=request.pig_id),
        )

        if not report or report.startswith("error"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"后端引擎报告生成异常: {report}",
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
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"算法后端服务响应超时或内部异常: {str(e)}",
        )


@router.post("/generate/stream", tags=["生猪检测"])
async def generate_inspection_report_stream(request: InspectionRequest):
    """
    接口 2：流式 (SSE) 报告生成接口
    
    适用于打字机效果展示，或者当报告生成时间较长时防止前端 HTTP 等待超时。
    """
    async def event_generator():
        try:
            # 状态推送：告知前端后端已开始处理
            yield _format_sse("status", {"message": "正在初始化双轨分析引擎..."})

            loop = asyncio.get_running_loop()
            # 执行核心分析任务
            report = await loop.run_in_executor(
                None,
                lambda: _run_inspection(pig_id=request.pig_id),
            )

            if not report or report.startswith("error"):
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

            yield _format_sse("status", {"message": "正在润色诊断报告..."})

            # 对生成的 Markdown 进行切片模拟流式传输 (打字机效果)
            chunk_size = 120
            for i in range(0, len(report), chunk_size):
                yield _format_sse("chunk", {"text": report[i : i + chunk_size]})
                # 微小停顿，增加前端视觉上的“生成感”
                await asyncio.sleep(0.01)

            # 发送结束标记
            yield _format_sse(
                "done",
                {
                    "code": 200,
                    "message": "分析流传输完成",
                    "pig_id": request.pig_id,
                    "timestamp": datetime.now().isoformat(),
                },
            )
        except Exception as e:
            yield _format_sse(
                "error",
                {
                    "code": 500,
                    "message": "算法节点不可用",
                    "detail": str(e),
                    "pig_id": request.pig_id,
                },
            )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache", # 禁用缓存确保实时性
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no", # 禁用 Nginx 等反向代理的缓冲，实现真正的流式输出
        },
    )


@router.post("/briefing", tags=["生猪检测"])
async def generate_farm_briefing():
    """
    接口 3：全场每日简报生成接口
    汇总全场所有猪只的 7 日行为趋势，识别异常并给出专家建议。
    """
    try:
        from pig_agent import run_farm_daily_briefing
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            run_farm_daily_briefing
        )
        
        if not result or (isinstance(result, dict) and result.get("report", "").startswith("error")):
             raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"简报引擎异常: {result}",
            )
            
        return {
            "code": 200,
            "message": "每日简报生成成功",
            "data": {
                "report": result["report"],
                "summary": result["summary"],
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"简报生成失败: {str(e)}",
        )


# ==================== 服务监控 ====================

@router.get("/health", tags=["系统监控"])
async def health_check():
    """检测报告组件存活检查"""
    return {
        "status": "UP",
        "service": "Liangtouwu-Report-Engine-v1",
        "arch": "Dual-Track (Numerical & Cognitive)",
        "timestamp": datetime.now(),
    }
