# -*- coding: utf-8 -*-
import sys
# 修复 Windows 终端中文输出乱码（确保输出流使用 UTF-8 编码）
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr = open(sys.stderr.fileno(), mode="w", encoding="utf-8", buffering=1)

"""
生猪生命周期时间序列 RAG 系统 (v2 - Lifecycle Edition)
=====================================================

本模块是 RAG（检索增强生成）系统的进阶实现，专门处理“时序性”生猪数据。

【核心业务背景】
传统的 RAG 检索通常只看“当前状态”，但在养猪业务中，生长是一个持续的过程。
同样体重的猪，如果一头是匀速生长，另一头是先慢后快，其未来的出栏预测会完全不同。

【核心技术创新：时间序列切片 (Timeline Slicing)】
为了解决“预测未来”而又不造成“数据穿越”的问题，本系统采用了切片策略：
1. 历史溯源：将一头已经出栏的猪（例如有 6 个月历史）拆解为 5 个不同的“生长断面”。
2. 向量化断面：
   - 截面 M 的向量中文本：仅包含该猪生命周期中前 M 个月的特征。
   - 截面 M 的元数据：包含其从第 M+1 月开始的所有真实数据。
3. 精准匹配：
   - 当用户查询一个处在“第 3 个月”的猪时，系统会强制只在历史猪只的“第 3 个月截面”中寻找最像的样本。
   - 这种“时间对齐”检索极大地提高了生长趋势预测的准确度，并完全杜绝了 AI 提前看到历史结局的弊端。

配置：使用阿里百炼 (DashScope) text-embedding-v3 进行语义向量化。
"""

import os
import json
import shutil
from typing import Any
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import DashScopeEmbeddings
from v1.common.config import get_settings

# ============================================================
# 系统全局配置
# ============================================================
_settings = get_settings()
DASHSCOPE_API_KEY = os.environ.get("DASHSCOPE_API_KEY") or _settings.dashscope_api_key
if DASHSCOPE_API_KEY:
    os.environ["DASHSCOPE_API_KEY"] = DASHSCOPE_API_KEY

# 选用 2048 维度的高性能向量模型
EMBEDDING_MODEL = "text-embedding-v3"
CHROMA_PERSIST_DIR = "./pig_lifecycle_chroma_db"


# ============================================================
# 模拟全生命周期数据
# ============================================================
MOCK_PIG_LIFECYCLE_DATA: list[dict[str, Any]] = [
    {
        "pig_id": "pig_lc_001",
        "breed": "杜洛克",
        "lifecycle": [
            {"month": 1, "feed_count": 45, "feed_duration_mins": 270, "weight_kg": 28.0, "status": "生长中"},
            {"month": 2, "feed_count": 52, "feed_duration_mins": 340, "weight_kg": 45.0, "status": "生长中"},
            {"month": 3, "feed_count": 58, "feed_duration_mins": 400, "weight_kg": 68.0, "status": "生长中"},
            {"month": 4, "feed_count": 60, "feed_duration_mins": 430, "weight_kg": 92.0, "status": "生长中"},
            {"month": 5, "feed_count": 55, "feed_duration_mins": 390, "weight_kg": 115.0, "status": "出厂"},
        ],
    },
    {
        "pig_id": "pig_lc_005",
        "breed": "两头乌", # 重点关注品种
        "lifecycle": [
            {"month": 1, "feed_count": 38, "feed_duration_mins": 230, "weight_kg": 20.0, "status": "生长中"},
            {"month": 2, "feed_count": 42, "feed_duration_mins": 265, "weight_kg": 32.0, "status": "生长中"},
            {"month": 3, "feed_count": 46, "feed_duration_mins": 295, "weight_kg": 46.0, "status": "生长中"},
            {"month": 4, "feed_count": 48, "feed_duration_mins": 310, "weight_kg": 60.0, "status": "生长中"},
            {"month": 5, "feed_count": 50, "feed_duration_mins": 325, "weight_kg": 74.0, "status": "生长中"},
            {"month": 6, "feed_count": 48, "feed_duration_mins": 308, "weight_kg": 88.0, "status": "生长中"},
            {"month": 7, "feed_count": 45, "feed_duration_mins": 285, "weight_kg": 100.0, "status": "出厂"},
        ],
    }
]


# ============================================================
# 辅助解析工具
# ============================================================

def _build_monthly_summary(month_data: dict) -> str:
    """提取单月核心指标，构建语义片段"""
    return (
        f"[第{month_data.get('month')}月: 体重{month_data.get('weight_kg')}kg, "
        f"进食时长{month_data.get('feed_duration_mins')}min]"
    )


