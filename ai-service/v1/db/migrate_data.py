# -*- coding: utf-8 -*-
"""
v1/db/migrate_data.py
生猪历史 Mock 数据及全生命周期切片数据清洗、向量化计算及 Milvus 本地迁移写入模块
"""

import os
import sys
import json
import time
import dashscope
from dashscope import TextEmbedding
from v1.common.config import get_settings
from v1.db.milvus_client import get_milvus_client, init_milvus_collections

# ============================================================
# 1. 模拟历史生猪知识库与全生命周期 Mock 数据定义
# ============================================================

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

MOCK_PIG_LIFECYCLE_DATA = [
    {
        "pig_id": "pig_lc_001",
        "breed": "杜洛克",
        "lifecycle": [
            {"month": 1, "feed_count": 45, "feed_duration_mins": 270, "weight_kg": 28.2, "status": "生长中"},
            {"month": 2, "feed_count": 52, "feed_duration_mins": 340, "weight_kg": 48.5, "status": "生长中"},
            {"month": 3, "feed_count": 58, "feed_duration_mins": 400, "weight_kg": 72.3, "status": "生长中"},
            {"month": 4, "feed_count": 60, "feed_duration_mins": 430, "weight_kg": 96.8, "status": "生长中"},
            {"month": 5, "feed_count": 55, "feed_duration_mins": 390, "weight_kg": 118.5, "status": "出厂"},
        ],
    },
    {
        "pig_id": "pig_lc_005",
        "breed": "两头乌", 
        "lifecycle": [
            {"month": 1, "feed_count": 35, "feed_duration_mins": 210, "weight_kg": 10.2, "status": "生长中"},
            {"month": 2, "feed_count": 40, "feed_duration_mins": 250, "weight_kg": 20.8, "status": "生长中"},
            {"month": 3, "feed_count": 44, "feed_duration_mins": 275, "weight_kg": 31.5, "status": "生长中"},
            {"month": 4, "feed_count": 46, "feed_duration_mins": 290, "weight_kg": 43.2, "status": "生长中"},
            {"month": 5, "feed_count": 47, "feed_duration_mins": 300, "weight_kg": 55.4, "status": "生长中"},
            {"month": 6, "feed_count": 46, "feed_duration_mins": 305, "weight_kg": 67.2, "status": "高速育肥"},
            {"month": 7, "feed_count": 45, "feed_duration_mins": 295, "weight_kg": 76.5, "status": "达标出厂"},
        ],
    },
    {
        "pig_id": "pig_lc_006",
        "breed": "两头乌", 
        "lifecycle": [
            {"month": 1, "feed_count": 32, "feed_duration_mins": 190, "weight_kg": 9.2, "status": "生长中"},
            {"month": 2, "feed_count": 38, "feed_duration_mins": 230, "weight_kg": 18.5, "status": "生长中"},
            {"month": 3, "feed_count": 41, "feed_duration_mins": 260, "weight_kg": 28.2, "status": "生长中"},
            {"month": 4, "feed_count": 44, "feed_duration_mins": 285, "weight_kg": 39.5, "status": "生长中"},
            {"month": 5, "feed_count": 46, "feed_duration_mins": 310, "weight_kg": 50.8, "status": "生长中"},
            {"month": 6, "feed_count": 45, "feed_duration_mins": 300, "weight_kg": 62.4, "status": "生长中"},
            {"month": 7, "feed_count": 43, "feed_duration_mins": 290, "weight_kg": 72.8, "status": "生长中"},
            {"month": 8, "feed_count": 42, "feed_duration_mins": 280, "weight_kg": 81.5, "status": "稳步成熟"},
        ],
    }
]

# ============================================================
# 2. 特征字符串构建函数（对齐原版逻辑）
# ============================================================

def build_feature_text(features: dict) -> str:
    """
    将生长特征描述转换为自然语言文本
    """
    return (
        f"品种：{features['breed']}，"
        f"当前日龄：{features['age_days']}天，"
        f"当前体重：{features['weight_kg']}公斤，"
        f"日均采食量：{features['daily_feed_kg']}公斤，"
        f"健康状况：{features['health_status']}"
    )

def _build_monthly_summary(month_data: dict) -> str:
    """
    单月周期核心时序描述片断
    """
    return (
        f"[第{month_data.get('month')}月: 体重{month_data.get('weight_kg')}kg, "
        f"进食时长{month_data.get('feed_duration_mins')}min]"
    )

def _build_slice_embedding_text(breed: str, months_slice: list[dict]) -> str:
    """
    生长时序时间切片中文特征序列描述构建
    """
    monthly_details = " | ".join(_build_monthly_summary(m) for m in months_slice)
    weights = [m.get("weight_kg", 0) for m in months_slice]
    total_gain = round(weights[-1] - weights[0], 1) if len(weights) > 1 else 0.0

    return (
        f"品种:{breed}，"
        f"观察周期:前{len(months_slice)}个月，"
        f"当前最新体重:{weights[-1]}kg，"
        f"累计增长:{total_gain}kg，"
        f"历史序列详情:{monthly_details}"
    )

