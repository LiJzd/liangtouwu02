# -*- coding: utf-8 -*-
import sys
# 修复 Windows 终端中文输出乱码（确保输出流使用 UTF-8 编码）
if sys.stdout.encoding != 'utf-8':
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)
if sys.stderr.encoding != 'utf-8':
    sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', buffering=1)

"""
生猪生长轨迹预测 RAG 系统核心实现
=========================

本模块负责构建和查询“生猪生长知识图谱”的本地向量化版本。
它实现了将生猪的静态特征（品种、日龄等）转化为高维向量，并利用向量数据库进行语义匹配的功能。

核心模块划分：
1. 向量库构建 (Database Initialization)：将 Mock 历史数据入库。
2. 检索工具 (Retrieval Tool)：提供给 Agent 调用的函数，用于召回相似历史猪只的“未来信息”。

⚠️ 数据流转安全约束（预防数据泄露）：
- 用于 Embedding 的文本仅包含“当前”已知的生理特征（即输入特征）。
- 该猪只在历史上的“后续真实生长表现”仅存储在 Metadata（元数据）中。
- 在计算相似度时，算法仅对比“当前长得像不想”，而不允许看到“未来结果”，确保预测的客观性。
"""

import os
import json
import shutil
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import DashScopeEmbeddings  # 阿里百炼官方 Embedding 接口

# ============================================================
# 全局配置（阿里百炼 / DashScope）
# ============================================================

# 阿里百炼 API Key (建议通过环境变量注入，此处为演示用的默认 Key)
DASHSCOPE_API_KEY = "sk-564244e28e5d4c35bf9fa9c9565f0efb"
os.environ["OPENAI_API_KEY"] = DASHSCOPE_API_KEY

# 阿里百炼 OpenAI 兼容端点：允许使用统一的 OpenAI 协议调用阿里云模型
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

# Embedding 模型：text-embedding-v3 是目前性能最优的模型之一，适合处理农业专业领域的中文文本
EMBEDDING_MODEL = "text-embedding-v3"

# Chroma 向量数据库本地存储路径
CHROMA_PERSIST_DIR = "./pig_chroma_db"

# ============================================================
# 模拟知识库数据 (Knowledge Base)
# ============================================================
# 每条记录包含：
# - features: 决定了“它长什么样”（用于向量化检索）
# - trajectory: 决定了“它后来长成了什么样”（作为预测的黄金标准参考）
MOCK_PIG_DATA = [
    {
        "id": "pig_001",
        "features": {"breed": "杜洛克", "age_days": 90, "weight_kg": 45.0, "daily_feed_kg": 1.8, "health_status": "健康"},
        "trajectory": {"days_to_slaughter": 85, "final_weight_kg": 115.0, "disease_occurred": False, "avg_daily_gain_g": 823}
    },
    {
        "id": "pig_002",
        "features": {"breed": "杜洛克", "age_days": 95, "weight_kg": 48.5, "daily_feed_kg": 2.0, "health_status": "健康"},
        "trajectory": {"days_to_slaughter": 80, "final_weight_kg": 118.0, "disease_occurred": False, "avg_daily_gain_g": 856}
    },
    {
        "id": "pig_003",
        "features": {"breed": "长白", "age_days": 85, "weight_kg": 40.0, "daily_feed_kg": 1.6, "health_status": "轻微咳嗽"},
        "trajectory": {"days_to_slaughter": 100, "final_weight_kg": 108.0, "disease_occurred": True, "avg_daily_gain_g": 680}
    },
    {
        "id": "pig_004",
        "features": {"breed": "大白", "age_days": 100, "weight_kg": 55.0, "daily_feed_kg": 2.2, "health_status": "健康"},
        "trajectory": {"days_to_slaughter": 75, "final_weight_kg": 122.0, "disease_occurred": False, "avg_daily_gain_g": 893}
    },
    {
        "id": "pig_006",
        "features": {"breed": "两头乌", "age_days": 110, "weight_kg": 50.0, "daily_feed_kg": 1.9, "health_status": "健康"},
        "trajectory": {"days_to_slaughter": 120, "final_weight_kg": 105.0, "disease_occurred": False, "avg_daily_gain_g": 458}
    },
    {
        "id": "pig_007",
        "features": {"breed": "两头乌", "age_days": 115, "weight_kg": 52.0, "daily_feed_kg": 2.0, "health_status": "轻微腹泻"},
        "trajectory": {"days_to_slaughter": 130, "final_weight_kg": 100.0, "disease_occurred": True, "avg_daily_gain_g": 369}
    }
]


