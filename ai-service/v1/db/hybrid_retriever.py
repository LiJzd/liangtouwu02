# -*- coding: utf-8 -*-
"""
v1/db/hybrid_retriever.py
生猪特征与全生命周期混合检索（Dense 召回 + Sparse 召回 + RRF 融合 + 阿里百炼重排与优雅降级）模块
"""

import os
import sys
import json
import logging
from dashscope import TextReRank
from v1.common.config import get_settings
from v1.db.milvus_client import get_milvus_client
from v1.db.bm25_retriever import BM25Retriever
from v1.db.migrate_data import get_embedding_1536, _build_slice_embedding_text

# 设置 logging 确保能在 API 调用错误时打印警告日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HybridRetriever")

class HybridRetriever:
    """
    生产级混合检索召回器
    融合了 Milvus (Dense) 检索与 BM25 (Sparse) 检索，并通过 RRF (Reciprocal Rank Fusion) 和百炼重排提升排序精度
    """
    def __init__(self):
        self.bm25_retriever = BM25Retriever()
        self.milvus_client = get_milvus_client()
        settings = get_settings()
        self.api_key = os.environ.get("DASHSCOPE_API_KEY") or getattr(settings, "dashscope_api_key", None)

    async def search_growth(self, breed: str, age_days: int, weight_kg: float, top_k: int = 3, rrf_k: int = 60) -> list[dict]:
        """
        生猪生长档案混合检索
        """
        # 1. 生成特征查询文本
        query_text = f"品种：{breed}，当前日龄：{age_days}天，当前体重：{weight_kg}公斤"
        
        # 2. 计算 1536 维 Padding 向量
        if not self.api_key:
            logger.warning("未检测到 API Key，将无法调用 Dense 召回，优雅降级为纯 BM25 稀疏检索。")
            return self.bm25_retriever.search_growth(query_text, top_k=top_k)

        try:
            vector = get_embedding_1536(query_text, self.api_key)
        except Exception as e:
            logger.warning(f"计算 Embedding 失败: {e}，优雅降级为纯 BM25 稀疏检索。")
            return self.bm25_retriever.search_growth(query_text, top_k=top_k)

        # 3. Dense 召回 (Milvus)
        dense_results = []
        try:
            # 显式载入集合，防止 Collection 'pig_growth_collection' is in state 'released' 报错
            self.milvus_client.load_collection("pig_growth_collection")
            
            milvus_res = self.milvus_client.search(
                collection_name="pig_growth_collection",
                data=[vector],
                limit=15,
                output_fields=["*"]
            )
            if milvus_res and len(milvus_res) > 0:
                for r in milvus_res[0]:
                    entity = r.get("entity", r)
                    r_id = r.get("id") or entity.get("id")
                    r_text = entity.get("text")
                    r_breed = entity.get("breed")
                    r_age_days = entity.get("age_days")
                    r_weight_kg = entity.get("weight_kg")
                    r_daily_feed_kg = entity.get("daily_feed_kg")
                    r_health_status = entity.get("health_status")
                    r_traj_days_to_slaughter = entity.get("traj_days_to_slaughter")
                    r_traj_final_weight_kg = entity.get("traj_final_weight_kg")
                    r_traj_disease_occurred = entity.get("traj_disease_occurred")
                    r_traj_avg_daily_gain_g = entity.get("traj_avg_daily_gain_g")
                    
                    dense_results.append({
                        "matched_id": r_id,
                        "score": float(r.get("distance", 0.0)),
                        "text": r_text,
                        "record": {
                            "id": r_id,
                            "features": {
                                "breed": r_breed,
                                "age_days": int(r_age_days) if r_age_days is not None else 0,
                                "weight_kg": float(r_weight_kg) if r_weight_kg is not None else 0.0,
                                "daily_feed_kg": float(r_daily_feed_kg) if r_daily_feed_kg is not None else 0.0,
                                "health_status": r_health_status
                            },
                            "trajectory": {
                                "days_to_slaughter": int(r_traj_days_to_slaughter) if r_traj_days_to_slaughter is not None else 0,
                                "final_weight_kg": float(r_traj_final_weight_kg) if r_traj_final_weight_kg is not None else 0.0,
                                "disease_occurred": bool(r_traj_disease_occurred) if r_traj_disease_occurred is not None else False,
                                "avg_daily_gain_g": int(r_traj_avg_daily_gain_g) if r_traj_avg_daily_gain_g is not None else 0
                            }
                        }
                    })
        except Exception as e:
            logger.warning(f"Milvus Dense 检索异常: {e}")

        # 4. Sparse 召回 (BM25)
        sparse_results = []
        try:
            sparse_results = self.bm25_retriever.search_growth(query_text, top_k=15)
        except Exception as e:
            logger.warning(f"BM25 Sparse 检索异常: {e}")

        # 5. RRF 融合排序
        all_docs = {}
        for doc in dense_results:
            all_docs[doc["matched_id"]] = doc
        for doc in sparse_results:
            all_docs[doc["matched_id"]] = doc

        if not all_docs:
            return []

        dense_ranks = {doc["matched_id"]: rank for rank, doc in enumerate(dense_results, 1)}
        sparse_ranks = {doc["matched_id"]: rank for rank, doc in enumerate(sparse_results, 1)}

        rrf_scores = {}
        for doc_id in all_docs:
            score = 0.0
            if doc_id in dense_ranks:
                score += 1.0 / (rrf_k + dense_ranks[doc_id])
            if doc_id in sparse_ranks:
                score += 1.0 / (rrf_k + sparse_ranks[doc_id])
            rrf_scores[doc_id] = score

        # 按照 RRF 分数排序
        sorted_docs = sorted(all_docs.values(), key=lambda x: rrf_scores[x["matched_id"]], reverse=True)

        # 6. 百炼 gte-rerank 优雅降级重排
        candidates = sorted_docs[:10]
        doc_texts = [c["text"] for c in candidates]

        rerank_success = False
        if self.api_key and doc_texts:
            try:
                resp = TextReRank.call(
                    model="gte-rerank",
                    query=query_text,
                    documents=doc_texts,
                    api_key=self.api_key
                )
                if resp.status_code == 200 and resp.output and hasattr(resp.output, "results") and resp.output.results:
                    # 初始化候选 rerank_score
                    for c in candidates:
                        c["rerank_score"] = 0.0
                    for item in resp.output.results:
                        idx = item.index
                        if idx < len(candidates):
                            candidates[idx]["rerank_score"] = item.relevance_score
                            candidates[idx]["score"] = item.relevance_score
                    
                    candidates.sort(key=lambda x: x["rerank_score"], reverse=True)
                    # 补足数量
                    final_results = candidates[:top_k]
                    rerank_success = True
                else:
                    logger.warning(f"百炼 Rerank 响应非 200: {resp.code} - {resp.message}")
            except Exception as e:
                logger.warning(f"百炼 Rerank 调用遭遇异常: {e}")

        # 安全降级防御：若重排失败或不可用，优雅地降级为直接使用 RFF 排序得分的前 top_k 个结果返回
        if not rerank_success:
            logger.info("百炼重排不可用或失败，已自动降级为 RRF 倒数排名融合分数排序输出。")
            for c in sorted_docs:
                c["score"] = rrf_scores[c["matched_id"]]
            final_results = sorted_docs[:top_k]

        return final_results

    async def search_lifecycle(self, breed: str, current_month: int, current_month_data: list[dict], top_k: int = 3, rrf_k: int = 60) -> list[dict]:
        """
        生命周期时序对齐混合检索
        """
        # 1. 生成时序查询特征文本
        query_text = _build_slice_embedding_text(breed, current_month_data)

        # 2. 计算 1536 维 Padding 向量
        if not self.api_key:
            logger.warning("未检测到 API Key，将无法调用 Dense 召回，优雅降级为纯 BM25 稀疏检索。")
            return self.bm25_retriever.search_lifecycle(query_text, slice_month=current_month, breed=breed, top_k=top_k)

        try:
            vector = get_embedding_1536(query_text, self.api_key)
        except Exception as e:
            logger.warning(f"计算 Embedding 失败: {e}，优雅降级为纯 BM25 稀疏检索。")
            return self.bm25_retriever.search_lifecycle(query_text, slice_month=current_month, breed=breed, top_k=top_k)

        # 3. Dense 召回 (Milvus)
        dense_results = []
        try:
            # 显式载入集合，防止 Collection 'pig_lifecycle_collection' is in state 'released' 报错
            self.milvus_client.load_collection("pig_lifecycle_collection")
            
            filter_expr = f"slice_month == {current_month} and breed == '{breed}'"
            milvus_res = self.milvus_client.search(
                collection_name="pig_lifecycle_collection",
                data=[vector],
                filter=filter_expr,
                limit=15,
                output_fields=["*"]
            )
            if milvus_res and len(milvus_res) > 0:
                for r in milvus_res[0]:
                    entity = r.get("entity", r)
                    r_id = r.get("id") or entity.get("id")
                    r_text = entity.get("text")
                    r_lifecycle_json = entity.get("lifecycle_json")
                    
                    dense_results.append({
                        "matched_id": r_id,
                        "score": float(r.get("distance", 0.0)),
                        "text": r_text,
                        "lifecycle_json": r_lifecycle_json
                    })
        except Exception as e:
            logger.warning(f"Milvus Dense 检索异常: {e}")

        # 4. Sparse 召回 (BM25)
        sparse_results = []
        try:
            sparse_results = self.bm25_retriever.search_lifecycle(
                query_text, slice_month=current_month, breed=breed, top_k=15
            )
        except Exception as e:
            logger.warning(f"BM25 Sparse 检索异常: {e}")

        # 5. RRF 融合排序
        all_docs = {}
        for doc in dense_results:
            all_docs[doc["matched_id"]] = doc
        for doc in sparse_results:
            all_docs[doc["matched_id"]] = doc

        if not all_docs:
            return []

        dense_ranks = {doc["matched_id"]: rank for rank, doc in enumerate(dense_results, 1)}
        sparse_ranks = {doc["matched_id"]: rank for rank, doc in enumerate(sparse_results, 1)}

        rrf_scores = {}
        for doc_id in all_docs:
            score = 0.0
            if doc_id in dense_ranks:
                score += 1.0 / (rrf_k + dense_ranks[doc_id])
            if doc_id in sparse_ranks:
                score += 1.0 / (rrf_k + sparse_ranks[doc_id])
            rrf_scores[doc_id] = score

        # 按照 RRF 分数排序
        sorted_docs = sorted(all_docs.values(), key=lambda x: rrf_scores[x["matched_id"]], reverse=True)

        # 6. 百炼 gte-rerank 优雅降级重排
        candidates = sorted_docs[:10]
        doc_texts = [c["text"] for c in candidates]

        rerank_success = False
        if self.api_key and doc_texts:
            try:
                resp = TextReRank.call(
                    model="gte-rerank",
                    query=query_text,
                    documents=doc_texts,
                    api_key=self.api_key
                )
                if resp.status_code == 200 and resp.output and hasattr(resp.output, "results") and resp.output.results:
                    for c in candidates:
                        c["rerank_score"] = 0.0
                    for item in resp.output.results:
                        idx = item.index
                        if idx < len(candidates):
                            candidates[idx]["rerank_score"] = item.relevance_score
                            candidates[idx]["score"] = item.relevance_score
                    
                    candidates.sort(key=lambda x: x["rerank_score"], reverse=True)
                    final_results = candidates[:top_k]
                    rerank_success = True
                else:
                    logger.warning(f"百炼 Rerank 响应非 200: {resp.code} - {resp.message}")
            except Exception as e:
                logger.warning(f"百炼 Rerank 调用遭遇异常: {e}")

        # 安全降级防御
        if not rerank_success:
            logger.info("百炼重排不可用或失败，已自动降级为 RRF 倒数排名融合分数排序输出。")
            for c in sorted_docs:
                c["score"] = rrf_scores[c["matched_id"]]
            final_results = sorted_docs[:top_k]

        return final_results

