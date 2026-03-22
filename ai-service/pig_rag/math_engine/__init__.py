# -*- coding: utf-8 -*-
"""
数值引擎 (Math Engine) — 统一外挂接口
====================================

本模块作为数值轨道的“总机”，负责协调 DTW 匹配引擎与曲线拟合引擎。
它对外提供简洁的单点入口，屏蔽了内部复杂的数据对齐、加权聚合及非线性回归过程。

设计模式： Facade (外观模式)
功能点：
1. 统一接口：对外仅暴露 predict_growth_curve()，简化调用方的逻辑。
2. 数据缓存：内置内存级缓存，避免在大规模推理任务中重复读取海量历史 CSV 文件，提高 IO 效率。
3. 跨维度检索：集成兽医日志（专家知识）检索功能，使数值偏差能与历史背书相关联。

使用范例：
    from pig_rag.math_engine import predict_growth_curve
    result = predict_growth_curve(current_day_age=60, current_weight_series=[...])
    print(result.deviation_summary)
"""

import os
from pathlib import Path
import json

import numpy as np
import pandas as pd

# 内部引用：DTW 相似性匹配与 Gompertz 拟合
from .dtw_matcher import find_top_k_matches, HistoricalMatch
from .curve_fitter import predict_growth_curve as _fit_curve, PredictionResult

# 默认数据资产路径 (相对于包根目录)
DEFAULT_CSV_PATH = Path(__file__).parent.parent.parent / "mock_data" / "historical_pig_timeseries.csv"

# 全局单例缓存：加载后的历史 DataFrame。
# 在多用户高并发场景下，此缓存能极大降低算法后端的响应延迟。
_cached_historical_df: pd.DataFrame | None = None


def _load_historical_data(csv_path: str | None = None) -> pd.DataFrame:
    """
    内部加载器：带缓存的历史数据读取
    
    返回：包含 pig_id, day_age, weight_kg 等列的 pandas DataFrame
    """
    global _cached_historical_df

    # 路径决策
    if csv_path is None:
        csv_path = str(DEFAULT_CSV_PATH)

    # 命中缓存
    if _cached_historical_df is not None:
        return _cached_historical_df

    # 执行物理 IO
    if not os.path.exists(csv_path):
        # 抛出具体的环境异常，提示资产缺失
        raise FileNotFoundError(f"CRITICAL: 历史生长数据集文件缺失，路径： {csv_path}")

    # 对于 10MB+ 的 CSV，建议使用 pyarrow 或 engine='c' 加速
    df = pd.read_csv(csv_path)
    _cached_historical_df = df
    return df


def predict_growth_curve(
    current_day_age: int,
    current_weight_series: list[float] | np.ndarray,
    top_k: int = 5,
    target_day_age: int = 300,
    csv_path: str | None = None,
    exclude_pig_id: str | None = None,
) -> PredictionResult:
    """
    数值引擎对外唯一 API：全流程自动化推理服务。

    流程拆解 (Sequence)：
    1. 【准备】将原始列表转换为高性能的 Numpy 数组。
    2. 【数据】获取或加载历史全量生长档案。
    3. 【检索】通过 DTW 算法从大海中捞出形态最像的 K 个“孪生”样本。
    4. 【拟合】将当前轨迹缝合进历史数据中，利用生物生长方程进行外推预测。
    5. 【产出】生成 PredictionResult，包含预测数值坐标及客观文本结论。

    参数：
    - current_day_age: 当前猪只的日龄（决定了预测的起始点）。
    - current_weight_series: 该猪只从出生至今的历史体重数据（反映其个性化生长潜能）。
    - exclude_pig_id: 设置后可防止模型在历史数据库中“撞见”自己，确交叉验证的准确性。
    """
    
    # 统一输入格式
    if not isinstance(current_weight_series, np.ndarray):
        current_weight_series = np.array(current_weight_series, dtype=float)

    # 获取底层数据集
    historical_df = _load_historical_data(csv_path)

    # 干预过滤：排除自身
    if exclude_pig_id:
        historical_df = historical_df[historical_df["pig_id"] != exclude_pig_id]

    # --- 数值轨道 Step 1: DTW 匹配 (检索最相似的生长档案) ---
    # 这里设置 dtw_window=30 表示允许特征在 30 天的范围内对齐
    matches = find_top_k_matches(
        current_weight_series=current_weight_series,
        historical_df=historical_df,
        top_k=top_k,
        dtw_window=30,
        normalize=True,
    )

    # --- 数值轨道 Step 2: 曲线拟合 (根据历史趋势外推未来) ---
    # 返回的内容将直接影响前端的折线图展示
    result = _fit_curve(
        current_day_age=current_day_age,
        current_weight_series=current_weight_series,
        top_k_matches=matches,
        target_day_age=target_day_age,
        use_gompertz_fit=True, # 开启 Gompertz 方程平滑
    )

    return result


def get_vet_logs_for_matches(
    matches: list[dict],
    vet_logs_path: str | None = None,
) -> list[dict]:
    """
    桥接功能：为匹配到的数值锚点检索对应的兽医日志（认知素材）。
    
    该函数连接了“数据点”与“文字叙述”，是实现 RAG 的关键步骤。
    它不仅提供数字预测，更由于能说出“这头猪表现得像过去那头生过病的猪”，从而增强了报告的解释性。
    """
    if vet_logs_path is None:
        vet_logs_path = str(Path(__file__).parent.parent.parent / "mock_data" / "vet_logs.json")

    if not os.path.exists(vet_logs_path):
        return []

    try:
        with open(vet_logs_path, "r", encoding="utf-8") as f:
            all_logs = json.load(f)
        
        # 索引匹配
        matched_pig_ids = {m["pig_id"] for m in matches}
        relevant_logs = [log for log in all_logs if log["pig_id"] in matched_pig_ids]
        return relevant_logs
    except Exception as e:
        print(f"Error loading vet logs: {e}")
        return []
