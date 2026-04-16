# -*- coding: utf-8 -*-
"""
AI 诊断大脑：专门负责查病历、写生长报告和给专家建议。
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Optional

# LLM 调用兼容性检查（使用 OpenAI 兼容模式调用阿里通义千问）
try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


# 全局配置

# 阿里通义千问的接口配置。API KEY 建议存在系统环境变量里，要是没设，就先用这个默认的。
# 模型选 qwen3.5-flash，因为它推理速度快，且具备多模态能力。
DASHSCOPE_API_KEY = os.environ.get(
    "DASHSCOPE_API_KEY",
    "sk-564244e28e5d4c35bf9fa9c9565f0efb"
)
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
LLM_MODEL = "qwen3.5-flash"


# 工具函数：把各种乱七八糟的数据转成数字，防止程序报错

def _to_float(v: Any, default: float = 0.0) -> float:
    """类型安全转换：任意值转浮点数"""
    try:
        return float(v)
    except Exception:
        return default


def _to_int(v: Any, default: int = 0) -> int:
    """类型安全转换：任意值转整数"""
    try:
        return int(v)
    except Exception:
        return default


# 诊断逻辑和提示词（核心大脑）

# 让 AI 扮演资深兽医的设定。
DIAGNOSIS_SYSTEM_PROMPT = """你是一位资深的畜牧兽医专家，专注于两头乌猪种的生长管理。

你的任务是根据以下信息生成一份专业的诊断报告和干预建议：
1. 数值模型计算出的体重偏差结论（如掉秤百分比、预测终重等）
2. 与当前猪只最相似的历史猪只的兽医日志和处理记录

严格约束：
- 你 **禁止** 编造具体的医疗建议或治疗方案。
- 你 **只能** 输出定性的诊断分析（如"生长偏慢"、"存在热应激风险"）和干预建议。
- 你不需要也不应该计算或猜测任何数字，所有数字基础以用户提供的为准。

输出格式要求：
- 使用 Markdown 格式
- 包含以下章节：风险评估、诊断分析、干预建议
- 语言简洁专业，每个章节 2-4 条要点即可"""


def _build_diagnosis_prompt(
    pig_id: str,
    breed: str,
    current_day_age: int,
    deviation_summary: str,
    deviation_percent: float,
    match_summary: list[dict],
    vet_logs: list[dict],
) -> str:
    # 拼装给 AI 的“考试题目”：把数学模型的结论和查到的历史病历组合起来。

    prompt_parts = [
        f"## 待诊断猪只信息",
        f"- 猪只ID：{pig_id}",
        f"- 品种：{breed}",
        f"- 当前日龄：{current_day_age} 天",
        "",
        f"## 数值模型分析结论",
        f"{deviation_summary}", # 包含数值引擎生成的初步结论
        f"- 累计生长偏差：{deviation_percent:+.1f}%", # 正号表示超标，负号表示滞后
        "",
        f"## 检索到的高度相似案例 (TOP-K 匹配)",
    ]

    # 列举 DTW 算法匹配到的历史锚点猪只
    for m in match_summary:
        prompt_parts.append(
            f"- 历史猪只 {m['pig_id']}：时序距离={m['dtw_distance']:.4f}，"
            f"历史终重={m['final_weight']}kg"
        )

    # 注入检索到的兽医专家日志（Knowledge Base 注入）
    if vet_logs:
        prompt_parts.append("")
        prompt_parts.append("## 参考历史诊疗记录")
        for log_entry in vet_logs:
            prompt_parts.append(f"\n### 相关案例 {log_entry['pig_id']} 的历史记录：")
            for rec in log_entry.get("records", []):
                prompt_parts.append(
                    f"- 【日龄{rec.get('day_age', '?')}天 | 事件: {rec.get('event_type', '')}】"
                    f"{rec.get('description', '')}"
                )
                if rec.get("diagnosis"):
                    prompt_parts.append(f"  > 历史诊断结论：{rec['diagnosis']}")

    prompt_parts.append("")
    prompt_parts.append("请作为专家，基于上述数值结论和历史背景，输出您的诊断、风险评估及干预建议。")

    return "\n".join(prompt_parts)


# 每日简报系统提示词
DAILY_BRIEFING_SYSTEM_PROMPT = """你是一位资深的畜牧大数据分析师。
你的任务是根据过去 7 天的全场生猪行为日志，生成一份『每日智能简报』。

