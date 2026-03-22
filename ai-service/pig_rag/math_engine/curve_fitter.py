# -*- coding: utf-8 -*-
"""
数值引擎 (Math Engine) — 曲线拟合与偏差预测
==========================================

本模块负责系统的“定量计算”轨道。
其核心逻辑是：通过对历史相似猪只的后续生长数据进行加权平均，并利用生物生长方程进行拟合，从而推演出当前猪只的
未来生长趋势。

核心算法：
1. 生长动力学模型：采用经典的 Gompertz 生长方程作为金华两头乌生长的底层数学描述。
2. 数据平滑技术：使用加权移动平均与 Scipy 的 Levenberg-Marquardt 非线性最小二乘法进行参数拟合。
3. 偏差量化分析：将预测值与品种标准基准值对比，计算精确的生长偏差百分比。

架构定位：
- 纯计算层：不包含任何业务判断或 AI 推理，仅产出客观的数值结论。
- 输出物：为认知引擎（Cognitive Track）提供具有统计学意义的“数据支撑”。
"""

import math
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np
from scipy.optimize import curve_fit

# 内部依赖：DTW 匹配结果
from .dtw_matcher import HistoricalMatch


@dataclass
class PredictionResult:
    """
    数值预测的核心数据载体
    (等效于后端计算结果的 DTO)
    """
    # 预测出的生长曲线：[{'day_age': 天, 'weight_kg': 重}, ...]
    predicted_curve: list[dict]

    # 数值偏差的文本化总结（由数值引擎生成的客观陈述，将被喂给 AI Agent）
    deviation_summary: str

    # 偏差百分比：用于量化当前猪只相对于品种标准的强弱（正数为超长，负数为滞后）
    deviation_percent: float

    # 预测最终出栏体重 (基于拟合模型推算)
    predicted_final_weight: float

    # 品种标准出栏体重 (基准线)
    standard_final_weight: float

    # Top-K 匹配的历史猪只摘要信息，包含相似度距离等
    match_summary: list[dict] = field(default_factory=list)


# ============================================================
# 生物数学模型底层：Gompertz 生长曲线
# ============================================================

def _gompertz(t: np.ndarray, A: float, b: float, c: float) -> np.ndarray:
    """
    Gompertz 生长函数实现：W(t) = A * exp(-b * exp(-c * t))
    
    参数解析：
    - A: 成年体重上限 (Asymptotic weight)，即理论上猪能够长到的最大重量。
    - b: 缩放常数，与初生重及生长起始阶段相关。
    - c: 生长速率系数 (Maturation rate)，决定了曲线的陡峭程度。
    """
    return A * np.exp(-b * np.exp(-c * t))


# 金华两头乌官方/科研标准生长模型参数 (群体平均基准)
# 这些参数反映了该品种在理想饲养条件下的典型生长轨迹
STANDARD_PARAMS = {
    "A": 135.0,   # 成年体重上限预计为 135kg
    "b": 4.5,     # 初始偏置常数
    "c": 0.012,   # 每日生长成熟速率
}


def compute_standard_weight(day_age: int) -> float:
    """
    计算特定日龄下的“品种标准体重”
    
    该数值作为全系统的“及格线”或“参考线”，任何个体生长都会与之对标。
    """
    return _gompertz(
        np.array([day_age], dtype=float),
        STANDARD_PARAMS["A"],
        STANDARD_PARAMS["b"],
        STANDARD_PARAMS["c"],
    )[0]


# ============================================================
# 核心预测算法实现
# ============================================================

