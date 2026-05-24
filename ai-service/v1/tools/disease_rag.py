# -*- coding: utf-8 -*-
"""
v1/tools/disease_rag.py
生猪特征混合检索案例匹配与生命周期时序轨迹预测核心智能工具组件
"""

import json
from typing import Any, Union, List
from pydantic import BaseModel, Field

from v1.tools.base_tool import safe_tool_sandbox
from v1.db.hybrid_retriever import HybridRetriever

# 1. 定义强类型输入契合类
class PigGrowthQueryInput(BaseModel):
    """生猪生长相似案例检索输入模型"""
    breed: str = Field(..., description="生猪品种，例如：'杜洛克'，'两头乌'")
    age_days: int = Field(..., description="生猪当前日龄，单位：天")
    weight_kg: float = Field(..., description="生猪当前体重，单位：公斤")
    top_n: int = Field(default=3, description="返回最相似的生猪历史案例数量")

class PigLifecycleQueryInput(BaseModel):
    """生猪生命周期时序轨迹预测检索输入模型"""
    breed: str = Field(..., description="生猪品种，例如：'两头乌'")
    current_month: int = Field(..., description="生猪当前所处的生命周期月份（用于时间切片物理对齐）")
    current_month_data: Any = Field(..., description="生猪当前生命周期阶段的历史观测时序数据，可以为单月特征字典，或历史多月时序特征字典列表")
    top_n: int = Field(default=3, description="返回最相似的生猪生命周期时序切片案例数量")

# 2. 实例化全局 RRF 混合检索器
_hybrid_retriever = HybridRetriever()

# 3. 编写异常安全的生猪相似案例查询工具
@safe_tool_sandbox
async def query_similar_pig_records(breed: str, age_days: int, weight_kg: float, top_n: int = 3) -> str:
    """
    【Agent 工具接口】根据生猪当前生理特征指标，在历史库中以 Dense+Sparse 混合算法检索最匹配案例，并输出未来结局。
    """
    results = await _hybrid_retriever.search_growth(
        breed=breed,
        age_days=age_days,
        weight_kg=weight_kg,
        top_k=top_n
    )

    if not results:
        return json.dumps({"status": "error", "message": "无法匹配相似案例"}, ensure_ascii=False)

    output = []
    for r in results:
        record_data = r.get("record", {})
        traj = record_data.get("trajectory", {})
        
        output.append({
            "matched_pig_id": record_data.get("id") or r["matched_id"],
            "historical_outcome": {
                "final_weight": traj.get("final_weight_kg"),
                "days_observed": traj.get("days_to_slaughter"),
                "had_disease": traj.get("disease_occurred")
            },
            "similarity_score": round(float(r["score"]), 4)
        })

    query_text = f"品种：{breed}，当前日龄：{age_days}天，当前体重：{weight_kg}公斤"
    return json.dumps({
        "status": "success",
        "query": query_text,
        "results": output
    }, ensure_ascii=False)

# 4. 编写异常安全的生命周期未来轨迹预测工具
@safe_tool_sandbox
async def query_pig_growth_prediction(breed: str, current_month: int, current_month_data: Any, top_n: int = 3) -> str:
    """
    【Agent 工具接口】根据生猪历史断面时序数据，匹配最相似的生命周期截面，截取该案例自下月起的未来轨迹作为决策参考。
    """
    # 兼容性处理：若用户只传了当前月特征字典，手动包装成序列
    if isinstance(current_month_data, dict):
        current_sequence = [{**current_month_data, "month": current_month}]
    else:
        current_sequence = current_month_data

    results = await _hybrid_retriever.search_lifecycle(
        breed=breed,
        current_month=current_month,
        current_month_data=current_sequence,
        top_k=top_n
    )

    output_list = []
    for r in results:
        full_history = json.loads(r["lifecycle_json"])
        
        # 截取“未来轨迹” (month > current_month)
        future_part = [m for m in full_history if m["month"] > current_month]

        pig_id = r.get("pig_id") or r["matched_id"].split("_slice_")[0]

        output_list.append({
            "matched_pig": pig_id,
            "similarity_distance": round(float(r["score"]), 4),
            "historical_future_track": future_part
        })

    return json.dumps({
        "query_context": f"{breed}龄期{current_month}月",
        "top_matches": output_list
    }, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    import asyncio

    async def test_tools():
        print("=== [测试] disease_rag 工具链 ===")
        
        print("\n1. 测试生猪相似案例查询工具 (query_similar_pig_records)")
        res1 = await query_similar_pig_records(breed="杜洛克", age_days=90, weight_kg=45.0, top_n=2)
        print(res1)
        
        print("\n2. 测试生命周期未来轨迹预测工具 (query_pig_growth_prediction)")
        test_lifecycle_data = {"feed_count": 35, "feed_duration_mins": 210, "weight_kg": 10.2}
        res2 = await query_pig_growth_prediction(breed="两头乌", current_month=3, current_month_data=test_lifecycle_data, top_n=2)
        print(res2)

    asyncio.run(test_tools())