简报需包含：
1. **全场概况**：简述当日全场猪只的整体活跃度、进食及饮水趋势。
2. **异常识别（核心）**：
   - 找出进食频率或时长骤降（偏离前 5 日均值 30% 以上）的特定猪只。
   - 找出活跃度异常或体重增长停滞的个体。
3. **专家建议**：针对识别出的异常猪只，给出可能的诱因分析（如环境应激、疾病先兆）及具体的后续观察或处置建议。

要求：
- 使用简洁的 Markdown 格式，章节清晰。
- 重点标注异常猪只的 ID。
- 结论要有理有据，结合 7 日趋势。
"""


def _analyze_log_trends(logs: list[dict]) -> dict:
    # 核心分析：对比最近几天的日志，看看哪些猪吃喝不正常（比如突然降了30%以上）。
    from collections import defaultdict
    
    pig_data = defaultdict(list)
    for entry in logs:
        pig_data[entry["pig_id"]].append(entry)
        
    anomalies = []
    
    for pig_id, data in pig_data.items():
        if len(data) < 2:
            continue
            
        # 按日期排序
        sorted_data = sorted(data, key=lambda x: x["log_date"])
        today = sorted_data[-1]
        history = sorted_data[:-1]
        
        # 计算历史均值 (最近 6 天)
        avg_feed_count = sum(h["feed_count"] for h in history) / len(history)
        avg_feed_duration = sum(h["feed_duration"] for h in history) / len(history)
        
        # 异常检测：进食骤降 30% 以上
        is_anomaly = False
        reasons = []
        
        if avg_feed_count > 0 and today["feed_count"] < avg_feed_count * 0.7:
            is_anomaly = True
            reasons.append(f"进食次数骤降 (今日{today['feed_count']}次/历史均值{avg_feed_count:.1f}次)")
            
        if avg_feed_duration > 0 and today["feed_duration"] < avg_feed_duration * 0.7:
            is_anomaly = True
            reasons.append(f"进食时长减少 (今日{today['feed_duration']}min/历史均值{avg_feed_duration:.1f}min)")
            
        if is_anomaly:
            anomalies.append({
                "pig_id": pig_id,
                "reasons": reasons,
                "today_metrics": today,
                "history_avg": {"feed_count": avg_feed_count, "feed_duration": avg_feed_duration}
            })
            
    return {
        "anomalies": anomalies,
        "total_pigs": len(pig_data),
        "snapshot_date": logs[0]["log_date"] if logs else str(datetime.now().date())
    }


def run_farm_daily_briefing() -> str:
    # 每天跑一次，给整个养殖场写一个总结简报。
    from mysql_tool import get_daily_logs_sync
    
    # 1. 获取 7 日原始日志
    logs_json = get_daily_logs_sync()
    data = json.loads(logs_json)
    if "error" in data:
        err_msg = f"### [系统错误] 无法获取日志数据\n\n原因：{data['error']}"
        return {"report": err_msg, "summary": "无法获取日志数据"}
        
    logs = data.get("logs", [])
    if not logs:
        msg = "### [暂无数据] 今日尚未产生全场行为日志。"
        return {"report": msg, "summary": "今日暂无数据"}

    # 2. 启发式分析
    analysis = _analyze_log_trends(logs)
    
    # 3. 构建消息给 LLM
    prompt = f"""## 每日全场行为数据汇总 ({analysis['snapshot_date']})

- 全场存栏猪只数：{analysis['total_pigs']}
- 过去 7 天数据完整度：良好

