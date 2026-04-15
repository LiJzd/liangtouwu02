# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
import random
import os

# 参数设置
NUM_PIGS = 50  # 增加样本量以展示分布
DAYS = 300
OUTPUT_FILE = "historical_pigs.csv"

def generate_gompertz_curve(t, A, B, k):
    """
    Gompertz 生长曲线模型
    W(t) = A * exp(-B * exp(-k * t))
    """
    return A * np.exp(-B * np.exp(-k * t))

def randn(mu=0, sigma=1):
    """正态分布 (Gaussian) 随机数"""
    return np.random.normal(mu, sigma)

def generate_pig_data(pig_id, has_anomaly=False):
    """生成单只猪的 300 天生命周期数据"""
    
    # 1. 基础生物学参数设定 (金华两头乌真实特征)
    # 渐近成熟体重 A: 130-145kg
    A = random.uniform(130.0, 145.0) 
    # B 值决定初始体重 (1kg 左右)
    B = random.uniform(4.7, 4.9)
    # 成熟速率 k: 两头乌属于慢生品种
    k = random.uniform(0.011, 0.014)
    
    # 异常事件参数
    anomaly_start = -1
    anomaly_duration = random.randint(5, 12)
    if has_anomaly:
        anomaly_start = random.randint(120, 180) # 中后期热应激
        
    data = []
    current_actual_weight = generate_gompertz_curve(0, A, B, k)
    
    # 累积生物波动系数 (自相关噪声: 前一天的状态会影响后一天)
    biological_drift = 0.0
    prev_ideal_weight = current_actual_weight
    
    in_anomaly = False
    recovery_days_left = 0
    
    for day in range(DAYS):
        # 理想生长量
        ideal_weight = generate_gompertz_curve(day, A, B, k)
        ideal_gain = ideal_weight - prev_ideal_weight
        prev_ideal_weight = ideal_weight
        
        # 模拟环境日气温 (正态分布波动)
        seasonal_temp = 20.0 + 8 * np.sin(2 * np.pi * (day + 30) / 365)
        avg_temp = seasonal_temp + randn(0, 1.5)
        
        # ---------------------------------------------------------
        # 核心逻辑：生长波动建模
        # ---------------------------------------------------------
        
        # A. 长期生物波动 (例如：微小健康起伏、食欲变化)
        # 采用 AR(1) 模型: 今天偏差 = 0.9 * 昨天偏差 + 随机扰动
        biological_drift = biological_drift * 0.92 + randn(0, 0.15)
        
        # B. 基础增重 + 生物波动
        daily_gain = ideal_gain + biological_drift
        
        # 异常事件逻辑 (热应激)
        if has_anomaly and day == anomaly_start:
            in_anomaly = True
            
        if in_anomaly and day < anomaly_start + anomaly_duration:
            # 严重热应激：气温升高，生长停滞
            avg_temp = 35.0 + randn(0, 1.0)
            daily_gain = random.uniform(-0.15, 0.05) 
            daily_feed = random.uniform(0.4, 1.0)
        elif in_anomaly and day == anomaly_start + anomaly_duration:
            # 异常结束转入补偿期
            in_anomaly = False
            recovery_days_left = 15
            daily_gain = ideal_gain * 1.6 # 补偿生长
            daily_feed = 2.8 + random.uniform(0, 0.4)
        elif recovery_days_left > 0:
            factor = 1.0 + (recovery_days_left / 15.0) * 0.4
            daily_gain = ideal_gain * factor
            daily_feed = (2.0 + daily_gain * 2.2) * (1 + randn(0, 0.03))
            recovery_days_left -= 1
        else:
            # 正常状态：确保单日增重符合生物学常识 (不持续掉秤)
            daily_gain = max(-0.05, daily_gain)
            daily_feed = (1.6 + daily_gain * 2.8) * (1 + randn(0, 0.05))

        # 更新累计真实体重
        current_actual_weight += daily_gain
        current_actual_weight = max(current_actual_weight, 1.0) # 防止极端负数
        
        # C. 测量噪声 (地磅/传感器误差，符合高斯分布)
        measured_weight = current_actual_weight + randn(0, 0.25)

        data.append({
            "pig_id": f"LTW-{pig_id:03d}",
            "day_age": day,
            "weight_kg": round(measured_weight, 2),
            "daily_feed_intake_kg": round(max(0.1, daily_feed), 2),
            "avg_temperature": round(avg_temp, 1),
            "is_anomaly": 1 if (in_anomaly and day < anomaly_start + anomaly_duration) else 0
        })
        
    return data

def main():
    print(f">>> 正在生成 {NUM_PIGS} 头两头乌生猪的高保真生长数据 (Gaussian Noise + AR Model)...")
    all_data = []
    
    # 设置 15% 的异常比例
    anomaly_count = int(NUM_PIGS * 0.15)
    anomaly_pigs = random.sample(range(1, NUM_PIGS + 1), anomaly_count)
    print(f">>> 已标记异常猪只编号: {anomaly_pigs}")
    
    for i in range(1, NUM_PIGS + 1):
        has_anomaly = i in anomaly_pigs
        pig_data = generate_pig_data(i, has_anomaly)
        all_data.extend(pig_data)
        
    df = pd.DataFrame(all_data)
    
    # 验证是否满足单调递增约束
    print("\n>>> 正在进行数据质量验证...")
    for pig_id in df['pig_id'].unique():
        pig_df = df[df['pig_id'] == pig_id].sort_values('day_age')
        weights = pig_df['weight_kg'].values
        
        # 允许微小的波动(热应激及其有限的掉秤，或秤的误差)，但宏观整体必须递增
        # 检查是否出现连续3天以上幅度极大的异常下降
        diffs = np.diff(weights)
        large_drops = diffs < -1.5
        if np.any(large_drops):
            print(f"警告: 猪 {pig_id} 发生超过 1.5kg 的单日剧烈掉秤！")
            
        # 宏观检查 (100天 vs 200天)
        w_10 = weights[10]
        w_100 = weights[100]
        w_200 = weights[200]
        w_299 = weights[299]
        if not (w_10 < w_100 < w_200 < w_299):
            print(f"严重错误: 猪 {pig_id} 不符合宏观递增约束! {w_10}->{w_100}->{w_200}->{w_299}")

    df.to_csv(OUTPUT_FILE, index=False)
    print(f"\n>>> 数据生成完毕！已保存至 {OUTPUT_FILE}")
    print(f">>> 总记录数: {len(df)} | 模拟天数: {DAYS} | 出栏平均体重: {round(df[df['day_age']==DAYS-1]['weight_kg'].mean(), 2)}kg")

if __name__ == "__main__":
    main()
