# -*- coding: utf-8 -*-
import sys
# 修复 Windows 终端中文输出乱码（确保输出流使用 UTF-8 编码）
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr = open(sys.stderr.fileno(), mode="w", encoding="utf-8", buffering=1)

"""
金华两头乌 RAG 向量检索控制器 (Liangtouwu RAG Controller)
======================================================
挂载并暴露两头乌专属知识库的语义搜索和向量库重建接口。
"""

import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

# 动态计算路径保障
from pig_rag.liangtouwu_knowledge_rag import (
    query_liangtouwu_knowledge,
    init_liangtouwu_knowledge_db
)

router = APIRouter()
logger = logging.getLogger("liangtouwu_rag_controller")


# ============================================================
# Pydantic 规范 DTO 模型定义
# ============================================================

class LiangtouwuQueryRequest(BaseModel):
    query: str = Field(..., description="检索的语义文本查询词", min_length=1)
    top_n: int = Field(default=3, description="返回的最优匹配条数", ge=1, le=10)


class LiangtouwuQueryItem(BaseModel):
    text: str = Field(..., description="匹配的语义文本内容")
    score: float = Field(..., description="匹配的距离度量得分（Chroma返回L2距离，越小表示越相似）")
    metadata: Dict[str, Any] = Field(..., description="匹配段落的相关元数据")


class LiangtouwuQueryResponse(BaseModel):
    query: str
    results: List[LiangtouwuQueryItem]


class LiangtouwuInitRequest(BaseModel):
    force_rebuild: bool = Field(default=False, description="是否强制重新构建本地的 ChromaDB 向量库")


class LiangtouwuInitResponse(BaseModel):
    status: str
    message: str


# ============================================================
# API 路由映射实现
# ============================================================

@router.post("/query", response_model=LiangtouwuQueryResponse)
async def query_rag(payload: LiangtouwuQueryRequest) -> LiangtouwuQueryResponse:
    """
    POST /api/v1/rag/liangtouwu/query
    
    提取 query 查询词，调用两头乌本地知识检索，返回排名前 Top-N 的匹配切片与相似度距离得分。
    """
    logger.info(f"[API] 收到两头乌 RAG 查询请求: query='{payload.query}', top_n={payload.top_n}")
    try:
        # 执行核心语义检索
        results = query_liangtouwu_knowledge(payload.query, top_n=payload.top_n)
        
        # 封装为规范响应体
        query_items = [
            LiangtouwuQueryItem(
                text=item["text"],
                score=item["score"],
                metadata=item["metadata"]
            )
            for item in results
        ]
        
        return LiangtouwuQueryResponse(
            query=payload.query,
            results=query_items
        )
    except Exception as e:
        logger.error(f"[API] 两头乌 RAG 查询发生系统异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"两头乌 RAG 查询失败: {str(e)}"
        )


@router.post("/init", response_model=LiangtouwuInitResponse)
async def init_rag_db(payload: LiangtouwuInitRequest) -> LiangtouwuInitResponse:
    """
    POST /api/v1/rag/liangtouwu/init
    
    支持通过 API 接口物理性重建/初始化两头乌本地 Chroma 向量数据库。
    """
    logger.info(f"[API] 收到两头乌 RAG 数据库初始化请求: force_rebuild={payload.force_rebuild}")
    try:
        # 物理触发 Chroma 构建
        init_liangtouwu_knowledge_db(force_rebuild=payload.force_rebuild)
        
        msg = "本地向量数据库物理重建成功！" if payload.force_rebuild else "本地向量数据库初始化/验证成功。"
        return LiangtouwuInitResponse(
            status="success",
            message=msg
        )
    except Exception as e:
        logger.error(f"[API] 两头乌 RAG 数据库初始化失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"初始化两头乌 RAG 数据库失败: {str(e)}"
        )