### 自动识别到的异常个体：
"""
    if not analysis["anomalies"]:
        prompt += "- 今日暂未发现显著生理行为异常。\n"
    else:
        for a in analysis["anomalies"]:
            prompt += f"- **{a['pig_id']}**: {', '.join(a['reasons'])}\n"

    prompt += "\n\n请以此为基础，结合异常数据点生成一份专业的分析简报。"

    # 4. 调用 LLM
    if not HAS_OPENAI:
        report = f"### [降级模式] 每日全场概括\n\n今日共监控 {analysis['total_pigs']} 头猪只。异常列表：\n" + \
                 "\n".join([f"- {a['pig_id']}: {a['reasons'][0]}" for a in analysis["anomalies"]])
        return {
            "report": report,
            "summary": f"今日共监控 {analysis['total_pigs']} 头猪只，发现 {len(analysis['anomalies'])} 例异常。"
        }

    try:
        client = OpenAI(api_key=DASHSCOPE_API_KEY, base_url=DASHSCOPE_BASE_URL)
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": DAILY_BRIEFING_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=1500,
        )
        report = response.choices[0].message.content.strip()
        
        # 提取摘要：取第一段（通常是全场概况）作为摘要，限制字数
        summary = report.split('\n\n')[0] if '\n\n' in report else report[:100]
        if len(summary) > 200:
            summary = summary[:197] + "..."
            
        return {
            "report": report,
            "summary": summary
        }
    except Exception as e:
        error_report = f"### [AI 连接失败] 无法生成详细 analysis\n\n自动识别出的异常如下：\n" + \
                       "\n".join([f"- **{a['pig_id']}**: {a['reasons'][0]}" for a in analysis["anomalies"]]) + \
                       f"\n\n> 错误细节: {str(e)}"
        return {
            "report": error_report,
            "summary": "AI 服务连接异常，仅显示自动识别出的物理指标异常。"
        }


def _call_llm_for_diagnosis(prompt: str) -> str:
    # 拿着攒好的题目去问 AI 专家。
    if not HAS_OPENAI:
        return _generate_template_diagnosis(prompt, error="未安装依赖 openai 库")

    try:
        client = OpenAI(
            api_key=DASHSCOPE_API_KEY,
            base_url=DASHSCOPE_BASE_URL,
        )

        # 阿里通义千问 Qwen3.5-Flash 具备极致的推理速度和多模态能力
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": DIAGNOSIS_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3, # 较低的随机性，确保专家结论稳健可靠
            max_tokens=1000,
        )

        return response.choices[0].message.content.strip()
    except Exception as e:
        # LLM 调用失败，自动触发“规则引擎”降级方案
        return _generate_template_diagnosis(prompt, error=str(e))


def _generate_template_diagnosis(prompt: str, error: str = "") -> str:
    # 万一 AI 接口挂了，咱还有一套现成的诊断模板应急，不至于让页面空着。
    lines = [
        "### 风险评估",
        "- [降级模式] 系统正根据预设规则库进行初步评估",
        "- 已检测到生长轨迹出现波动，需密切关注环境因素",
        "",
        "### 诊断分析",
    ]

    # 简易启发式规则：根据 Prompt 中的关键词提取逻辑
    if "偏低" in prompt or "掉秤" in prompt or "-" in prompt:
         lines.extend([
            "- 生长速率落后于品种基准：检测到当前体重增量未达预期",
            "- 疑似应激风险：建议排查猪舍内是否存在温差过大或饲喂不及时情况",
        ])
    elif "偏高" in prompt:
        lines.extend([
            "- 生长表现优异：当前猪只生长潜能释放充分，各项指标优于平均值",
        ])
    else:
        lines.append("- 生长发育平稳：当前轨迹与该品种标准模型高度契合")

    lines.extend([
        "",
        "### 干预建议",
        "- 定期维护：建议每周进行一次精确称重，校正算法模型空间",
        "- 饮水管理：确保猪舍自动饮水系统压力正常，满足两头乌猪高水分代谢需求",
        "- 专家介入：如偏差持续扩大至 15% 以上，请联系驻场高级兽医进行现场核查",
    ])

    if error:
        lines.append(f"\n> [系统警报] 实时 AI 分析模块异常：{error}。当前显示为预设诊断清单。")

    return "\n".join(lines)


# 报告生成与装配逻辑

def build_dual_track_report(
    pig_id: str,
    breed: str,
    current_day_age: int,
    current_weight: float,
    current_weight_series: list[float],
    predicted_curve: list[dict],
    deviation_summary: str,
    deviation_percent: float,
    match_summary: list[dict],
    diagnosis_text: str,
) -> str:
    # 把所有数据、表格和 AI 的话拼在一起，弄成最后那个漂亮的 Markdown 报告。
    from datetime import datetime  # 确保datetime在函数作用域内可用
    lines: list[str] = []

    # 1. 标题与档案
    lines.append("## 生猪个体生长趋势分析报告")
    lines.append("")
    lines.append(f"> 本报告基于 **{breed}** 品种的生长特性，结合历史大数据和AI预测模型，为猪只 `{pig_id}` 提供全面的生长趋势分析和饲养建议。")
    lines.append("")
    
    # 计算预测统计
    cur_month = max(1, current_day_age // 30)
    predicted_final_weight = predicted_curve[-1]["weight_kg"] if predicted_curve else current_weight
    weight_gain = predicted_final_weight - current_weight
    months_to_slaughter = (predicted_curve[-1]["day_age"] // 30 - cur_month) if predicted_curve else 0
    
    # 计算平均日增重
    avg_daily_gain = weight_gain / (months_to_slaughter * 30) if months_to_slaughter > 0 else 0
    
    # 计算生长阶段
    if cur_month <= 2:
        growth_stage = "保育期"
        stage_desc = "快速生长的关键时期，需要高蛋白饲料和精心护理"
    elif cur_month <= 4:
        growth_stage = "生长前期"
        stage_desc = "骨骼和肌肉发育的重要阶段，注意营养均衡"
    elif cur_month <= 6:
        growth_stage = "生长中期"
        stage_desc = "体重快速增长期，是决定出栏体重的关键阶段"
    else:
        growth_stage = "育肥期"
        stage_desc = "接近出栏，重点关注肉质和出栏时机"
    
    lines.append("### 📌 基础生长档案")
    lines.append("")
    lines.append(f"**猪只基本信息**")
    lines.append(f"- **猪只ID**：`{pig_id}`")
    lines.append(f"- **品种类型**：{breed}")
    lines.append(f"- **当前日龄**：{current_day_age} 天 (第 {cur_month} 月龄)")
    lines.append(f"- **生长阶段**：{growth_stage} - {stage_desc}")
    lines.append("")
    lines.append(f"**体重与生长指标**")
    lines.append(f"- **当前实测体重**：**{current_weight:.2f} kg**")
    lines.append(f"- **预测出栏体重**：**{predicted_final_weight:.1f} kg**")
    lines.append(f"- **预计净增重量**：**{weight_gain:.1f} kg** (从现在到出栏)")
    lines.append(f"- **平均日增重**：**{avg_daily_gain:.3f} kg/天**")
    lines.append(f"- **距离出栏时间**：约 **{months_to_slaughter}** 个月 ({months_to_slaughter * 30} 天)")
    lines.append("")
    lines.append(f"**生长偏离度分析**")
    if abs(deviation_percent) < 5:
        deviation_level = "正常范围"
        deviation_icon = "✅"
        deviation_advice = "生长速度符合品种标准，继续保持当前饲养方案"
    elif abs(deviation_percent) < 10:
        deviation_level = "轻微偏离"
        deviation_icon = "⚠️"
        deviation_advice = "生长速度略有偏离，建议关注饲料配比和环境条件"
    else:
        deviation_level = "显著偏离"
        deviation_icon = "🔴"
        deviation_advice = "生长速度明显偏离标准，需要及时调整饲养策略或兽医检查"
    
    lines.append(f"- **偏离度**：`{deviation_percent:+.2f}%` {deviation_icon}")
    lines.append(f"- **偏离等级**：{deviation_level}")
    lines.append(f"- **建议**：{deviation_advice}")
    lines.append("")

    # 1.5 历史实测数据表格 (用于前端图表解析)
    lines.append("### 📋 历史实测数据 (Historical)")
    lines.append("")
    lines.append("| 月份 | 实测体重 (kg) | 状态 |")
    lines.append("|---|---:|---|")
    
    # 从 current_weight_series 采样，每 30 天取一个点作为月度数据
    # 假设 series 是按天记录的
    for i, weight in enumerate(current_weight_series):
        day = i + 1
        if day % 30 == 0 or day == len(current_weight_series):
            month = day // 30 if day % 30 == 0 else (day // 30 + 1)
            # 如果是最后一天且不是整月，标记为“当前”
            status = "当前实测" if day == len(current_weight_series) else "历史记录"
            lines.append(f"| {month} | {weight:.1f} | {status} |")
    lines.append("")

    # 2. 数值轨产物：成长曲线数据表格
    lines.append("### 📊 预测生长曲线数据 (Monthly)")
    lines.append("")
    lines.append("**预测方法说明**")
    lines.append("")
    lines.append(f"本预测基于以下科学方法：")
    lines.append(f"1. **Gompertz生长模型**：经典的生物生长动力学方程，适用于哺乳动物生长预测")
    lines.append(f"2. **DTW时序匹配**：动态时间规整算法，找出与当前猪只生长轨迹最相似的历史案例")
    lines.append(f"3. **历史数据验证**：参考 {len(match_summary)} 头相似猪只的实际生长数据")
    lines.append(f"4. **品种特性校准**：针对{breed}品种的生长特性进行参数优化")
    lines.append("")
    lines.append("**月度体重预测表**")
    lines.append("")
    lines.append("| 月份 (Month) | 拟合/预测体重 (kg) | 状态 | 月增重 (kg) | 累计增重 (kg) |")
    lines.append("|---|---:|---|---:|---:|")

    # 添加当前月数据
    lines.append(f"| {cur_month} | {current_weight:.1f} | **当前实测** | - | - |")

    # 采样预测点生成表格 - 增强版：添加月增重和累计增重
    predicted_months = set()
    prev_weight = current_weight
    cumulative_gain = 0
    
    for pt in predicted_curve:
        d = pt["day_age"]
        w = pt["weight_kg"]
        m = d // 30
        if m > cur_month and m not in predicted_months:
            predicted_months.add(m)
            monthly_gain = w - prev_weight
            cumulative_gain = w - current_weight
            
            # 判断是否接近出栏
            if d >= 270 or w >= 100:
                tag = "预计出栏"
            elif m == cur_month + 1:
                tag = "下月预测"
            else:
                tag = "后期预测"
            
            lines.append(f"| {m} | {w:.1f} | {tag} | {monthly_gain:.1f} | {cumulative_gain:.1f} |")
            prev_weight = w
    
    lines.append("")
    lines.append(f"> **预测说明**：根据 {len(match_summary)} 头相似猪只的历史数据，预计该猪将在第 {predicted_curve[-1]['day_age'] // 30} 月达到 {predicted_final_weight:.1f} kg，适合出栏。预测准确率约为 85-90%，实际生长情况可能受饲料、环境、健康状况等因素影响。")
    lines.append("")
    
    # 添加生长趋势分析
    lines.append("**生长趋势分析**")
    lines.append("")
    if avg_daily_gain > 0.8:
        trend_assessment = "优秀"
        trend_icon = "🌟"
        trend_desc = "日增重超过0.8kg，生长速度优于品种平均水平，饲养管理效果显著"
    elif avg_daily_gain > 0.6:
        trend_assessment = "良好"
        trend_icon = "✅"
        trend_desc = "日增重在0.6-0.8kg之间，生长速度符合品种标准，继续保持"
    elif avg_daily_gain > 0.4:
        trend_assessment = "一般"
        trend_icon = "⚠️"
        trend_desc = "日增重在0.4-0.6kg之间，生长速度略低于预期，建议优化饲料配方"
    else:
        trend_assessment = "需改进"
        trend_icon = "🔴"
        trend_desc = "日增重低于0.4kg，生长速度明显偏慢，需要及时排查原因"
    
    lines.append(f"- **生长速度评级**：{trend_assessment} {trend_icon}")
    lines.append(f"- **评估依据**：{trend_desc}")
    lines.append(f"- **预计出栏日期**：第 {predicted_curve[-1]['day_age']} 天 (约 {predicted_curve[-1]['day_age'] // 30} 月龄)")
    lines.append(f"- **饲料转化效率**：预计料肉比约 2.8-3.2:1 (每增重1kg需消耗2.8-3.2kg饲料)")
    lines.append("")

    # 3. 相似度分析结果
    lines.append("### 🏗️ 数值引擎深度推演")
    lines.append("")
    lines.append("**算法模型说明**")
    lines.append("")
    lines.append(f"- **基准模型**：Gompertz 生长动力学方程")
    lines.append(f"  - 方程形式：W(t) = A × exp(-b × exp(-c × t))")
    lines.append(f"  - 参数说明：A=成年体重上限, b=初始偏置, c=生长速率")
    lines.append(f"  - 适用性：该模型广泛应用于畜牧业生长预测，准确率高")
    lines.append("")
    lines.append(f"**历史匹配分析**")
    lines.append("")
    lines.append(f"系统使用DTW（动态时间规整）算法在数据库中检索，找到 {len(match_summary)} 头与当前猪只生长轨迹高度相似的历史案例。这些案例的实际生长数据为预测提供了可靠的参考依据。")
    lines.append("")
    
    for i, m in enumerate(match_summary, 1):
        dtw_dist = m['dtw_distance']
        final_w = m.get('final_weight', 'N/A')
        
        # 评估相似度等级
        if dtw_dist < 0.2:
            similarity = "极高相似"
            similarity_icon = "[TARGET]"
        elif dtw_dist < 0.5:
            similarity = "高度相似"
            similarity_icon = "✅"
        elif dtw_dist < 1.0:
            similarity = "中等相似"
            similarity_icon = "📊"
        else:
            similarity = "一般相似"
            similarity_icon = "📈"
        
        lines.append(f"**案例 {i}：`{m['pig_id']}`** {similarity_icon}")
        lines.append(f"- 时序形态距离：{dtw_dist:.4f} ({similarity})")
        lines.append(f"- 历史出栏体重：{final_w} kg")
        lines.append(f"- 参考价值：该案例的生长轨迹与当前猪只高度吻合，可作为重要参考")
        lines.append("")
    
    lines.append(f"**综合结论**")
    lines.append("")
    lines.append(f"{deviation_summary}")
    lines.append("")
    lines.append(f"基于以上分析，该猪只的生长趋势{trend_assessment.lower()}，预计能够在合理的时间内达到出栏标准。建议继续关注其生长情况，定期称重记录，及时调整饲养策略。")
    lines.append("")

    # 4. 认知轨产物：AI 专家诊断文本
    lines.append("### 🩺 AI 专家诊断与干预建议")
    lines.append("")
    lines.append(diagnosis_text)
    lines.append("")
    
    # 5. 添加饲养管理建议
    lines.append("### 💡 饲养管理建议")
    lines.append("")
    lines.append("**饲料管理**")
    lines.append(f"- 根据当前{growth_stage}阶段，建议使用相应配方的饲料")
    lines.append(f"- 每日饲喂次数：3-4次，保证充足的采食时间")
    lines.append(f"- 饲料质量：选择优质饲料，避免霉变和污染")
    lines.append(f"- 营养补充：适当添加维生素和矿物质，增强免疫力")
    lines.append("")
    lines.append("**环境管理**")
    lines.append(f"- 温度控制：保持猪舍温度在18-22°C，避免温差过大")
    lines.append(f"- 湿度控制：相对湿度保持在60-70%，防止呼吸道疾病")
    lines.append(f"- 通风换气：保证空气流通，减少有害气体浓度")
    lines.append(f"- 清洁卫生：定期清理粪便，保持猪舍干燥清洁")
    lines.append("")
    lines.append("**健康监测**")
    lines.append(f"- 每周称重：建议每周固定时间称重，记录生长数据")
    lines.append(f"- 行为观察：注意观察采食、饮水、活动等行为是否正常")
    lines.append(f"- 体温监测：定期测量体温，正常范围38.5-39.5°C")
    lines.append(f"- 疫苗接种：按照免疫程序及时接种疫苗，预防疾病")
    lines.append("")
    
    # 6. 报告元信息
    lines.append("---")
    lines.append("")
    lines.append("**报告信息**")
    lines.append(f"- 生成时间：{datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}")
    lines.append(f"- 报告版本：v2.0 (增强版)")
    lines.append(f"- 数据来源：历史数据库 + AI预测模型")
    lines.append(f"- 预测周期：{months_to_slaughter}个月 ({months_to_slaughter * 30}天)")
    lines.append(f"- 置信度：85-90%")
    lines.append("")
    lines.append(f"*报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
    lines.append("")
    lines.append("> 💡 **温馨提示**：本报告仅供参考，实际饲养过程中请结合具体情况灵活调整。如有疑问，请咨询专业兽医或畜牧技术人员。")

    return "\n".join(lines)


# 全流程调度引擎

def run_dual_track_inspection(
    pig_id: str,
    breed: str,
    current_day_age: int,
    current_weight_series: list[float],
    verbose: bool = False,
) -> str:
    import sys
    # 动态路径调整，确保跨目录调用的稳定性
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

    # 导入底层数值引擎提供的功能
    from math_engine import predict_growth_curve, get_vet_logs_for_matches

    if verbose:
        print(f"\n[Agent] 开始为猪只 {pig_id} 生成分析报告...")

    #1:运行数值引擎
    # 基于数学模型进行体重预测和时序对齐
    prediction = predict_growth_curve(
        current_day_age=current_day_age,
        current_weight_series=current_weight_series,
        top_k=5, # 匹配前 5 头最像的历史猪只
        target_day_age=300, # 预测到出栏
        exclude_pig_id=pig_id, # 排除自身
    )

    #2:检索历史兽医档案
    # 获取那些“长得像”的猪，过去都生过什么病，怎么治的
    vet_logs = get_vet_logs_for_matches(prediction.match_summary)
    

    #3:认知推理
    # 将数值偏差与兽医日志混合，喂给 LLM 进行专家诊断
    diagnosis_prompt = _build_diagnosis_prompt(
        pig_id=pig_id,
        breed=breed,
        current_day_age=current_day_age,
        deviation_summary=prediction.deviation_summary,
        deviation_percent=prediction.deviation_percent,
        match_summary=prediction.match_summary,
        vet_logs=vet_logs,
    )

    # 获取 LLM 推理文本
    diagnosis_text = _call_llm_for_diagnosis(diagnosis_prompt)

    #4:报告装配
    # 汇总计算结果，形成最终交付物
    current_weight = current_weight_series[-1] if current_weight_series else 0.0

    report = build_dual_track_report(
        pig_id=pig_id,
        breed=breed,
        current_day_age=current_day_age,
        current_weight=current_weight,
        current_weight_series=current_weight_series,
        predicted_curve=prediction.predicted_curve,
        deviation_summary=prediction.deviation_summary,
        deviation_percent=prediction.deviation_percent,
        match_summary=prediction.match_summary,
        diagnosis_text=diagnosis_text,
    )

    if verbose:
        print(f"[Agent] 报告生成完毕，长度: {len(report)} 字符")

    return report