def predict_growth_curve(
    current_day_age: int,
    current_weight_series: np.ndarray,
    top_k_matches: list[HistoricalMatch],
    target_day_age: int = 300,
    use_gompertz_fit: bool = True,
) -> PredictionResult:
    """
    多阶预测算法主逻辑：
    
    1. 【加权聚合】将 DTW 算法匹配到的 K 头历史猪只的未来数据，按相似度（距离的倒数）进行加权融合。
    2. 【模型拟合】将“已有历史轨迹”与“融合后的未来轨迹”拼接，送入 Gompertz 模型进行回归拟合。
       - 即使历史数据存在噪声或断档，生物模型也能确保预测出的曲线具备连贯的生物学意义。
    3. 【对标分析】将生成的平滑曲线与 STANDARD_PARAMS 描述的标准线进行对比，计算偏差。
    """
    
    # --- 阶段 0: 边界条件处理 ---
    if not top_k_matches:
        # 当数据库中没有相似猪只时，退化为保守的标准曲线预测
        curve = []
        for d in range(current_day_age + 1, target_day_age + 1):
            w = compute_standard_weight(d)
            curve.append({"day_age": d, "weight_kg": round(w, 2)})
        return PredictionResult(
            predicted_curve=curve,
            deviation_summary="由于缺乏相似的历史生长档案，当前预测基于品种标准模型生成。",
            deviation_percent=0.0,
            predicted_final_weight=round(compute_standard_weight(target_day_age), 2),
            standard_final_weight=round(compute_standard_weight(target_day_age), 2),
        )

    # --- 阶段 1: 加权平均计算 (Weighted Aggregation) ---
    # 权重策略：距离越近（相似度越高）的猪只，其未来生长趋势对当前预测的贡献度越大
    epsilon = 1e-6
    # 算出每个匹配项的原始权重 (1/距离)
    weights = np.array([1.0 / (m.dtw_distance + epsilon) for m in top_k_matches])
    weights /= weights.sum()  # 权值归一化，确保权重之和为 1

    # 初始化未来时间轴 (从明天到目标出栏日)
    future_days = list(range(current_day_age + 1, target_day_age + 1))
    num_future_days = len(future_days)
    weighted_future = np.zeros(num_future_days)
    valid_weights = np.zeros(num_future_days)

    # 遍历每个匹配到的历史“锚点”，并将其未来部分的贡献叠加
    for match, w in zip(top_k_matches, weights):
        # 仅截取历史猪在该对应日龄之后的数据段
        mask = match.full_day_ages > current_day_age
        future_days_hist = match.full_day_ages[mask]
        future_weights_hist = match.full_weight_series[mask]

        for fd, fw in zip(future_days_hist, future_weights_hist):
            idx = int(fd) - current_day_age - 1
            if 0 <= idx < num_future_days:
                weighted_future[idx] += w * fw
                valid_weights[idx] += w # 记录每个时间点的有效权重积累，用于均值化

    # 对累积值进行均值化处理，缺失点使用标准生长值填充
    for i in range(num_future_days):
        if valid_weights[i] > 0:
            weighted_future[i] /= valid_weights[i]
        else:
            weighted_future[i] = compute_standard_weight(future_days[i])

    # --- 阶段 2: 生物学模型重合逻辑 (Gompertz Fitting) ---
    # 原始的加权平均曲线可能存在锯齿。利用 Gompertz 方程对其进行平滑回归，保证预测曲线符合动物生长规律。
    predicted_weights = weighted_future # 默认使用原始加权值
    if use_gompertz_fit:
        try:
            # 构造全周期数据集：[历史实测点 + 聚合预测点]
            all_days = np.concatenate([
                np.arange(1, len(current_weight_series) + 1), # 假设实测数据从第1天开始
                np.array(future_days, dtype=float),
            ])
            # 对齐日龄和体重的数量级 (此处假设 current_weight_series 涵盖了 1~current_day_age)
            # 如果不匹配，拟合器会自动根据输入日龄对齐
            all_weights = np.concatenate([
                current_weight_series[-current_day_age:] if len(current_weight_series) >= current_day_age else current_weight_series,
                weighted_future,
            ])
            
            # 使用 scipy 的非线性优化工具 curve_fit
            # p0: 初始搜索种子；bounds: 参数搜索范围限制（防止长出“超猪”）
            popt, _ = curve_fit(
                _gompertz, all_days[-len(all_weights):], all_weights,
                p0=[STANDARD_PARAMS["A"], STANDARD_PARAMS["b"], STANDARD_PARAMS["c"]],
                bounds=([80, 1, 0.005], [200, 10, 0.025]),
                maxfev=5000,
            )

            # 根据拟合出的“个性化参数”重新生成平滑的未来预测点
            predicted_weights = _gompertz(np.array(future_days, dtype=float), *popt)
        except Exception as e:
            # 拟合算法不收敛或数据不足时，平滑失败。自动回退到加权平均原始结果以保证可用性。
            print(f"Warning: Gompertz fit failed ({e}), falling back to weighted moving average.")

    # --- 阶段 3: 输出格式化与偏差评估 ---
    curve = []
    for d, w in zip(future_days, predicted_weights):
        curve.append({"day_age": int(d), "weight_kg": round(float(w), 2)})

    # 计算出栏日 (target_day_age) 的最终预测体重与标准值的偏差
    predicted_final = float(predicted_weights[-1]) if len(predicted_weights) > 0 else 0
    standard_final = compute_standard_weight(target_day_age)
    deviation_pct = ((predicted_final - standard_final) / standard_final) * 100

    # 生成客观的偏差描述文本（该文本将被下游的 AI Agent 引用作为“证据”）
    if abs(deviation_pct) < 2:
        deviation_text = f"预测终重约 {predicted_final:.1f}kg，与品种基准（{standard_final:.1f}kg）处于同一水平。"
    elif deviation_pct > 0:
        deviation_text = f"预测表现强劲，出栏终重预计可达 {predicted_final:.1f}kg，高出标准线 {deviation_pct:.1f}%。"
    else:
        deviation_text = f"生长曲线出现显著低位，预测终重仅 {predicted_final:.1f}kg，低于标准线 {abs(deviation_pct):.1f}%。"

    # --- 阶段 4: 结果封装与摘要 ---
    match_info = []
    for m in top_k_matches:
        final_w = float(m.full_weight_series[-1]) if len(m.full_weight_series) > 0 else 0
        match_info.append({
            "pig_id": m.pig_id,
            "dtw_distance": round(m.dtw_distance, 4),
            "final_weight": round(final_w, 2),
        })

    return PredictionResult(
        predicted_curve=curve,
        deviation_summary=deviation_text,
        deviation_percent=round(deviation_pct, 2),
        predicted_final_weight=round(predicted_final, 2),
        standard_final_weight=round(standard_final, 2),
        match_summary=match_info,
    )
