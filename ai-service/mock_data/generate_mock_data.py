# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
import random
import os

# 参数设置
NUM_PIGS = 20
DAYS = 300
OUTPUT_FILE = "historical_pigs.csv"

def generate_gompertz_curve(t, A, B, k):
    """
    Gompertz 生长曲线模型
    W(t) = A * exp(-B * exp(-k * t))
    """
    return A * np.exp(-B * np.exp(-k * t))

def generate_pig_data(pig_id, has_anomaly=False):
    """生成单只猪的 300 天生命周期数据"""
    
    # 1. 基础生物学参数设定 (两头乌特征)
    # 极限体重 A 设定在 120-135kg 之间
    A = random.uniform(120.0, 135.0) 
    # B 值使得初始体重在 1-1.5kg 左右
    B = random.uniform(4.0, 4.8)
    # 生长速率 k
    k = random.uniform(0.012, 0.016)
    
    # 异常事件参数
    anomaly_start = -1
    anomaly_duration = 5
    if has_anomaly:
        anomaly_start = random.randint(100, 150) # 夏季热应激通常发生在生长期
        
    data = []
    current_weight = generate_gompertz_curve(0, A, B, k)
    
    # 用于记录前一天的理想状态，以便计算每日真实增重
    prev_ideal_weight = current_weight
    
    in_anomaly = False
    recovery_days_left = 0
    compensation_factor = 1.0 # 补偿生长系数
    
    for day in range(DAYS):
        # 计算基础日增重 (理想状态)
        ideal_weight = generate_gompertz_curve(day, A, B, k)
        base_daily_gain = ideal_weight - prev_ideal_weight
        prev_ideal_weight = ideal_weight
        
        # 环境温度模拟
        avg_temp = 20.0 + 5 * np.sin(2 * np.pi * day / 365) + random.uniform(-2, 2)
        
        # 异常事件逻辑 (热应激)
        if has_anomaly and day == anomaly_start:
            in_anomaly = True
            recovery_days_left = 0
            
        if in_anomaly and day < anomaly_start + anomaly_duration:
            # 高温发生
            avg_temp = random.uniform(34.0, 36.5)
            # 异常时停滞生长或微小掉秤 (严格约束不超过 1kg)
            daily_gain = random.uniform(-0.2, 0.05) 
            daily_feed = random.uniform(0.5, 1.2) # 采食量骤降
        elif in_anomaly and day == anomaly_start + anomaly_duration:
            # 异常结束，进入补偿期
            in_anomaly = False
            recovery_days_left = 15 # 补偿生长期 15 天
            daily_gain = base_daily_gain * 1.5 # 初期补偿猛烈
            daily_feed = 2.5 + random.uniform(0, 0.5)
        elif recovery_days_left > 0:
            # 补偿生长期逐渐恢复正常
            compensation_factor = 1.0 + (recovery_days_left / 15.0) * 0.3 # 逐渐回落到 1.0
            daily_gain = base_daily_gain * compensation_factor
            daily_feed = (1.8 + daily_gain * 2.5) * random.uniform(0.95, 1.05)
            recovery_days_left -= 1
        else:
            # 正常生长状态
            # 加入白噪声：测量误差或正常生理波动
            noise = random.uniform(-0.2, 0.2)
            # 确保即使有噪声，宏观趋势不变（单日增重如果加上负噪声导致掉秤过多，强行拉平）
            daily_gain = max(0.01, base_daily_gain + noise)
            
            # 采食量与增重正相关
            daily_feed = (1.5 + daily_gain * 3.0) * random.uniform(0.9, 1.1)

        # 更新当前体重
        current_weight += daily_gain
        
        # 单调递增底线最后防线：体重决不能比历史最低点还要低
        # （前面已经用 max(0.01, ...) 和约束的热应激掉秤幅度保证了宏观递增）
        
        # 添加轻微绝对白噪声 (模拟秤的误差)
        measured_weight = current_weight + random.uniform(-0.1, 0.1)

        data.append({
            "pig_id": f"LTW-{pig_id:03d}",
            "day_age": day,
            "weight_kg": round(measured_weight, 2),
            "daily_feed_intake_kg": round(daily_feed, 2),
            "avg_temperature": round(avg_temp, 1),
            "is_anomaly": 1 if (in_anomaly and day < anomaly_start + anomaly_duration) else 0
        })
        
    return data

def main():
    print(f"开始生成 {NUM_PIGS} 头两头乌生猪的 300 天生命周期时序数据...")
    all_data = []
    
    # 随机选择 4 头猪注入热应激异常
    anomaly_pigs = random.sample(range(1, NUM_PIGS + 1), 4)
    print(f"选定为异常样本(热应激)的猪只编号: {anomaly_pigs}")
    
    for i in range(1, NUM_PIGS + 1):
        has_anomaly = i in anomaly_pigs
        pig_data = generate_pig_data(i, has_anomaly)
        all_data.extend(pig_data)
        
    df = pd.DataFrame(all_data)
    
    # 验证是否满足单调递增约束
    print("正在验证生物学约束 (宏观单调递增)...")
    for pig_id in df['pig_id'].unique():
        pig_df = df[df['pig_id'] == pig_id].sort_values('day_age')
        weights = pig_df['weight_kg'].values
        
        # 允许微小的波动(热应激极其有限的掉秤，或秤的误差)，但整体必须递增
        # 检查是否出现连续3天以上大幅度下降
        diffs = np.diff(weights)
        large_drops = diffs < -0.5
        if np.any(large_drops):
            print(f"警告: 猪 {pig_id} 发生超过 0.5kg 的单日掉秤！")
            
        # 宏观检查 (100天 vs 200天)
        w_10 = weights[10]
        w_100 = weights[100]
        w_200 = weights[200]
        w_299 = weights[299]
        if not (w_10 < w_100 < w_200 < w_299):
            print(f"严重错误: 猪 {pig_id} 不符合宏观递增约束! {w_10}->{w_100}->{w_200}->{w_299}")

    df.to_csv(OUTPUT_FILE, index=False)
    print(f"数据生成完毕！已保存至 {OUTPUT_FILE}，总记录数: {len(df)}")

if __name__ == "__main__":
    main()