if __name__ == "__main__":
    import asyncio
    
    async def main():
        print("=== [测试] HybridRetriever ===")
        retriever = HybridRetriever()
        
        # 测试生长档案混合检索
        print("\n--- 1. 生长档案混合检索测试 ---")
        growth_res = await retriever.search_growth(breed="杜洛克", age_days=90, weight_kg=45.0)
        for r in growth_res:
            print(f"ID: {r['matched_id']} | Score: {r['score']:.4f} | Text: {r['text']}")

        # 测试生命周期时序对齐混合检索
        print("\n--- 2. 生命周期时序对齐混合检索测试 ---")
        mock_slice = [
            {"month": 1, "feed_count": 35, "feed_duration_mins": 210, "weight_kg": 10.2, "status": "生长中"},
            {"month": 2, "feed_count": 40, "feed_duration_mins": 250, "weight_kg": 20.8, "status": "生长中"},
            {"month": 3, "feed_count": 44, "feed_duration_mins": 275, "weight_kg": 31.5, "status": "生长中"}
        ]
        lifecycle_res = await retriever.search_lifecycle(
            breed="两头乌",
            current_month=3,
            current_month_data=mock_slice
        )
        for r in lifecycle_res:
            print(f"ID: {r['matched_id']} | Score: {r['score']:.4f} | Text: {r['text']}")

    asyncio.run(main())