# ============================================================
# 3. 阿里云百炼官方 SDK 向量化函数（通过 Padding 1024 维向量至 1536 维以契合 Milvus 架构）
# ============================================================

def get_embedding_1536(text: str, api_key: str) -> list[float]:
    """
    由于百炼 text-embedding-v3 支持的最大原生维度为 1024 维，
    为了对齐系统架构中 Collections 字段维度设为 1536 的技术硬红线约束，
    我们在此先提取百炼原生的 1024 维稠密语义向量，并在尾部进行 512 维的 Zero Padding。
    该算法在数学上完全等价，在超空间中对于 COSINE 相似度与检索精度没有任何精度损失，且完全兼容 1536 维物理索引。
    
    同时，该函数内置 3 次指数退避重试，以及对百炼 API 响应结构和空列表进行防越界边界安全检查。
    """
    max_retries = 3
    for attempt in range(max_retries):
        try:
            resp = TextEmbedding.call(
                model="text-embedding-v3",
                input=text,
                api_key=api_key,
                dimension=1024
            )
            if resp.status_code == 200:
                # 结构安全防御
                if not resp.output or "embeddings" not in resp.output or len(resp.output["embeddings"]) == 0:
                    raise Exception("百炼返回的向量列表为空！")
                raw_emb = resp.output["embeddings"][0]["embedding"]
                # 执行 Zero Padding
                return raw_emb + [0.0] * 512
            else:
                raise Exception(f"DashScope Error: code={resp.code}, msg={resp.message}")
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            time.sleep(2 ** attempt)

# ============================================================
# 4. 数据迁移核心逻辑
# ============================================================

def migrate_to_milvus():
    """
    一键清洗数据，调用官方 1536 维 Padding Embedding，并批量入库至本地 Milvus 集合中
    """
    settings = get_settings()
    api_key = os.environ.get("DASHSCOPE_API_KEY") or settings.dashscope_api_key
    
    if not api_key:
        print("[错误] 未检测到合法的 DASHSCOPE_API_KEY 环境变量或配置，无法执行 Embedding 数据清洗向量化！")
        sys.exit(1)

    # 1. 物理重构并初始化 Milvus 集合
    init_milvus_collections(force_rebuild=True)
    client = get_milvus_client()

    print("[迁移] 正在迁移生猪生长特征数据至 pig_growth_collection...")
    growth_batch = []
    for record in MOCK_PIG_DATA:
        text = build_feature_text(record["features"])
        # 计算精准锁定为 1536 维的稠密语义向量
        vector = get_embedding_1536(text, api_key)
        
        # 组装数据行，支持 enable_dynamic_field 特征
        row = {
            "id": record["id"],
            "vector": vector,
            "breed": record["features"]["breed"],
            "age_days": record["features"]["age_days"],
            "weight_kg": record["features"]["weight_kg"],
            "text": text,
            "daily_feed_kg": record["features"]["daily_feed_kg"],
            "health_status": record["features"]["health_status"],
            "traj_days_to_slaughter": record["trajectory"]["days_to_slaughter"],
            "traj_final_weight_kg": record["trajectory"]["final_weight_kg"],
            "traj_disease_occurred": record["trajectory"]["disease_occurred"],
            "traj_avg_daily_gain_g": record["trajectory"]["avg_daily_gain_g"]
        }
        growth_batch.append(row)

    if growth_batch:
        client.insert(collection_name="pig_growth_collection", data=growth_batch)
        print(f"[迁移] pig_growth_collection 数据迁移成功，共插入 {len(growth_batch)} 条记录。")

    print("[迁移] 正在迁移生猪生命周期时序数据至 pig_lifecycle_collection...")
    lifecycle_batch = []
    for pig in MOCK_PIG_LIFECYCLE_DATA:
        lifecycle = pig["lifecycle"]
        for m in range(1, len(lifecycle)):
            slice_data = lifecycle[:m]
            text = _build_slice_embedding_text(pig["breed"], slice_data)
            vector = get_embedding_1536(text, api_key)

            row = {
                "id": f"{pig['pig_id']}_slice_{m}",
                "pig_id": pig["pig_id"],
                "breed": pig["breed"],
                "slice_month": m,
                "vector": vector,
                "text": text,
                "lifecycle_json": json.dumps(lifecycle, ensure_ascii=False)
            }
            lifecycle_batch.append(row)

    if lifecycle_batch:
        client.insert(collection_name="pig_lifecycle_collection", data=lifecycle_batch)
        print(f"[迁移] pig_lifecycle_collection 时序时间片迁移成功，共插入 {len(lifecycle_batch)} 条历史切片。")

if __name__ == "__main__":
    print("=== 生猪特征及全生命周期切片数据 Milvus 本地迁移引擎启动 ===")
    migrate_to_milvus()
    print("=== 数据清洗迁移成功 ===")
