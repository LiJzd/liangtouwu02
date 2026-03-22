# -*- coding: utf-8 -*-
"""
数值引擎 (Math Engine) — DTW 序列比对与 Top-K 召回
================================================

本模块负责系统的“相似性发现”逻辑。
通过 Dynamic Time Warping (动态时间规整) 算法，在历史数据库中寻找生长特征（体重变化趋势）
与当前猪只最相似的历史档案。

算法核心：
1. DTW 距离计算：相比于简单的欧氏距离，DTW 允许时间轴的轻微平移或伸缩，能更准确地匹配“生长慢热型”或“生长爆发型”猪只。
2. 性能优化：实现了带 Sakoe-Chiba 窗口限制的 Fast-DTW，将时间复杂度控制在 O(n*window) 级别。
3. Z-Score 标准化：支持对比前进行能量缩放，消除由于绝对重量差异引起的偏差，专注于“趋势形态”的匹配。

架构定位：
- 检索层：为曲线拟合（Curve Fitter）提供最相关的“参考锚点”。
- 数据对齐：解决不同猪只录入时间点不一致、数据频率不均匀导致的匹配难题。
"""

import numpy as np
from dataclasses import dataclass
from typing import Optional
import pandas as pd


@dataclass
class HistoricalMatch:
    """
    匹配结果封装类
    
    存储了单头历史猪只的完整生命周期档案，便于后续预测引擎提取其“未来”数据。
    """
    pig_id: str
    dtw_distance: float                 # 核心距离标量：值越小表示生长趋势越像
    full_weight_series: np.ndarray      # 该猪从出生到出栏的全周期体重 (1..N天)
    full_day_ages: np.ndarray           # 对应的日龄坐标轴
    full_feed_series: np.ndarray        # 对应的采食量背景数据（用于 RAG 关联分析）
    full_temp_series: np.ndarray        # 对应的环境温度背景数据（用于 RAG 关联分析）


def _dtw_distance(s1: np.ndarray, s2: np.ndarray) -> float:
    """
    标准 DTW (动态时间规整) 算法实现
    
    算法原理：
    构建一个 n x m 的累计代价矩阵，寻找一条从左下角到右上角的最佳对齐路径，使得路径上的元素差值之和最小。
    
    复杂度：O(n*m)
    """
    n, m = len(s1), len(s2)
    # 初始化累计代价矩阵，填充为无穷大
    dtw_matrix = np.full((n + 1, m + 1), np.inf)
    dtw_matrix[0, 0] = 0.0

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            # 基元代价：当前两个时间点的数值差绝对值
            cost = abs(s1[i - 1] - s2[j - 1])
            # 状态转移：取 [插入, 删除, 匹配] 三种路径中代价最小的一个
            dtw_matrix[i, j] = cost + min(
                dtw_matrix[i - 1, j],       # 垂直移动
                dtw_matrix[i, j - 1],       # 水平移动
                dtw_matrix[i - 1, j - 1],   # 对角线移动
            )

    return dtw_matrix[n, m]


def _dtw_distance_fast(s1: np.ndarray, s2: np.ndarray,
                       window: Optional[int] = None) -> float:
    """
    带窗限的加速版 DTW (Sakoe-Chiba Band)
    
    优化思路：
    由于生物生长通常不会发生剧烈的“时间瞬移”，因此合理的匹配路径应当分布在对角线两侧的一个小范围内。
    通过限制搜索窗口 (window)，大幅减少代价矩阵的计算单元，同时能有效防止病态的对齐结果。
    """
    n, m = len(s1), len(s2)
    if window is None:
        window = max(n, m)
    # 强制窗口至少能涵盖长度差，否则无法达到终点
    window = max(window, abs(n - m))

    dtw_matrix = np.full((n + 1, m + 1), np.inf)
    dtw_matrix[0, 0] = 0.0

    for i in range(1, n + 1):
        # 仅在对角线窗口范围内进行扫描
        j_start = max(1, i - window)
        j_end = min(m, i + window)
        for j in range(j_start, j_end + 1):
            cost = abs(s1[i - 1] - s2[j - 1])
            dtw_matrix[i, j] = cost + min(
                dtw_matrix[i - 1, j],
                dtw_matrix[i, j - 1],
                dtw_matrix[i - 1, j - 1],
            )

    return dtw_matrix[n, m]


def find_top_k_matches(
    current_weight_series: np.ndarray,
    historical_df: pd.DataFrame,
    top_k: int = 5,
    dtw_window: Optional[int] = 30, # 默认 30 天的弹性窗口，即允许一个月的时间错位
    normalize: bool = True,
) -> list[HistoricalMatch]:
    """
    Top-K 相似性发现核心函数
    
    工作机制：
    1. 接收当前猪只的已有生长片段 (Length = L)。
    2. 遍历历史池中每一头猪，取其生长周期的前 L 天。
    3. 调用 DTW 计算两者生长轨迹的形态相似度。
    4. 返回排序后的最佳匹配项。
    """
    current_len = len(current_weight_series)

    # 预处理：标准化 (Z-Score)
    # 目的：有些两头乌猪整体基数大，有些基数小。标准化能让我们比对“增长斜率和趋势”，而非绝对公斤数。
    if normalize and current_len > 1:
        mean_c = np.mean(current_weight_series)
        std_c = np.std(current_weight_series)
        # 防止除零错误
        current_norm = (current_weight_series - mean_c) / (std_c + 1e-9)
    else:
        current_norm = current_weight_series

    results: list[HistoricalMatch] = []

    # 按个体对历史海量日粮/体重数据进行分组扫描
    for pig_id, pig_group in historical_df.groupby("pig_id"):
        # 确保时间序列严格按日龄递增
        pig_group = pig_group.sort_values("day_age")
        full_weights = pig_group["weight_kg"].values
        full_days = pig_group["day_age"].values
        full_feed = pig_group["daily_feed_intake_kg"].values
        full_temp = pig_group["avg_temperature"].values

        # 数据清洗：如果历史记录还没当前的长，则无法作为参考
        if len(full_weights) < current_len:
            continue 

        # 截取历史样本的对应区间用于“形态比对”
        hist_prefix = full_weights[:current_len]

        # 同样对历史前缀进行标准化
        if normalize and current_len > 1:
            mean_h = np.mean(hist_prefix)
            std_h = np.std(hist_prefix)
            hist_norm = (hist_prefix - mean_h) / (std_h + 1e-9)
        else:
            hist_norm = hist_prefix

        # 执行高性能 DTW 扫描
        dist = _dtw_distance_fast(current_norm, hist_norm, window=dtw_window)

        results.append(HistoricalMatch(
            pig_id=str(pig_id),
            dtw_distance=dist,
            full_weight_series=full_weights,
            full_day_ages=full_days,
            full_feed_series=full_feed,
            full_temp_series=full_temp,
        ))

    # 距离越小越相似，取排序后的前 K 位
    results.sort(key=lambda x: x.dtw_distance)
    return results[:top_k]
