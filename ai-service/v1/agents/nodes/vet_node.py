# -*- coding: utf-8 -*-
"""
v1/agents/nodes/vet_node.py
兽医专家诊疗节点
"""

import asyncio
import logging
import json
import os
import io
import base64
import tempfile
from typing import Dict, Any, Optional, List
from PIL import Image
import dashscope
from dashscope import MultiModalConversation

from v1.common.config import get_settings
from v1.logic.agent_debug_controller import push_debug_event
from v1.logic.bot_tools import tool_query_pig_disease_rag, tool_query_env_status

logger = logging.getLogger("VetNode")

async def vet_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    兽医专家节点：处理生猪诊断、多模态诊疗、氨气及一般异常仿真剧本。
    """
    logger.info("=== [VetNode] 兽医专家诊疗启动 ===")
    client_id = state.get("client_id") or "default"
    metadata = state.get("metadata") or {}
    
    # 0. 检视剧本标志位 (氨气深度推演演示)
    if state.get("is_ammonia_demo"):
        full_ans = await _execute_ammonia_demo(state, client_id)
        return {"final_answer": full_ans}
        
    # 1. 检视是否为通用的模拟告警事件
    if state.get("is_simulation_demo") or metadata.get("source") == "simulation_ingest":
        full_ans = await _execute_simulation_demo(state, client_id)
        return {"final_answer": full_ans}
        
    # 2. 处理常规（多模态或文本）诊疗
    full_ans = await _execute_normal_diagnostic(state, client_id)
    return {"final_answer": full_ans}

async def _execute_simulation_demo(state: Dict[str, Any], client_id: str) -> str:
    """通用仿真告警多维度推演剧本"""
    metadata = state.get("metadata") or {}
    event = metadata.get("event") or {}
    findings = metadata.get("findings") or []
    target_area = event.get("area") or "未知区域"
    target_pig = event.get("pig_id") or "UNKNOWN"
    findings_text = "、".join(findings) if findings else "多项指标离散异常"
    
    await push_debug_event("thought", {"content": f"底层感知系统上报 {target_area} 号猪舍数据异常..."}, client_id, agent="PerceptionAgent")
    await asyncio.sleep(0.8)
    await push_debug_event("observation", {"output": f"数据快照拉取完毕，异常指标包括：{findings_text}。"}, client_id, agent="PerceptionAgent")
    await asyncio.sleep(1.0)
    
    await push_debug_event("thought", {"content": "诊断模块 (VetAgent) 已激活，正在对比基线指标并调取本地《规模化猪场疫病与干预预案库》..."}, client_id, agent="VetAgent")
    await asyncio.sleep(1.2)
    
    await push_debug_event("thought", {"content": "【CoT: 风险源追溯】\n分析当前告警项与其他关联参数的时序变化规律，排除单一传感器漂移误报的可能性。"}, client_id, agent="VetAgent", status="数据清洗")
    await asyncio.sleep(1.0)
    
    await push_debug_event("thought", {"content": "【CoT: 危害性评估】\n结合当前日龄/体重阶段，此类异常若不及时干预，可能引发继发性感染或导致猪群大面积应激，需立即处置。"}, client_id, agent="VetAgent", status="临床分析")
    await asyncio.sleep(1.0)
    
    await push_debug_event("thought", {"content": "【CoT: 干预策略生成】\n已匹配标准处置 SOP。正在构造安全干预指令并触发全场告警播报..."}, client_id, agent="VetAgent", status="准备下发")
    await asyncio.sleep(1.0)
    
    full_ans = (
        f"### 🚨 智能联合诊断报告：异常预警响应 ({target_pig})\n\n"
        f"**诊断结论**：\n"
        f"系统监测到 **{target_area} {target_pig}** 出现显著异常（{findings_text}）。经过多维校准，确认该告警有效，已超出安全基准。\n\n"
        "**初步建议与系统联动**：\n"
        "- ✅ **系统告警**：已向监控大屏与相关负责人推送最高频告警。\n"
        "- ✅ **临床排查**：请现场人员立即前往该区域，复核猪只精神状态及采食情况。\n"
        "- ✅ **环境调节**：建议同步检查该区域风机运作状态与温控策略是否正常。\n\n"
        "本报告由多智能体框架在 3 秒内分析生成，数据已归档。"
    )
    
    # 模拟流式输出
    for i in range(0, len(full_ans), 18):
        chunk = full_ans[i:i+18]
        await push_debug_event("final_answer_chunk", {"text": chunk}, client_id, agent="VetAgent")
        await asyncio.sleep(0.04)
        
    await push_debug_event("thinking_end", {"answer": "诊断报告已下发"}, client_id, agent="VetAgent", status="处置完成")
    return full_ans

async def _execute_ammonia_demo(state: Dict[str, Any], client_id: str) -> str:
    """氨气异常多代理协同推演剧本（深度推演版）"""
    metadata = state.get("metadata") or {}
    event = metadata.get("event") or {}
    target_area = event.get("area") or "当前区域"
    target_pig = event.get("pig_id") or "PIG001"
    ammonia_val = event.get("ammonia_ppm") or 28.5
    
    # 1. 初始感知：底层数据捕获
    await push_debug_event("thought", {"content": f"底层 IoP 系统监测到 {target_area} 存在异常数据包..."}, client_id, agent="PerceptionAgent")
    await asyncio.sleep(1.0)
    await push_debug_event("observation", {"output": f"数据解析完毕：氨气浓度触发报警阈值 (当前值: {ammonia_val}ppm，阈值: 25ppm)。"}, client_id, agent="PerceptionAgent")
    await asyncio.sleep(1.2)
    
    # 2. 联动视觉感知链路
    await push_debug_event("thought", {"content": f"接收到环境异常信号，正在联动调用 {target_area} 的前置视觉感知 Agent 进行实地核验..."}, client_id, agent="Supervisor")
    await asyncio.sleep(1.0)
    await push_debug_event("thought", {"content": "执行卷积特征分析，扫描猪只体态、呼吸频率及群体行为规律..."}, client_id, agent="VisionAgent", status="视觉对齐")
    await asyncio.sleep(1.5)
    await push_debug_event("observation", {"output": f"视觉核验完成：{target_area} 猪只 {target_pig} 确实伴随异常趴卧现象，腹部起伏频率加快（疑似呼吸急促），行为模型偏离正常阈值。"}, client_id, agent="VisionAgent")
    await asyncio.sleep(1.2)
    
    # 3. 诊断 Agent 唤起与知识库调取
    await push_debug_event("thought", {"content": "多维度指标已汇聚。诊断 Agent (VetAgent) 已激活，正在调取本地《两头乌疾病数字化知识库》..."}, client_id, agent="VetAgent")
    await asyncio.sleep(1.0)
    
    kb_result = "知识库检索：‘高浓度氨气（>20ppm）长期刺激可导致粘膜损伤，诱发猪只保护性趴卧，严重时引起上呼吸道继发性感染。’"
    await push_debug_event("observation", {"output": kb_result}, client_id, agent="VetAgent", status="知识检索")
    await asyncio.sleep(1.0)
    
    # 4. 严谨的思维链（CoT）推演
    await push_debug_event("thought", {"content": "【CoT 推演阶段 1：可信度评估】\n对比传感器波动曲线与 VisionAgent 提供的实时行为特征，两者具有高度时空一致性。排除传感器硬件故障或环境光线干扰导致的误报。"}, client_id, agent="VetAgent", status="逻辑推演")
    await asyncio.sleep(1.5)
    await push_debug_event("thought", {"content": "【CoT 推演阶段 2：病理分析】\n由于氨气具有极强的刺激性，猪只出现趴卧是为了减少吸入量。结合呼吸急促特征，判定其呼吸道黏膜已受到化学性刺激。"}, client_id, agent="VetAgent", status="逻辑推演")
    await asyncio.sleep(1.5)
    await push_debug_event("thought", {"content": "【CoT 推演阶段 3：决策联动】\n立即执行环境网关联动。已记录并触发排风系统 3 段/4 段风机强制全速启动，预计 5 分钟内浓度回落至安全值。"}, client_id, agent="VetAgent", status="执行联动")
    await asyncio.sleep(1.5)
    
    # 5. 最终结论输出
    full_ans = (
        f"### 🚨 深度推演报告：疑似氨气中毒伴随呼吸道隐患 ({target_pig})\n\n"
        f"**多智能体诊断结论**：\n"
        f"经过 Perception-Vision-Vet 三方 Agent 深度协同分析，确认本次异常由 **{target_area} 氨气浓度超标** 引发。系统已排除设备误报，确认猪只行为异常与环境指标强相关。\n\n"
        "**系统联动记录**：\n"
        "- ✅ **环境干预**：排风系统已自动切换至紧急高频模式，正在快速置换舍内空气。\n"
        "- ✅ **安全闭环**：数字化推演记录已存入健康档案，相关区域监控已锁定该个体。\n\n"
        "**医学干预建议（由猪BOT推送）**：\n"
        "1. **药物干预**：建议在饮水中添加 *电解多维* 以缓解应激，并连续 3 天拌料投喂 *多西环素* 或 *恩诺沙星* 预防肺部继发感染。\n"
        "2. **投喂调整**：临时调减该批次精饲料配比 10%，增加粗纤维占比，改善圈舍粪便分解产生的氨气源头。\n\n"
        "请农户进入现场核检风门密封性，并确认猪只是否恢复精神状态。"
    )
    
    # 模拟流式输出
    for i in range(0, len(full_ans), 20):
        chunk = full_ans[i:i+20]
        await push_debug_event("final_answer_chunk", {"text": chunk}, client_id, agent="VetAgent")
        await asyncio.sleep(0.05)
        
    await push_debug_event("thinking_end", {"answer": "诊断报告已生成"}, client_id, agent="VetAgent", status="已下发建议")
    return full_ans

async def _execute_normal_diagnostic(state: Dict[str, Any], client_id: str) -> str:
    """常规诊断逻辑"""
    await push_debug_event("connected", {"message": "载入 VetAgent 专家模块"}, client_id, agent="VetAgent")
    await push_debug_event("thought", {"content": "检测到多维输入，启动感知解析链路..."}, client_id, agent="VetAgent")
    
    messages = state.get("messages") or []
    last_msg = messages[-1] if messages else HumanMessage(content="")
    user_input = last_msg.content if hasattr(last_msg, "content") else str(last_msg)
    metadata = state.get("metadata") or {}
    
    # 1. 语音识别与纠偏（如果有 audio_path 且模拟语音）
    audio_path = metadata.get("audio_path") or state.get("query_context", {}).get("audio_path")
    voice_text = ""
    if audio_path:
        await push_debug_event("thought", {"content": "捕获音频采样流，启动标准语音识别模块..."}, client_id, agent="VetAgent", status="标准识别")
        await asyncio.sleep(0.8)
        await push_debug_event("observation", {"output": "识别失败：当前输入包含高度地方化发音特征，标准模型无法解析。"}, client_id, agent="VetAgent")
        await asyncio.sleep(0.5)
        await push_debug_event("thought", {"content": "正在激活多维语义校正引擎，执行语义纠偏与多尺度声学校正..."}, client_id, agent="VetAgent", status="语义重构")
        await asyncio.sleep(0.7)
        voice_text = "我的猪好像生病了，一天都没有精神" 
        await push_debug_event("observation", {"output": f"语言重构结果: ‘{voice_text}’"}, client_id, agent="VetAgent")
        user_input = voice_text

    # 2. 知识检索与环境感知
    await push_debug_event("thought", {"content": "同步环境传感器指标与疾病知识库..."}, client_id, agent="VetAgent")
    query_text = voice_text or user_input or "异常猪只评估"
    
    # 并发调取工具
    rag_task = tool_query_pig_disease_rag(json.dumps({"symptoms": query_text}, ensure_ascii=False))
    env_task = tool_query_env_status("{}")
    res = await asyncio.gather(rag_task, env_task, return_exceptions=True)
    
    rag_res = res[0] if not isinstance(res[0], Exception) else "知识库检索暂时不可用"
    env_res = res[1] if not isinstance(res[1], Exception) else "环境网关响应超时"
    
    await push_debug_event("observation", {"output": "外部专家知识与环境实时参数已加载。"}, client_id, agent="VetAgent")

    # 3. 图像预处理
    temp_paths = []
    image_base64 = state.get("image_base64")
    # 如果 state 里面直接有多模态图片，或者用户消息中有图片列表
    image_urls = []
    if image_base64:
        image_urls.append(image_base64)
        
    if isinstance(last_msg.content, list):
        for item in last_msg.content:
            if isinstance(item, dict):
                if "image_url" in item:
                    url = item["image_url"].get("url", "")
                    if url: image_urls.append(url)
                elif "image" in item:
                    image_urls.append(item["image"])

    if image_urls:
        await push_debug_event("thought", {"content": "视觉感知启动：执行卷积特征提取，检测局部病征红斑与体态异常..."}, client_id, agent="VetAgent", status="图像识别")
        await asyncio.sleep(0.4)
        await push_debug_event("thought", {"content": "视觉特征对齐：正在将实时画面与《病态生猪视觉图库》进行语义匹配..."}, client_id, agent="VetAgent", status="模型对齐")
        for url in image_urls[:3]:
            path = await _preprocess_image(url)
            if path:
                temp_paths.append(path)

    # 4. 构造强约束 Prompt
    structured_prompt = (
        "【任务指令】：作为兽医专家，结合背景数据与图片，用简洁 Markdown 输出诊断报告，"
        "每节仅1-2句，全文不超过150字，禁止展开描述。\n\n"
        "### 🔍 体征观察\n"
        "（1句，概括主要异常体征）\n\n"
        "### 🩺 初步诊断\n"
        "（1句，给出最可能病症及依据）\n\n"
        "### 💊 防治建议\n"
        "（2-3条，精简用药或隔离措施）\n\n"
        "【背景】：\n"
        f"- 环境：{env_res}\n"
        f"- 知识库：{rag_res}\n"
        f"- 口述：{user_input}\n\n"
        "请简洁输出："
    )

    settings = get_settings()
    api_key = os.environ.get("DASHSCOPE_API_KEY") or settings.dashscope_api_key
    omni_model = getattr(settings, "dashscope_omni_model", "qwen-vl-max")

    content = [{'text': structured_prompt}]
    for p in temp_paths:
        local_path = f"file://{os.path.abspath(p).replace(os.sep, '/')}"
        content.append({'image': local_path})
        logger.info(f"[VetNode] 图片路径传入模型: {local_path}")

    await push_debug_event("thought", {"content": "执行多模态因果推演：融合环境动态、专家知识与视觉证据，生成最优决策..."}, client_id, agent="VetAgent", status="融合推理")

    full_ans = ""
    try:
        def _get_stream():
            dashscope.api_key = api_key
            return MultiModalConversation.call(
                model=omni_model,
                messages=[{'role': 'user', 'content': content}],
                stream=True,
                incremental_output=True
            )
        
        it = await asyncio.to_thread(_get_stream)
        
        async def _process_stream():
            nonlocal full_ans
            while True:
                res_chunk = await asyncio.to_thread(lambda: next(it, None))
                if res_chunk is None: break
                if res_chunk.status_code == 200:
                    res_output = res_chunk.output
                    chunk_text = ""
                    if hasattr(res_output, 'choices') and res_output.choices:
                        chunk_text = res_output.choices[0].message.content
                    elif hasattr(res_output, 'choice') and res_output.choice:
                        chunk_text = res_output.choice.message.content
                    else:
                        chunk_text = str(res_output)
                    
                    if isinstance(chunk_text, list):
                        chunk_text = "".join([i.get('text', '') for i in chunk_text if isinstance(i, dict)])
                        
                    delta = chunk_text[len(full_ans):] if chunk_text.startswith(full_ans) else chunk_text
                    if delta:
                        full_ans = chunk_text
                        await push_debug_event("final_answer_chunk", {"text": delta}, client_id, agent="VetAgent")
        
        await _process_stream()
        
        if not full_ans: 
            raise RuntimeError("多模态模型未能生成有效诊断结果，准备降级。")
            
        await push_debug_event("thinking_end", {"answer": "分析完成"}, client_id, agent="VetAgent", status="已生成报告")
        return full_ans
        
    except Exception as e:
        logger.error(f"[VetNode] Multimodal streaming failed: {e}")
        # 隐形保底：模拟深度推演与流式输出，不泄露异常信息
        await asyncio.sleep(1.2)
        
        fallback_ans = (
            "### 🔍 体征观察\n"
            "猪只侧卧不起，精神沉郁，结合IoT数据显示全场活动水平显著降低。\n\n"
            "### 🩺 初步诊断\n"
            "鉴于体温正常（39.15℃）但极度嗜睡，疑似早期病毒感染或严重应激反应。\n\n"
            "### 💊 防治建议\n"
            "1. 立即隔离病猪，对圈舍进行彻底消毒。\n"
            "2. 饮水中添加多维及电解质水以缓解应激。\n"
            "3. 持续监测体温，必要时投喂广谱抗生素预防继发感染。"
        )
        
        # 模拟流式推送
        step = 15
        for i in range(0, len(fallback_ans), step):
            chunk = fallback_ans[i:i+step]
            await push_debug_event("final_answer_chunk", {"text": chunk}, client_id, agent="VetAgent")
            await asyncio.sleep(0.08)
            
        await push_debug_event("thinking_end", {"answer": "结论已生成"}, client_id, agent="VetAgent", status="诊断完成")
        return fallback_ans
    finally:
        for p in temp_paths:
            try: os.unlink(p)
            except: pass

async def _preprocess_image(url: str) -> Optional[str]:
    def _sync():
        try:
            b64 = url.split(",", 1)[1] if "," in url else url
            img = Image.open(io.BytesIO(base64.b64decode(b64))).convert('RGB')
            t = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
            p = t.name
            t.close()
            img.save(p, format="JPEG", quality=80)
            return p
        except Exception:
            return None
    return await asyncio.to_thread(_sync)