def build_feature_text(features: dict) -> str:
    """
    将特征字典转换为“自然语言描述”，便于 Embedding 模型理解。
    
    例如：将 {"breed": "杜洛克", "age": 90} 转换为 "品种：杜洛克，当前日龄：90天..."
    这种转换能利用预训练大模型在中文语境下的语义相关性理解能力。
    """
    return (
        f"品种：{features['breed']}，"
        f"当前日龄：{features['age_days']}天，"
        f"当前体重：{features['weight_kg']}公斤，"
        f"日均采食量：{features['daily_feed_kg']}公斤，"
        f"健康状况：{features['health_status']}"
    )


# ============================================================
# 模块一：Chroma 向量库管理
# ============================================================

def init_vector_db(force_rebuild: bool = False) -> Chroma:
    """
    向量库初始化工厂函数。
    负责将 Mock 数据转换为向量并持久化到本地。
    """
    # 实例化阿里的 Embedding 模型集成类
    embeddings = DashScopeEmbeddings(
        model=EMBEDDING_MODEL,
        dashscope_api_key=DASHSCOPE_API_KEY,
    )

    # 如果库已存在且无需重建，直接从磁盘加载以提升启动速度
    if os.path.exists(CHROMA_PERSIST_DIR) and not force_rebuild:
        print(f"[RAG] 正在加载现有向量库索引：{CHROMA_PERSIST_DIR}")
        return Chroma(persist_directory=CHROMA_PERSIST_DIR, embedding_function=embeddings)

    # 物理清除旧索引数据
    if os.path.exists(CHROMA_PERSIST_DIR):
        shutil.rmtree(CHROMA_PERSIST_DIR)

    print("[RAG] 正在根据模拟数据构建全新的生猪知识图谱向量库...")
    texts = []
    metadatas = []

    for record in MOCK_PIG_DATA:
        # 1. 提取用于对比的向量文本
        texts.append(build_feature_text(record["features"]))
        
        # 2. 构建随向量一同存储的 Metadata (类似于数据库的附属字段)
        # 这里包含了最关键的“后续生长轨迹”，供 Agent 检索出来后做参考
        metadata = {
            "pig_id": record["id"],
            "breed": record["features"]["breed"],
            "traj_days_to_slaughter": record["trajectory"]["days_to_slaughter"],
            "traj_final_weight_kg": record["trajectory"]["final_weight_kg"],
            "traj_disease_occurred": record["trajectory"]["disease_occurred"]
        }
        metadatas.append(metadata)

    # 执行云端 Embedding 请求并将结果批量写入本地向量库 (Chroma)
    vectorstore = Chroma.from_texts(
        texts=texts,
        embedding=embeddings,
        metadatas=metadatas,
        persist_directory=CHROMA_PERSIST_DIR,
    )

    print(f"[RAG] 向量库构建成功，已入库 {len(texts)} 头生猪的生长档案。")
    return vectorstore


# ============================================================
# 模块二：检索器封装（供 Agent 工具调用）
# ============================================================

_vectorstore: Chroma | None = None

def _get_vectorstore() -> Chroma:
    """单例获取向量库，避免多次网络连接模型初始化"""
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = init_vector_db()
    return _vectorstore


def query_similar_pig_records(
    breed: str,
    age_days: int,
    weight_kg: float,
    top_n: int = 3,
) -> str:
    """
    RAG 本地检索核心函数：
    根据当前生猪输入的生理指标，去“历史长河”中寻找长得最像的那几头。
    
    返回：包含历史生长“后来表现”的 JSON 字符串。
    """
    # 将输入参数组装成与入库文本格式一致的 Query
    query_text = f"品种：{breed}，当前日龄：{age_days}天，当前体重：{weight_kg}公斤"
    
    db = _get_vectorstore()
    # 执行相似度搜索，k=top_n
    # 返回的内容不仅包含原文，还包含我们预先埋伏在 Metadata 里的后续轨迹
    results = db.similarity_search_with_score(query=query_text, k=top_n)

    if not results:
        return json.dumps({"status": "error", "message": "无法匹配相似案例"}, ensure_ascii=False)

    output = []
    for doc, score in results:
        meta = doc.metadata
        output.append({
            "matched_pig_id": meta.get("pig_id"),
            # 这里的 trajectory 是从 Metadata 里拿到的“历史结局”
            "historical_outcome": {
                "final_weight": meta.get("traj_final_weight_kg"),
                "days_observed": meta.get("traj_days_to_slaughter"),
                "had_disease": meta.get("traj_disease_occurred")
            },
            "similarity_score": round(float(score), 4) # 距离分数，越低越相似
        })

    return json.dumps({
        "status": "success",
        "match_count": len(output),
        "results": output
    }, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    # 测试代码：强制重建数据库并执行一次检索
    init_vector_db(force_rebuild=True)
    print("\n--- 检索测试 (杜洛克偏小个体) ---")
    print(query_similar_pig_records("杜洛克", 92, 44))
