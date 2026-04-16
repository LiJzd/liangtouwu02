import sys
import os

# 将 ai-service 目录添加到 path
sys.path.append(r'c:\Users\lost\Desktop\两头乌\ai-service')

from pig_rag.pig_agent import build_dual_track_report

# 模拟数据
pig_id = "PIG001"
breed = "两头乌"
current_day_age = 150
current_weight = 85.5
current_weight_series = [15.0 + i * 0.5 for i in range(150)] 
predicted_curve = [{"day_age": 180, "weight_kg": 100.0}, {"day_age": 210, "weight_kg": 110.0}]
deviation_summary = "生长良好"
deviation_percent = 2.5
match_summary = [{"pig_id": "HIST_001", "dtw_distance": 0.1, "final_weight": 115}]
diagnosis_text = "建议继续保持"

print("正在构建报告...")
report = build_dual_track_report(
    pig_id, breed, current_day_age, current_weight, current_weight_series,
    predicted_curve, deviation_summary, deviation_percent, match_summary, diagnosis_text
)

print("\n--- 报告内容摘要 ---")
if "### 📋 历史实测数据 (Historical)" in report:
    print("Found section: Historical data")
    # 打印表格部分
    start_idx = report.find("### 📋 历史实测数据 (Historical)")
    end_idx = report.find("### 📊 预测生长曲线数据")
    print(report[start_idx:end_idx])
    print("\nVerification Success: Report contains historical data table.")
else:
    print(report[:1000])
    print("\nVerification Failure: Report does NOT contain historical data table.")