def _build_slice_embedding_text(breed: str, months_slice: list[dict]) -> str:
    """
    【关键逻辑】构建“时序感”的向量文本。
    不仅列出每月数据，还计算整体增重斜率，帮助向量模型捕捉生长速度的快慢。
    """
    monthly_details = " | ".join(_build_monthly_summary(m) for m in months_slice)
    weights = [m.get("weight_kg", 0) for m in months_slice]
    # 计算总增重：当前体重 - 入栏体重
    total_gain = round(weights[-1] - weights[0], 1) if len(weights) > 1 else 0.0

    return (
        f"品种:{breed}，"
        f"观察周期:前{len(months_slice)}个月，"
        f"当前最新体重:{weights[-1]}kg，"
        f"累计增长:{total_gain}kg，"
        f"历史序列详情:{monthly_details}"
    )


# ============================================================
# 模块一：向量库生命周期管理
# ============================================================

def init_lifecycle_vector_db(force_rebuild: bool = False) -> Chroma:
    """
    执行“时间切片”入库的核心逻辑。
    """
    embeddings = DashScopeEmbeddings(
        model=EMBEDDING_MODEL,
        dashscope_api_key=DASHSCOPE_API_KEY,
    )

    if os.path.exists(CHROMA_PERSIST_DIR) and not force_rebuild:
        print(f"[RAG-V2] 加载时序向量库：{CHROMA_PERSIST_DIR}")
        return Chroma(persist_directory=CHROMA_PERSIST_DIR, embedding_function=embeddings)

    if os.path.exists(CHROMA_PERSIST_DIR):
        shutil.rmtree(CHROMA_PERSIST_DIR)

    print("[RAG-V2] 正在执行全生命周期 Timeline Slicing 入库建模...")
    texts, metadatas = [], []

    for pig in MOCK_PIG_LIFECYCLE_DATA:
        lifecycle = pig["lifecycle"]
        # 对每个历史记录进行步进切片入库
        # m = 1, 2, 3... (直至倒数第二个月，因为最后一个月已是终点，无预测意义)
        for m in range(1, len(lifecycle)):
            # 仅取前 m 个月作为搜索特征文本
            slice_data = lifecycle[:m]
            texts.append(_build_slice_embedding_text(pig["breed"], slice_data))

            # Metadata 存储完整的 JSON 序列，以便检索后可以提取“未来”
            metadatas.append({
                "pig_id": pig["pig_id"],
                "breed": pig["breed"],
                "slice_month": m, # 标记该向量对应的观测截面
                "lifecycle_json": json.dumps(lifecycle, ensure_ascii=False)
            })

    vectorstore = Chroma.from_texts(
        texts=texts,
        embedding=embeddings,
        metadatas=metadatas,
        persist_directory=CHROMA_PERSIST_DIR,
    )
    print(f"[RAG-V2] 时序建模完成，共生成 {len(texts)} 个时间观测截面。")
    return vectorstore


# ============================================================
# 模块二：智能化生长预测检索 (供 Agent 核心调度)
# ============================================================

_vectorstore: Chroma | None = None

def _get_vectorstore() -> Chroma:
    """懒加载机制"""
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = init_lifecycle_vector_db()
    return _vectorstore


def query_pig_growth_prediction(
    breed: str,
    current_month: int,
    current_month_data: Any, # 支持单月 dict 或历史 list
    top_n: int = 3,
) -> str:
    """
    【Agent 工具入口】基于历史轨迹的未来预测检索。
    
    工作原理：
    1. 根据用户提供的“目标猪当前前 M 个月数据”，在库中检索“历史上同样处在第 M 个月，且长势最像”的案例。
    2. 提取这些历史案例从 M+1 个月开始的所有真实生长数据。
    3. 返回给 Agent，作为它生成预测报告的“事实依据”。
    """
    # 兼容性处理：若用户只传了当前月，手动包装成序列
    if isinstance(current_month_data, dict):
        current_sequence = [{**current_month_data, "month": current_month}]
    else:
        current_sequence = current_month_data

    # 构建查询向量
    query_text = _build_slice_embedding_text(breed, current_sequence)
    db = _get_vectorstore()

    # 执行带过滤条件的检索：强制 slice_month == current_month，确保时间维度对齐
    results = db.similarity_search_with_score(
        query=query_text,
        k=top_n,
        filter={"slice_month": current_month}
    )

    output_list = []
    for doc, score in results:
        meta = doc.metadata
        full_history = json.loads(meta["lifecycle_json"])
        
        # ✅ 关键步骤：截取“未来”
        # 获取第 current_month 月之后的所有数据
        future_part = [m for m in full_history if m["month"] > current_month]

        output_list.append({
            "matched_pig": meta["pig_id"],
            "similarity_distance": round(float(score), 4),
            "historical_future_track": future_part # 这就是 Agent 预测未来的参考答案
        })

    return json.dumps({
        "query_context": f"{breed}龄期{current_month}月",
        "top_matches": output_list
    }, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    # 执行演示检索
    init_lifecycle_vector_db(force_rebuild=True)
    print("\n--- [测试] 检索两头乌第3个月后的预期生长轨迹 ---")
    test_data = {"feed_count": 45, "feed_duration_mins": 300, "weight_kg": 45.0}
    print(query_pig_growth_prediction("两头乌", 3, test_data))
