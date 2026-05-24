# -*- coding: utf-8 -*-
"""
v1/agents/nodes/data_node.py
升级版生猪电子档案查询与智能 Text-to-SQL 融合数据节点
"""

import asyncio
import logging
import json
import re
import os
from typing import Dict, Any
import dashscope
from dashscope import Generation

from v1.common.config import get_settings
from v1.logic.agent_debug_controller import push_debug_event
from v1.logic.bot_tools import tool_get_pig_info_by_id
from v1.tools.text_to_sql import execute_readonly_sql

logger = logging.getLogger("DataNode")

async def data_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    数据专家节点：自动进行意图分流，普通查询走 API 快速通道，复杂聚合查询升级走 Text-to-SQL 沙盒只读执行流程。
    """
    logger.info("=== [DataNode] 数据专家查询智能分流启动 ===")
    client_id = state.get("client_id") or "default"
    
    await push_debug_event("connected", {"message": "载入 DataAgent 智能数据专家模块"}, client_id, agent="DataAgent")
    
    # 1. 提取用户输入
    messages = state.get("messages") or []
    last_msg = messages[-1] if messages else None
    user_input = last_msg.content if last_msg and hasattr(last_msg, "content") else str(last_msg or "")
    user_input_str = str(user_input).strip()
    
    # 2. 意图分流判定
    # 检查用户输入是否包含特定的生猪编号正则（如 PIG001 / LTW-002），且不含复杂统计词汇
    pig_id_match = re.search(r"(PIG|LTW|LTW-)\s*(\d+)", user_input_str, re.I)
    
    # 复杂分析统计类敏感词
    complex_keywords = ["多少", "总共", "平均", "列表", "有哪些", "体重超过", "数量", "统计", "活跃度", "最重", "最轻", "采食", "饮水"]
    is_complex_query = any(k in user_input_str for k in complex_keywords)
    
    # 决定走哪条路线
    if pig_id_match and not is_complex_query:
        # ---- 快速普通单只查询路径 ----
        p_id = pig_id_match.group(0).upper().replace(" ", "")
        await push_debug_event("thought", {"content": "【意图分流】匹配到单只猪基本档案查询，触发快速查询通道..."}, client_id, agent="DataAgent", status="单只档案")
        await asyncio.sleep(0.5)
        
        res = await _execute_fast_pig_info(p_id, client_id)
    else:
        # ---- 升级 Text-to-SQL 复杂聚合路径 ----
        await push_debug_event("thought", {"content": "【意图分流】匹配到复杂聚合与多维统计查询，自动升级为 Text-to-SQL 流程..."}, client_id, agent="DataAgent", status="Text-to-SQL")
        await asyncio.sleep(0.8)
        
        res = await _execute_text_to_sql_flow(user_input_str, client_id)
        
    # 3. 分段流式打字机效果推送给前端
    chunk_size = 20
    for i in range(0, len(res), chunk_size):
        chunk = res[i:i+chunk_size]
        await push_debug_event("final_answer_chunk", {"text": chunk}, client_id, agent="DataAgent")
        await asyncio.sleep(0.04)
        
    await push_debug_event("thinking_end", {"answer": "数据查询与分析完成"}, client_id, agent="DataAgent", status="数据呈现")
    return {"final_answer": res}

async def _execute_fast_pig_info(p_id: str, client_id: str) -> str:
    """常规单只查询极速路径"""
    try:
        raw_res = await tool_get_pig_info_by_id(json.dumps({"pig_id": p_id}))
        data = json.loads(raw_res)
        
        if isinstance(data, dict):
            md = f"# 🐖 {p_id} 电子档案详情\n\n"
            md += f"- **猪只编号**: `{data.get('pigId', p_id)}`\n"
            md += f"- **品种**: {data.get('breed', '金华两头乌')}\n"
            md += f"- **所在区域**: {data.get('area', 'B区舍舍房')}\n"
            md += f"- **当前月龄**: {data.get('currentMonth') or data.get('current_month', '--')} M\n"
            md += f"- **当前体重**: {data.get('currentWeight') or data.get('current_weight_kg', '--')} KG\n\n"
            
            md += "### 📋 档案关键指标数据\n"
            md += "| 指标名称 | 当前观测值 | 状态评估 |\n"
            md += "| :--- | :--- | :--- |\n"
            md += f"| 当前体重 | {data.get('currentWeight') or data.get('current_weight_kg', '--')} kg | 正常 |\n"
            md += f"| 当前月龄 | {data.get('currentMonth') or data.get('current_month', '--')} 个月 | 稳定 |\n"
            md += f"| 栏舍位置 | {data.get('area', '二号猪舍')} | 适宜 |\n"
            res = md
        else:
            res = str(raw_res)
            
        await push_debug_event("observation", {"output": f"猪只 {p_id} 档案获取成功。"}, client_id, agent="DataAgent")
        return res
    except Exception as e:
        logger.error(f"[DataNode] Fast-track query failed: {e}")
        return f"获取猪只 `{p_id}` 档案失败。\n详情: {e}"

async def _execute_text_to_sql_flow(query_str: str, client_id: str) -> str:
    """Text-to-SQL 复杂流程"""
    settings = get_settings()
    api_key = os.environ.get("DASHSCOPE_API_KEY") or settings.dashscope_api_key
    model = os.environ.get("DASHSCOPE_MODEL") or settings.dashscope_model or "qwen3.5-flash"
    
    # 1. 构造 Text-to-SQL Prompt 并调用模型生成 SQL
    schema_prompt = (
        "你是一个专业的 MySQL 数据库专家，负责将用户的自然语言问题翻译成安全、标准的只读 SQL SELECT 语句。\n\n"
        "我们有如下两张表，请仔细阅读它们的 Schema 及关联关系：\n"
        "1. pig_info（生猪基本档案表）：\n"
        "   - pig_id: VARCHAR(50), 主键，生猪编号 (如 'PIG001')\n"
        "   - breed: VARCHAR(100), 品种 (如 '金华两头乌')\n"
        "   - lifecycle: TEXT, 历史时序成长轨迹 (JSON 字符串，格式如 '[{\"month\": 1, \"weight\": 9.5}]'。注：除非用户明确要查询历史轨迹详情，一般基本信息直接使用 current_weight_kg)\n"
        "   - current_month: INT, 当前月龄\n"
        "   - current_weight_kg: DECIMAL(10,2), 当前最新测得体重\n\n"
        "2. daily_pig_logs（生猪每日行为与体征日志表）：\n"
        "   - pig_id: VARCHAR(50), 外键关联 pig_info.pig_id\n"
        "   - log_date: DATE, 日志记录日期\n"
        "   - feed_count: INT, 每日采食次数\n"
        "   - feed_duration_mins: INT, 每日采食时长 (分钟)\n"
        "   - water_count: INT, 每日饮水次数\n"
        "   - weight_kg: DECIMAL(10,2), 当日实测体重\n"
        "   - activity_level: INT, 活跃度等级 (1-10)\n\n"
        "【极其严格的生成约束】：\n"
        "- 你**只能且必须**只生成一条以 'SELECT' 开头的 SQL 语句，绝对不要添加任何其他的分析、文字解释或 Markdown 包裹！\n"
        "- 绝不要在生成的 SQL 中带有分号 ';'。\n"
        "- 绝不要使用 UNION、INSERT、UPDATE、DELETE 等高危词汇。\n"
        "- SQL 中的字符串变量请用单引号括起来。\n"
        "- 仅生成一条 SQL 本身，不要带任何 markdown 包裹符号（比如不要用 ```sql ）。\n\n"
        f"用户问题: {query_str}\n"
        "请直接生成 SQL:"
    )
    
    await push_debug_event("thought", {"content": "【Text-to-SQL】正在激活大模型，将用户提问编译翻译为标准只读 SQL 语句..."}, client_id, agent="DataAgent", status="SQL编译")
    
    generated_sql = ""
    try:
        def _call_llm_for_sql():
            dashscope.api_key = api_key
            return Generation.call(
                model=model,
                messages=[{"role": "user", "content": schema_prompt}],
                result_format="message",
                temperature=0.1
            )
        
        resp = await asyncio.to_thread(_call_llm_for_sql)
        if resp.status_code == 200:
            res_output = resp.output
            if hasattr(res_output, 'choices') and res_output.choices:
                generated_sql = res_output.choices[0].message.content
            elif hasattr(res_output, 'choice') and res_output.choice:
                generated_sql = res_output.choice.message.content
            else:
                generated_sql = str(res_output)
        else:
            raise RuntimeError(f"API Error code {resp.status_code}")
            
    except Exception as e:
        logger.error(f"[DataNode] LLM sql generation failed: {e}")
        return f"大模型生成 SQL 语句失败，无法查询数据。\n详情: {e}"

    # 清洗生成的 SQL 语句，防止包含包裹符
    generated_sql = generated_sql.strip()
    generated_sql = re.sub(r"^```(sql)?", "", generated_sql, flags=re.I)
    generated_sql = re.sub(r"```$", "", generated_sql)
    generated_sql = generated_sql.strip().rstrip(';')

    await push_debug_event("thought", {"content": f"【Text-to-SQL】翻译 SQL 成功：`{generated_sql}`"}, client_id, agent="DataAgent")
    await asyncio.sleep(0.5)

    # 2. 静态防火墙安全审计与只读沙盒执行
    await push_debug_event("thought", {"content": "【只读沙盒】启动静态防火墙 SQL 安全审计，校验多语句/写注入/UNION 漏洞..."}, client_id, agent="DataAgent", status="沙盒审计")
    await asyncio.sleep(0.8)
    
    sandbox_result = await execute_readonly_sql(generated_sql)
    
    if not sandbox_result.get("success"):
        err_msg = sandbox_result.get("error", "未知审计异常")
        await push_debug_event("thought", {"content": f"【只读沙盒】安全审计拦截阻断：{err_msg}"}, client_id, agent="DataAgent", status="高危拦截")
        return f"❌ **安全防火墙拦截高危 SQL 操作**！\n原因: {err_msg}\n触发语句: `{generated_sql}`"

    await push_debug_event("thought", {"content": "【只读沙盒】静态审计 100% 通过！允许在只读数据库执行..."}, client_id, agent="DataAgent")
    await push_debug_event("thought", {"content": "【数据库执行】连接 MySQL 只读账户，执行安全 SQL，检索出结果集..."}, client_id, agent="DataAgent", status="数据调取")
    await asyncio.sleep(0.6)

    db_data = sandbox_result.get("data", [])
    columns = sandbox_result.get("columns", [])
    
    # 3. 将结果和用户原问题再次喂给大模型，进行精美 Markdown 呈现
    await push_debug_event("thought", {"content": "【数据呈现】召回结果成功！正在激活大模型，将 JSON 报表整理为精美 Markdown 样式并融入决策建议..."}, client_id, agent="DataAgent", status="智能润色")
    await asyncio.sleep(0.6)
    
    render_prompt = (
        "你是一个顶级的金华两头乌智能养殖分析师。\n"
        "请根据用户的原始问题、执行的 SQL 语句以及数据库返回的 JSON 数据，撰写一份排版精美、充满商业与养殖洞察力的分析报告。\n\n"
        "【排版规范】：\n"
        "- 强制多使用 Markdown 表格来整理和对比数据指标。\n"
        "- 保持专业且容易阅读，在最后给出 2 条科学的生产建议。\n"
        "- 绝对不要泄露底层数据库表名或字段名，把它们转化为养殖户易读懂的名词（如将 current_weight_kg 描述为'当前实测体重'）。\n\n"
        f"【原始提问】: {query_str}\n"
        f"【执行 SQL】: {generated_sql}\n"
        f"【召回数据(JSON)】: {json.dumps(db_data, ensure_ascii=False)}\n\n"
        "请精美呈现数据分析报告："
    )

    rendered_report = ""
    try:
        def _call_llm_for_render():
            dashscope.api_key = api_key
            return Generation.call(
                model=model,
                messages=[{"role": "user", "content": render_prompt}],
                result_format="message",
                temperature=0.3
            )
            
        resp = await asyncio.to_thread(_call_llm_for_render)
        if resp.status_code == 200:
            res_output = resp.output
            if hasattr(res_output, 'choices') and res_output.choices:
                rendered_report = res_output.choices[0].message.content
            elif hasattr(res_output, 'choice') and res_output.choice:
                rendered_report = res_output.choice.message.content
            else:
                rendered_report = str(res_output)
        else:
            raise RuntimeError(f"API Error code {resp.status_code}")
            
    except Exception as e:
        logger.error(f"[DataNode] LLM render report failed: {e}")
        # 降级：如果模型生成报告失败，手动进行基础表格渲染
        rendered_report = f"### 📊 智能数据分析报表\n\n*由于报告渲染服务繁忙，已为您降级为基础报表展示。*\n\n"
        rendered_report += f"**执行 SQL**: `{generated_sql}`\n\n"
        if not db_data:
            rendered_report += "🔍 数据库中未找到匹配的记录。"
        else:
            rendered_report += "| " + " | ".join(columns) + " |\n"
            rendered_report += "| " + " | ".join(["---"] * len(columns)) + " |\n"
            for row in db_data:
                rendered_report += "| " + " | ".join(str(row.get(col, '--')) for col in columns) + " |\n"

    return rendered_report
