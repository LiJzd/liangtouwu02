# -*- coding: utf-8 -*-
"""
v1/db/bm25_retriever.py
基于 rank-bm25 稀疏词库文本检索实现的高级混合检索召回器
支持生长档案库与生命周期时序切片过滤检索
"""

import json
import re
from rank_bm25 import BM25Okapi

# 兼容性 Mock 数据直接载入，确保在本地检索时不强依赖外部数据库环境
from v1.db.migrate_data import MOCK_PIG_DATA, MOCK_PIG_LIFECYCLE_DATA, build_feature_text, _build_slice_embedding_text

def safe_tokenize(text: str) -> list[str]:
    """
    健壮的安全中文/英数分词器
    - 将连续的英文字母、数字、点、下划线聚合为整词
    - 对于非英数字符（如汉字、特殊符号），继续保持单字拆分
    - 过滤所有空白字符
    """
    tokens = []
    # 匹配连续的英文字母/数字/点/下划线，或者匹配单个非空白的中文字符
    pattern = re.compile(r'[a-zA-Z0-9_\.]+|[^\s]')
    for match in pattern.finditer(text):
        token = match.group().strip()
        if token:
            tokens.append(token)
    return tokens

class BM25Retriever:
    """
    轻量级生产级中文 BM25 稀疏词检索召回器
    """
    def __init__(self):
        # 升级为健壮的安全中文/英数分词器
        self.tokenize = safe_tokenize
        self._init_growth_bm25()
        self._init_lifecycle_docs()

    def _init_growth_bm25(self):
        """
        初始化生猪生长特征文档语料库并构建静态 BM25 实例
        """
        self.growth_docs = []
        corpus = []
        for record in MOCK_PIG_DATA:
            text = build_feature_text(record["features"])
            self.growth_docs.append({
                "id": record["id"],
                "text": text,
                "record": record
            })
            corpus.append(self.tokenize(text))
        
        self.growth_bm25 = BM25Okapi(corpus)

    def _init_lifecycle_docs(self):
        """
        加载并打平生命周期切片数据，为时间切片检索提供特征库
        """
        self.lifecycle_docs = []
        for pig in MOCK_PIG_LIFECYCLE_DATA:
            lifecycle = pig["lifecycle"]
            for m in range(1, len(lifecycle)):
                slice_data = lifecycle[:m]
                text = _build_slice_embedding_text(pig["breed"], slice_data)
                self.lifecycle_docs.append({
                    "id": f"{pig['pig_id']}_slice_{m}",
                    "pig_id": pig["pig_id"],
                    "breed": pig["breed"],
                    "slice_month": m,
                    "text": text,
                    "lifecycle_json": json.dumps(lifecycle, ensure_ascii=False)
                })

    def search_growth(self, query: str, top_k: int = 3) -> list[dict]:
        """
        生猪生长特征档案检索
        """
        tokenized_query = self.tokenize(query)
        scores = self.growth_bm25.get_scores(tokenized_query)
        
        # 纯 Python 检索打分最大值排序，零 NumPy 库依赖防御兼容报错
        indexed_scores = list(enumerate(scores))
        indexed_scores.sort(key=lambda x: x[1], reverse=True)
        
        results = []
        for idx, score in indexed_scores[:top_k]:
            doc = self.growth_docs[idx]
            results.append({
                "matched_id": doc["id"],
                "score": float(score),
                "text": doc["text"],
                "record": doc["record"]
            })
        return results

    def search_lifecycle(self, query: str, slice_month: int, breed: str, top_k: int = 3) -> list[dict]:
        """
        生命周期时序对齐检索：在满足指定 breed 和 slice_month 的特定文档子集上构建实时 BM25 索引进行精准召回
        """
        # 1. 过滤符合时间切片与品种的历史断面记录
        filtered_docs = [
            doc for doc in self.lifecycle_docs
            if doc["slice_month"] == slice_month and doc["breed"] == breed
        ]
        
        if not filtered_docs:
            return []

        # 2. 在时间对齐子集上构建现场 BM25Okapi 实例
        corpus = [self.tokenize(doc["text"]) for doc in filtered_docs]
        temp_bm25 = BM25Okapi(corpus)
        
        tokenized_query = self.tokenize(query)
        scores = temp_bm25.get_scores(tokenized_query)
        
        # 排序
        indexed_scores = list(enumerate(scores))
        indexed_scores.sort(key=lambda x: x[1], reverse=True)
        
        results = []
        for idx, score in indexed_scores[:top_k]:
            doc = filtered_docs[idx]
            results.append({
                "matched_id": doc["id"],
                "score": float(score),
                "text": doc["text"],
                "lifecycle_json": doc["lifecycle_json"]
            })
        return results

if __name__ == "__main__":
    retriever = BM25Retriever()
    print("=== [测试] 生猪生长档案稀疏召回 ===")
    growth_results = retriever.search_growth("品种：杜洛克，健康状况：健康")
    for r in growth_results:
        print(f"ID: {r['matched_id']} | 分数: {r['score']:.4f} | 描述: {r['text']}")

    print("\n=== [测试] 生命周期时序对齐稀疏召回 ===")
    lifecycle_results = retriever.search_lifecycle(
        query="体重45.0kg",
        slice_month=3,
        breed="两头乌"
    )
    for r in lifecycle_results:
        print(f"ID: {r['matched_id']} | 分数: {r['score']:.4f} | 描述: {r['text']}")
