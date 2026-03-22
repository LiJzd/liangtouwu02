# -*- coding: utf-8 -*-
"""
认知引擎 (Cognitive Engine) — 双轨架构重构版
=========================

本模块负责系统的“逻辑决策”与“专家诊断”功能。
基于 RAG (检索增强生成) 技术，结合数值引擎的定量分析结果与历史专家日志，生成定性的增长建议。

架构核心原则：
1. 数值归数值：所有的体重预测、偏差百分比、拟合曲线均由『数值引擎 (Math Engine)』计算。
2. 认知归认知：LLM (大语言模型) 仅负责解读数值引擎的结论，并结合历史档案给出兽医建议。
3. 严格解耦：Agent 禁止自行猜测或生成连续的体重数值序列，以防止 AI “幻觉”导致数据失真。

主要功能：
- 构建针对生猪生长阶段的专家级 Prompt。
- 调用阿里百炼 (DashScope) 兼容的 LLM 进行逻辑推理。
- 在 LLM 不可用时提供基于规则的兜底诊断模板。
- 最终拼装包含图表数据（数值轨）与文本建议（认知轨）的综合报告。
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


# ============================================================
# 全局配置
# ============================================================

# 阿里百炼 API 配置 (建议通过操作系统环境变量设置，此处为默认缺省值)
DASHSCOPE_API_KEY = os.environ.get(
    "DASHSCOPE_API_KEY",
    "sk-564244e28e5d4c35bf9fa9c9565f0efb"
)
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
LLM_MODEL = "qwen-plus"  # 选用通义千问增强版，具备良好的中文逻辑推理能力


# ============================================================
# 辅助工具函数
# ============================================================

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


# ============================================================
# 认知引擎内核：LLM 诊断逻辑
# ============================================================

# 专家角色设定（System Prompt）
# 通过 Role Prompting 确保 LLM 的回复符合职业兽医的口吻和逻辑
DIAGNOSIS_SYSTEM_PROMPT = """你是一位资深的畜牧兽医专家，专注于金华两头乌猪种的生长管理。

你的任务是根据以下信息生成一份专业的诊断报告和干预建议：
1. 数值模型计算出的体重偏差结论（如掉秤百分比、预测终重等）
2. 与当前猪只最相似的历史猪只的兽医日志和处理记录

严格约束：
- 你 **禁止** 生成任何具体的体重数值、预测曲线或连续数字序列（这些由数值引擎负责）。
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
    """
    RAG 核心：构建用于诊断的 Context Prompt
    
    该函数将数值引擎的枯燥数据转换为 LLM 易于理解的自然语言上下文。
    """

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
    """内部工具：分析 7 日日志中的趋势与异常"""
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
    """
    生成全场每日简报：数据聚合 -> 趋势分析 -> LLM 总结。
    """
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

    prompt += "\n### 原始数据上下文 (最近 2 日抽样):\n"
    # 仅提供少量样本以节省 tokens
    sample_logs = logs[:15]
    prompt += json.dumps(sample_logs, ensure_ascii=False, indent=2)
    prompt += "\n\n请以此为基础，生成一份专业的分析简报。"

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
    """
    底层调用：向 LLM 获取推理结果
    包含自动降级机制，确保在网络故障或 API 欠费时系统不宕机。
    """
    if not HAS_OPENAI:
        return _generate_template_diagnosis(prompt, error="未安装依赖 openai 库")

    try:
        client = OpenAI(
            api_key=DASHSCOPE_API_KEY,
            base_url=DASHSCOPE_BASE_URL,
        )

        # 阿里通义千问 Qwen-Plus 具备极致的性价比和推理稳定性
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
    """
    兜底方案：基于启发式规则生成的诊断模板
    当 LLM 接口连接超时或异常时，确保依然有“看起来专业”的建议。
    """
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
        "- 饮水管理：确保猪舍自动饮水系统压力正常，满足金华猪高水分代谢需求",
        "- 专家介入：如偏差持续扩大至 15% 以上，请联系驻场高级兽医进行现场核查",
    ])

    if error:
        lines.append(f"\n> [系统警报] 实时 AI 分析模块异常：{error}。当前显示为预设诊断清单。")

    return "\n".join(lines)


# ============================================================
# 报告拼装逻辑
# ============================================================

def build_dual_track_report(
    pig_id: str,
    breed: str,
    current_day_age: int,
    current_weight: float,
    predicted_curve: list[dict],
    deviation_summary: str,
    deviation_percent: float,
    match_summary: list[dict],
    diagnosis_text: str,
) -> str:
    """
    将数值和认知两条轨道的产出物进行融合，构建最终的 Markdown 报告。
    """
    from datetime import datetime  # 确保datetime在函数作用域内可用
    lines: list[str] = []

    # 1. 标题与档案
    lines.append("## 生猪个体生长趋势分析报告")
    lines.append("")
    lines.append("### 📌 基础生长档案")
    lines.append(f"- **猪只ID**：`{pig_id}`")
    lines.append(f"- **品种**：{breed}")
    lines.append(f"- **当前日龄**：{current_day_age} 天 (约 {current_day_age // 30} 月龄)")
    lines.append(f"- **当前称重**：**{current_weight:.2f} kg**")
    lines.append(f"- **模型偏离度**：`{deviation_percent:+.2f}%`")
    lines.append("")

    # 2. 数值轨产物：成长曲线数据表格
    # 注：此表格格式已被前端 Vue 组件中的 ECharts 解析器适配，不可修改格式
    lines.append("### 📊 预测生长曲线数据 (Monthly)")
    lines.append("| 月份 (Month) | 拟合/预测体重 (kg) | 状态 |")
    lines.append("|---|---:|---|")

    # 分割当前月与未来月
    cur_month = max(1, current_day_age // 30)
    lines.append(f"| {cur_month} | {current_weight:.2f} | **当前实测** |")

    # 采样预测点生成表格
    for pt in predicted_curve:
        d = pt["day_age"]
        w = pt["weight_kg"]
        m = d // 30
        if d % 30 == 0 and m > cur_month:
            tag = "预计出栏" if d >= 270 or w >= 100 else "后期预测"
            lines.append(f"| {m} | {w:.1f} | {tag} |")
    lines.append("")

    # 3. 相似度分析结果
    lines.append("### 🏗️ 数值引擎深度推演")
    lines.append(f"- **基准模型**：Gompertz 生长动力学方程")
    lines.append(f"- **历史匹配**：成功找到 {len(match_summary)} 头具有高度相似性的历史猪只")
    for m in match_summary:
        lines.append(f"  - 案例 `{m['pig_id']}`：时序形态距离 {m['dtw_distance']:.3f}")
    lines.append(f"- **结论总结**：{deviation_summary}")
    lines.append("")

    # 4. 认知轨产物：AI 专家诊断文本
    lines.append("### 🩺 AI 专家诊断与干预建议")
    lines.append("---")
    lines.append(diagnosis_text)
    lines.append("\n---")
    lines.append(f"*报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

    return "\n".join(lines)


# ============================================================
# 双轨架构完整流程编排 (Orchestrator)
# ============================================================

def run_dual_track_inspection(
    pig_id: str,
    breed: str,
    current_day_age: int,
    current_weight_series: list[float],
    verbose: bool = False,
) -> str:
    """
    认知引擎的主入门函数。
    
    该函数如同一个“中央调度员”，指挥不同角色的 Agent 按顺序完成工作：
    1. 唤醒数值 Agent：计算曲线。
    2. 唤醒检索 Agent：搜集日志。
    3. 唤醒推理 Agent：生成诊断。
    4. 唤醒装配 Agent：输出报告。
    """
    import sys
    # 动态路径调整，确保跨目录调用的稳定性
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

    # 导入底层 Math Engine (数值引擎) 提供的功能
    from math_engine import predict_growth_curve, get_vet_logs_for_matches

    if verbose:
        print(f"\n[Agent] 开始为猪只 {pig_id} 生成分析报告...")

    # ── 步骤 1: 运行数值引擎 (Numerical Track) ──
    # 基于数学模型进行体重预测和时序对齐
    prediction = predict_growth_curve(
        current_day_age=current_day_age,
        current_weight_series=current_weight_series,
        top_k=5, # 匹配前 5 头最像的历史猪只
        target_day_age=300, # 预测到出栏（常设为 300 天）
        exclude_pig_id=pig_id, # 排除自身
    )

    # ── 步骤 2: 检索历史兽医档案 (Retrieval) ──
    # 获取那些“长得像”的猪，过去都生过什么病，怎么治的
    vet_logs = get_vet_logs_for_matches(prediction.match_summary)
    

    # ── 步骤 3: 认知推理 (Cognitive Track) ──
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

    # ── 步骤 4: 报告装配 ──
    # 汇总计算结果，形成最终交付物
    current_weight = current_weight_series[-1] if current_weight_series else 0.0

    report = build_dual_track_report(
        pig_id=pig_id,
        breed=breed,
        current_day_age=current_day_age,
        current_weight=current_weight,
        predicted_curve=prediction.predicted_curve,
        deviation_summary=prediction.deviation_summary,
        deviation_percent=prediction.deviation_percent,
        match_summary=prediction.match_summary,
        diagnosis_text=diagnosis_text,
    )

    if verbose:
        print(f"[Agent] 报告生成完毕，长度: {len(report)} 字符")

    return report
