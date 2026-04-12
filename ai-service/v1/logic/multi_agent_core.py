# -*- coding: utf-8 -*-
"""
多智能体系统（MAS）核心模块

实现了基于 Supervisor-Worker 架构的协作推理框架。
系统通过意图路由（Supervisor）识别用户需求，并将任务分发至特定领域的专家智能体（Worker）。
Worker 采用 ReAct（Reasoning and Acting）模式进行多步决策，利用专业工具集完成任务并汇总响应。

系统核心组件：
1. SupervisorAgent: 负责意图识别与任务路由。
2. WorkerAgent: 各领域专家智能体的抽象基类。
3. VetAgent: 畜牧兽医专家，支持多模态（视觉）诊断。
4. DataAgent: 数据分析专家，负责生产数据查询与增重预测。
5. PerceptionAgent: 视觉感知专家，负责监控视频流分析。
6. GrowthCurveAgent: 生长曲线专题专家。
7. BriefingAgent: 每日养殖简报生成专家。
8. MultiAgentOrchestrator: 系统总协调器，管理上下文流程及智能体集群。
"""
from __future__ import annotations

import asyncio
import base64
import io
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Any
from PIL import Image

from v1.common.config import get_settings

logger = logging.getLogger("multi_agent")

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    HAS_RICH = True
    console = Console()
except Exception:
    HAS_RICH = False
    console = None

from v1.common.langchain_compat import (
    HAS_LANGCHAIN,
    AgentExecutor,
    BaseCallbackHandler,
    create_react_agent,
    LCTool,
    PromptTemplate,
    ChatOpenAI
)

try:
    from openai import OpenAI
    HAS_OPENAI = True
except Exception:
    HAS_OPENAI = False

import dashscope
from dashscope import Generation, AioGeneration

try:
    from v1.common.langchain_compat import (
        BaseChatModel,
        AIMessage,
        HumanMessage,
        SystemMessage,
        ChatResult,
        ChatGeneration,
        AIMessageChunk,
        ChatGenerationChunk
    )
    from pydantic import Field
    from dashscope import MultiModalConversation

    def _is_multimodal_model(model_name: str) -> bool:
        """判断是否为多模态/Omni 模型，需使用 MultiModalConversation 接口"""
        if not model_name: return False
        m = model_name.lower()
        # 识别 qwen-vl, qwen-audio, qwen3.6 以及特殊的 omni 模型
        keywords = ["qwen-vl", "qwen-audio", "qwen3.6", "omni", "multimodal"]
        return any(k in m for k in keywords)

    class DashScopeNativeChat(BaseChatModel):
        """
        DashScope 原生驱动包装类。
        直接调用官方 SDK 以绕过 OpenAI 兼容层的额度策略限制。
        """
        model_name: str
        api_key: str
        temperature: float = 0.1
        max_tokens: int = 2000
        streaming: bool = False

        def __init__(self, **kwargs):
            # 兼容 Pydantic v1/v2 的简单构建方式
            if "model" in kwargs: kwargs["model_name"] = kwargs.pop("model")
            super().__init__(**kwargs)

        def _format_messages(self, messages, is_mm: bool):
            formatted_messages = []
            for m in messages:
                if is_mm:
                    if isinstance(m, SystemMessage):
                        formatted_messages.append({'role': 'system', 'content': [{'text': m.content}]})
                    elif isinstance(m, HumanMessage):
                        if isinstance(m.content, list):
                            formatted_messages.append({'role': 'user', 'content': m.content})
                        else:
                            formatted_messages.append({'role': 'user', 'content': [{'text': m.content}]})
                    elif isinstance(m, AIMessage):
                        formatted_messages.append({'role': 'assistant', 'content': [{'text': m.content}]})
                    else:
                        formatted_messages.append({'role': 'user', 'content': [{'text': str(m.content)}]})
                else:
                    if isinstance(m, SystemMessage):
                        formatted_messages.append({'role': 'system', 'content': m.content})
                    elif isinstance(m, HumanMessage):
                        formatted_messages.append({'role': 'user', 'content': m.content})
                    elif isinstance(m, AIMessage):
                        formatted_messages.append({'role': 'assistant', 'content': m.content})
                    else:
                        formatted_messages.append({'role': 'user', 'content': str(m.content)})
            return formatted_messages

        def _extract_text_content(self, response) -> str:
            res_output = response.output
            if hasattr(res_output, 'choices') and res_output.choices:
                content = res_output.choices[0].message.content
            elif hasattr(res_output, 'choice') and res_output.choice:
                content = res_output.choice.message.content
            else:
                content = str(res_output)

            if isinstance(content, list):
                text_parts = []
                for item in content:
                    if isinstance(item, dict) and 'text' in item:
                        text_parts.append(item['text'])
                    else:
                        text_parts.append(str(item))
                return "".join(text_parts).strip()
            return str(content).strip()

        async def _call_non_streaming(self, formatted_messages, is_mm: bool):
            def _call():
                if is_mm:
                    mm_messages = []
                    for m in formatted_messages:
                        mm_messages.append({
                            'role': m['role'],
                            'content': [{'text': m['content']}] if isinstance(m['content'], str) else m['content']
                        })
                    return MultiModalConversation.call(
                        model=self.model_name,
                        messages=mm_messages,
                        api_key=self.api_key,
                        temperature=self.temperature,
                        max_tokens=self.max_tokens,
                    )
                return Generation.call(
                    model=self.model_name,
                    messages=formatted_messages,
                    api_key=self.api_key,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    result_format='message'
                )

            logger.info(f"DashScope Native Call Starting: model={self.model_name}, is_mm={is_mm}")
            response = await asyncio.to_thread(_call)
            logger.info(f"DashScope Native Call Finished: status_code={response.status_code}, request_id={response.request_id}")

            if response.status_code != 200:
                err_msg = f"DashScope Native Error: code={response.code}, message={response.message}, request_id={response.request_id}"
                logger.error(err_msg)
                raise Exception(err_msg)

            content = self._extract_text_content(response)
            if not content:
                raise ValueError("DashScope non-stream response returned empty content")
            return content

        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            # 内部调用 _agenerate 的同步 wrapper
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import threading
                    # 如果在 event loop 中调用同步方法，这通常是个问题，但 LangChain 有时会这样做
                    # 这里我们保持同步，但记录警告
                    logger.warning("DashScopeNativeChat._generate called within a running event loop")
            except Exception:
                pass
            
            return asyncio.run(self._agenerate(messages, stop, run_manager, **kwargs))

        async def _astream(self, messages, stop=None, run_manager=None, **kwargs):
            is_mm = _is_multimodal_model(self.model_name)
            
            formatted_messages = self._format_messages(messages, is_mm)

            logger.info(f"DashScope Native Stream Call Starting: model={self.model_name}, is_mm={is_mm}")
            
            async def _make_async_gen():
                if is_mm:
                    # 多模态 SDK 目前仅支持同步流式，我们封装在线程中
                    def sync_gen():
                        return MultiModalConversation.call(
                            model=self.model_name,
                            messages=formatted_messages,
                            api_key=self.api_key,
                            temperature=self.temperature,
                            max_tokens=self.max_tokens,
                            stream=True,
                            incremental_output=True
                        )
                    
                    it = await asyncio.to_thread(sync_gen)
                    def _safe_next(iterator):
                        try:
                            return next(iterator)
                        except StopIteration:
                            return None
                    
                    while True:
                        res = await asyncio.to_thread(_safe_next, it)
                        if res is None:
                            break
                        yield res
                else:
                    # 纯文本可以使用官方 AioGeneration
                    responses = await AioGeneration.call(
                        model=self.model_name,
                        messages=formatted_messages,
                        api_key=self.api_key,
                        temperature=self.temperature,
                        max_tokens=self.max_tokens,
                        result_format='message',
                        stream=True,
                        incremental_output=True
                    )
                    async for r in responses:
                        yield r

            full_text_so_far = ""
            saw_success_chunk = False
            async for response in _make_async_gen():
                if response.status_code != 200:
                    logger.error(f"DashScope Stream Error: {response.message}")
                    continue
                saw_success_chunk = True
                
                # 获取当前时刻的全量/增量回复
                res_output = response.output
                current_full_text = ""
                
                # 解析内容 (多模态 vs 纯文本)
                content = ""
                if hasattr(res_output, 'choices') and res_output.choices:
                    content = res_output.choices[0].message.content
                elif hasattr(res_output, 'choice') and res_output.choice:
                    content = res_output.choice.message.content
                
                # 如果是多模态，Content 可能是列表: [{'text': '...'}, ...]
                if isinstance(content, list):
                    text_parts = []
                    for item in content:
                        if isinstance(item, dict) and 'text' in item:
                            text_parts.append(item['text'])
                    current_full_text = "".join(text_parts)
                else:
                    current_full_text = str(content)
                
                if current_full_text:
                    # 💡 手动增量计算逻辑（对多模态和文本模型均有效）
                    if current_full_text.startswith(full_text_so_far):
                        delta_text = current_full_text[len(full_text_so_far):]
                    else:
                        delta_text = current_full_text
                        
                    if delta_text:
                        if run_manager:
                            # 💡 关键：手动触发 LangChain 回调
                            await run_manager.on_llm_new_token(delta_text)
                        
                        # 💡 增强：如果这是一个普通 LLM 调用（非 Agent 内部），尝试直接推送
                        # 注意：在 Agent 执行过程中，RichTraceHandler 会负责此项工作，
                        # 但为了鲁棒性，我们在这里确保 chunk 被生成
                        yield ChatGenerationChunk(message=AIMessageChunk(content=delta_text))
                        full_text_so_far = current_full_text

        async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
            # 如果开启了流式，我们一律通过 _astream 驱动
            if self.streaming:
                is_mm = _is_multimodal_model(self.model_name)
                formatted_messages = self._format_messages(messages, is_mm)
                try:
                    full_content = ""
                    async for chunk in self._astream(messages, stop, run_manager, **kwargs):
                        full_content += chunk.message.content
                    if not full_content.strip():
                        raise ValueError("DashScope stream returned empty content")
                    return ChatResult(generations=[ChatGeneration(message=AIMessage(content=full_content))])
                except Exception as e:
                    logger.warning(
                        "DashScope stream failed, falling back to non-streaming call. model=%s is_mm=%s error=%s",
                        self.model_name,
                        is_mm,
                        e,
                    )
                    fallback_content = await self._call_non_streaming(formatted_messages, is_mm)
                    if run_manager:
                        await run_manager.on_llm_new_token(fallback_content)
                    return ChatResult(generations=[ChatGeneration(message=AIMessage(content=fallback_content))])

            # 非流式路径
            formatted_messages = []
            # ... (后面是非流式原有逻辑)

            is_mm = _is_multimodal_model(self.model_name)
            
            def _call():
                if is_mm:
                    # 对于多模态模型，使用 MultiModalConversation 接口，且 content 必须是列表
                    mm_messages = []
                    for m in formatted_messages:
                        mm_messages.append({
                            'role': m['role'],
                            'content': [{'text': m['content']}] if isinstance(m['content'], str) else m['content']
                        })
                    return MultiModalConversation.call(
                        model=self.model_name,
                        messages=mm_messages,
                        api_key=self.api_key,
                        temperature=self.temperature,
                        max_tokens=self.max_tokens,
                    )
                else:
                    return Generation.call(
                        model=self.model_name,
                        messages=formatted_messages,
                        api_key=self.api_key,
                        temperature=self.temperature,
                        max_tokens=self.max_tokens,
                        result_format='message'
                    )

            logger.info(f"DashScope Native Call Starting: model={self.model_name}")
            response = await asyncio.to_thread(_call)
            logger.info(f"DashScope Native Call Finished: status_code={response.status_code}, request_id={response.request_id}")

            if response.status_code != 200:
                err_msg = f"DashScope Native Error: code={response.code}, message={response.message}, request_id={response.request_id}"
                logger.error(err_msg)
                raise Exception(err_msg)

            # 兼容不同结构的返回
            res_output = response.output
            if hasattr(res_output, 'choices') and res_output.choices:
                content = res_output.choices[0].message.content
            elif hasattr(res_output, 'choice') and res_output.choice:
                content = res_output.choice.message.content
            else:
                content = str(res_output)

            # 如果 content 是列表（多模态模型返回），则提取其中的文本部分
            if isinstance(content, list):
                text_parts = []
                for item in content:
                    if isinstance(item, dict) and 'text' in item:
                        text_parts.append(item['text'])
                    else:
                        text_parts.append(str(item))
                content = "".join(text_parts).strip()

            # 💡 补丁：部分模型在输出 Action 时喜欢在 Thought 后面不换行，手动通过正则对齐
            # 这种“热修”在 LangChain Parser 之前进行，提高稳健性
            if "Thought:" in content and "Action:" in content:
                content = re.sub(r"(Thought:.*?)(Action:)", r"\1\n\2", content, flags=re.DOTALL)
            
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content=content))])

        @property
        def _llm_type(self) -> str:
            return "dashscope_native"

except Exception as e:
    logger.warning(f"Failed to initialize DashScopeNativeChat components: {e}")


# ============================================================
# 数据结构定义
# ============================================================

@dataclass
class AgentContext:
    """
    智能体执行上下文。
    封装用户输入、历史记录、元数据及多模态资源 URL。

    Attributes:
        user_id: 用户唯一标识符
        user_input: 当前查询文本内容
        chat_history: 上下文对话历史列表
        metadata: 扩展元数据字典
        client_id: 客户端会话 ID（用于消息推送隔离）
        image_urls: 多模态图片资源 URL 列表
    """
    user_id: str
    user_input: str
    chat_history: list
    metadata: dict
    client_id: str = "default"
    image_urls: Optional[List[str]] = None
    audio_path: Optional[str] = None


@dataclass
class AgentResult:
    """
    智能体执行结果。
    封装专家反馈、执行日志、工具产出及元数据统计。

    Attributes:
        success: 执行是否成功
        answer: 最终响应内容
        worker_name: 负责处理任务的智能体名称
        thoughts: ReAct 推理逻辑记录
        tool_outputs: 各步骤工具调用的原始输出
        error: 异常信息描述
        image: 执行过程中产出的图片（Base64 编码）
        metadata: 包含执行模式、资源消耗等统计数据的字典
    """
    success: bool
    answer: str
    worker_name: Optional[str] = None
    thoughts: List[str] = None
    tool_outputs: List[str] = None
    error: Optional[str] = None
    image: Optional[str] = None
    metadata: Optional[dict] = None
    trace_id: Optional[str] = None

    def __post_init__(self):
        """初始化默认值"""
        if self.thoughts is None:
            self.thoughts = []
        if self.tool_outputs is None:
            self.tool_outputs = []
        if self.metadata is None:
            self.metadata = {}


# ============================================================
# Supervisor Agent - 意图路由
# ============================================================

SUPERVISOR_PROMPT = """你是智能体调度中心。根据用户问题，选择最合适的专家处理。

可用专家：
- vet_agent: 兽医诊断、疾病分析、用药建议、健康评估、症状判断
- data_agent: 猪只档案查询、通用数据统计、猪只列表查询
- growth_curve_agent: 生长曲线报告、体重预测、月龄生长分析（针对单头猪只）
- briefing_agent: 每日简报、全场日报、农场综合状态报告、日常巡检汇总
- perception_agent: 视频监控、图像识别、现场情况、截图分析

规则：
1. 只输出专家名称，不要解释
2. 如果不需要专家（如闲聊、问候），输出 "direct_reply"
3. 一次只选一个专家
4. 优先选择最专业的专家
5. 涉及单只猪生长/体重预测时选 growth_curve_agent；涉及全场综合日报时选 briefing_agent

用户问题：{user_input}

选择专家："""


class SupervisorAgent:
    """
    意图识别与任务分发器。
    通过语义分析判断任务类型并路由至专用专家智能体。
    """
    
    def __init__(self):
        self.api_key, self.base_url, self.model, self.omni_model = self._get_llm_config()
    
    def _get_llm_config(self):
        """获取 LLM 全局配置。"""
        import os
        settings = get_settings()
        api_key = os.environ.get("DASHSCOPE_API_KEY") or settings.dashscope_api_key
        base_url = (
            os.environ.get("DASHSCOPE_BASE_URL")
            or settings.dashscope_base_url
            or "https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        model = os.environ.get("DASHSCOPE_MODEL") or settings.dashscope_model or "qwen-plus"
        omni_model = getattr(settings, "dashscope_omni_model", "qwen-plus")
        return api_key, base_url, model, omni_model
    
    async def route(self, user_input: str, has_image: bool = False, has_audio: bool = False, client_id: str = "default") -> str:
        """
        根据用户输入及附件状态进行意图路由。
        
        Args:
            user_input: 用户原始文本请求
            has_image: 标识是否包含多模态图片资源
            has_audio: 标识是否包含多模态音频资源
        
        Returns:
            str: 目标智能体标识符（若无特定路由则返回 "direct_reply"）
        """
        # 如果包含图片或音频，优先路由到能处理多模态的 VetAgent
        if has_image or has_audio:
            reason = "图片" if has_image else "语音"
            if has_image and has_audio: reason = "图片和语音"
            
            if HAS_RICH and console:
                console.print(Panel(
                    Text(f"检测到{reason}，直接路由到: VetAgent (多模态处理)", style="bold cyan"),
                    title="[bold magenta][Supervisor 决策 (多模态)][/]",
                    border_style="magenta"
                ))
            else:
                logger.info(f"Supervisor 路由: 检测到{reason} -> vet_agent")
            return "vet_agent"
        
        from v1.logic.agent_debug_controller import push_debug_event
        
        # 记录路由开始
        await push_debug_event("thought", {"content": f"正在分析您的指令: {user_input[:50]}..."}, client_id, agent="SupervisorAgent", status="思索中")
        
        if not HAS_OPENAI or not self.api_key:
            # 降级到规则引擎
            worker_name = self._rule_based_route(user_input)
            await push_debug_event("action", {"tool": "RuleEngine", "input": user_input, "thought": "降级到硬编码规则逻辑"}, client_id, agent="Supervisor", status="工作中")
            return worker_name
        
        try:
            prompt = SUPERVISOR_PROMPT.format(user_input=user_input)
            
            logger.info(f"Supervisor 原生异步调度开始: model={self.model}, input={user_input[:20]}...")
            
            is_mm = _is_multimodal_model(self.model)
            
            # 使用 DashScope 原生 SDK 进行调用 (异步化)
            def _call():
                if is_mm:
                    return MultiModalConversation.call(
                        model=self.model,
                        messages=[{"role": "user", "content": [{"text": prompt}]}],
                        api_key=self.api_key,
                        temperature=0.1,
                    )
                else:
                    return Generation.call(
                        model=self.model,
                        messages=[{"role": "user", "content": prompt}],
                        api_key=self.api_key,
                        temperature=0.1,
                        result_format='message'
                    )
            try:
                response = await asyncio.to_thread(_call)
            except Exception as e:
                logger.warning(f"DashScope 原生调用触发网络异常: {e}，尝试使用备用通道...")
                # 尝试使用 LangChain 版 LLM 备用（httpx 通常具有更好的连接兼容性）
                from v1.common.langchain_compat import HAS_LANGCHAIN, ChatOpenAI
                if HAS_LANGCHAIN:
                    llm = ChatOpenAI(api_key=self.api_key, base_url=self.base_url, model=self.model)
                    res_msg = await llm.ainvoke(prompt)
                    worker_name = res_msg.content
                    await push_debug_event("observation", {"output": "主连接中断，已切换至备用安全信道"}, client_id, agent="Supervisor", status="工作中")
                    return worker_name.strip().replace("`","").lower()
                raise e
            
            if response.status_code != 200:
                err_msg = f"Supervisor API Error: code={response.code}, message={response.message}, request_id={response.request_id}"
                logger.error(err_msg)
                raise Exception(err_msg)
            
            # 兼容不同结构的返回
            res_output = response.output
            if hasattr(res_output, 'choices') and res_output.choices:
                worker_name = res_output.choices[0].message.content
            elif hasattr(res_output, 'choice') and res_output.choice:
                worker_name = res_output.choice.message.content
            else:
                worker_name = str(res_output)
            
            # 如果是列表格式，提取文本
            if isinstance(worker_name, list):
                text_parts = []
                for item in worker_name:
                    if isinstance(item, dict) and 'text' in item:
                        text_parts.append(item['text'])
                    else:
                        text_parts.append(str(item))
                worker_name = "".join(text_parts)
            
            worker_name = worker_name.strip().replace("`", "").lower()
            
            # 提取可能的解释（如果 LLM 返回了 Thought）
            await push_debug_event("action", {"tool": "IntentSupervisor", "input": worker_name, "thought": f"分析完毕，决定将任务路由至: {worker_name}"}, client_id, agent="Supervisor", status="决策完成")
            
            # 验证返回值
            valid_workers = ["vet_agent", "data_agent", "perception_agent", "growth_curve_agent", "briefing_agent", "direct_reply"]
            if worker_name not in valid_workers:
                logger.warning(f"Supervisor 返回无效 worker: {worker_name}，降级到规则引擎")
                fallback = self._rule_based_route(user_input)
                await push_debug_event("observation", {"output": f"注意：模型返回了未知节点 {worker_name}，已自动修正为 {fallback}"}, client_id, agent="Supervisor", status="工作中")
                return fallback
            
            if HAS_RICH and console:
                console.print(Panel(
                    Text(f"路由到: {worker_name}", style="bold cyan"),
                    title="[bold magenta][Supervisor 决策][/]",
                    border_style="magenta"
                ))
            else:
                logger.info(f"Supervisor 路由: {user_input[:50]} -> {worker_name}")
            
            return worker_name
            
        except Exception as e:
            logger.error(f"Supervisor 路由失败: {e}，降级到规则引擎")
            fallback = self._rule_based_route(user_input)
            await push_debug_event("error", {"message": f"路由层发生异常: {str(e)}，切换至安全模式"}, client_id, agent="Supervisor")
            return fallback
    
    def _rule_based_route(self, user_input: str) -> str:
        """规则引擎兜底路由逻辑。"""
        text = user_input.lower()

        # 每日简报关键词（优先最高）
        briefing_keywords = [
            "每日简报", "日报", "今日简报", "全场简报", "每日诊断简报",
            "farm_daily_briefing", "daily_briefing", "briefing",
            "全场报告", "场内简报", "日常巡检汇总",
        ]
        if any(k in text for k in briefing_keywords):
            return "BriefingAgent"

        # 生长曲线关键词（单只猪分析）
        growth_curve_keywords = [
            "生长曲线", "生长曲线报告", "growth_curve", "growth curve",
            "体重预测", "月增重", "生长分析", "喂食趋势", "饮水趋势",
            "日增重", "生长预测",
        ]
        if any(k in text for k in growth_curve_keywords):
            return "GrowthCurveAgent"

        # 兽医诊断关键词
        vet_keywords = [
            "病", "诊断", "治疗", "用药", "症状", "拉稀", "咳嗽",
            "发烧", "体温", "不吃", "精神", "健康", "兽医"
        ]
        if any(k in text for k in vet_keywords):
            return "vet_agent"

        # 数据查询关键词
        data_keywords = [
            "查", "档案", "列表", "有哪些", "多少", "轨迹",
            "月龄", "id", "编号"
        ]
        if any(k in text for k in data_keywords):
            return "DataAgent"

        # 视觉识别关键词
        perception_keywords = [
            "图片", "照片", "视频", "监控", "摄像", "现场", "情况",
            "状态", "截图", "识别", "检测", "看看", "看下"
        ]
        if any(k in text for k in perception_keywords):
            return "PerceptionAgent"

        # 默认直接回复
        return "direct_reply"


# ============================================================
# Worker Agent 基类
# ============================================================

class WorkerAgent(ABC):
    """
    专家智能体抽象基类。
    
    定义了领域专家智能体的核心执行逻辑，采用 ReAct 推理模式。
    """
    
    def __init__(self, name: str, system_prompt: str, tools: List[LCTool]):
        self.name = name
        self.system_prompt = system_prompt
        self.tools = tools
        self.api_key, self.base_url, self.model, self.omni_model = self._get_llm_config()
    
    def _get_llm_config(self):
        """获取 LLM 配置"""
        import os
        settings = get_settings()
        api_key = os.environ.get("DASHSCOPE_API_KEY") or settings.dashscope_api_key
        base_url = (
            os.environ.get("DASHSCOPE_BASE_URL")
            or settings.dashscope_base_url
            or "https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        model = os.environ.get("DASHSCOPE_MODEL") or settings.dashscope_model or "qwen-plus"
        omni_model = getattr(settings, "dashscope_omni_model", "qwen-plus")
        return api_key, base_url, model, omni_model
    
    @abstractmethod
    def get_tools(self) -> List[LCTool]:
        """获取该 Worker 可用的工具"""
        pass
    
    async def execute(self, context: AgentContext, max_iterations: int = 4) -> AgentResult:
        """
        执行 ReAct 推理循环：思考 -> 行动 -> 观察 -> 总结。
        
        Args:
            context: 执行上下文信息
            max_iterations: 最大迭代次数，默认为 4
        
        Returns:
            AgentResult: 执行结果封装
        """
        if not HAS_LANGCHAIN:
            return AgentResult(
                success=False,
                answer="系统繁忙，请稍后再试。",
                worker_name=self.name,
                error="LangChain 未安装"
            )
        
        if not self.api_key:
            return AgentResult(
                success=False,
                answer="系统繁忙，请稍后再试。",
                worker_name=self.name,
                error="缺少 API Key"
            )
        try:
            # 推送物理就绪事件，确保前端感知到链路活跃
            try:
                from v1.logic.agent_debug_controller import push_debug_event
                await push_debug_event("connected", {"message": f"Worker {self.name} 已就绪，开始任务处理..."}, context.client_id, agent=self.name, status="启动中")
            except Exception:
                pass

            # 显示 Worker 启动
            if HAS_RICH and console:
                console.print(Panel(
                    Text(f"Worker: {self.name}\n任务: {context.user_input}", style="white"),
                    title=f"[bold green][{self.name.upper()} 启动][/]",
                    border_style="green"
                ))
            
            # 构建 LLM (使用自定义原生驱动以绕过 403 配额错误)
            try:
                llm = DashScopeNativeChat(
                    model=self.model,
                    api_key=self.api_key,
                    temperature=0.1,
                    max_tokens=2000,
                    streaming=True  # 开启流式支持
                )
            except Exception as e:
                logger.warning(f"原生驱动启动失败，尝试降级: {e}")
                llm = ChatOpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url,
                    model=self.model,
                    temperature=0.1,
                    max_tokens=2000,
                )
            
            # 获取工具
            tools = self.get_tools()
            
            # 标准 ReAct 流程
            # 构建 ReAct 提示词
            react_prompt = self._build_react_prompt()
            
            # 创建 Agent
            agent = create_react_agent(llm=llm, tools=tools, prompt=react_prompt)
            
            # 创建 Executor（增加 Pydantic 兼容性保护）
            from v1.logic.central_agent_core import RichTraceHandler
            callbacks = [RichTraceHandler(client_id=context.client_id, agent_name=self.name)] if HAS_LANGCHAIN else []
            
            try:
                agent_executor = AgentExecutor(
                    agent=agent,
                    tools=tools,
                    verbose=True,
                    handle_parsing_errors=True,
                    max_iterations=max_iterations,
                    callbacks=callbacks, # 正确传递回调
                    return_intermediate_steps=True,
                )
            except Exception as e:
                logger.warning(f"Agent {self.name} Executor 初始化报错: {e}")
                # 兜底：手动注入 callbacks 属性
                agent_executor = AgentExecutor(
                    agent=agent,
                    tools=tools,
                    verbose=True,
                    handle_parsing_errors=True,
                    max_iterations=max_iterations,
                    return_intermediate_steps=True,
                )
                if not hasattr(agent_executor, 'callbacks') or not agent_executor.callbacks:
                    agent_executor.callbacks = callbacks
                else:
                    agent_executor.callbacks.extend([c for c in callbacks if c not in agent_executor.callbacks])

            # 构建输入
            input_text = self._build_input(context)
            
            # 执行
            # 💡 优化：对于流式输出，我们需要拦截最终答案并推送到 SSE
            # 这里的思路是判断当前运行是否为“最终回复”阶段
            result = await agent_executor.ainvoke({"input": input_text})
            
            # 提取结果
            raw_output = result.get("output", "")
            # 💡 关键修正：传递 intermediate_steps 供解析器恢复数据
            intermediate_steps = result.get("intermediate_steps", [])
            clean_output = self._extract_final_answer(raw_output, intermediate_steps=intermediate_steps)
            
            # 提取中间步骤和图片
            intermediate_steps = result.get("intermediate_steps", [])
            tool_outputs = []
            thoughts = []
            image_base64 = None
            
            for step in intermediate_steps:
                if len(step) >= 2:
                    action, observation = step[0], step[1]
                    tool_name = getattr(action, "tool", "unknown")
                    tool_input = getattr(action, "tool_input", "")
                    thoughts.append(f"Action: {tool_name}")
                    thoughts.append(f"Action Input: {tool_input}")
                    tool_outputs.append(str(observation))
                    thoughts.append(f"Observation: {observation}")
                    
                    # 尝试从工具输出中提取图片缓存键
                    if not image_base64:
                        try:
                            # 尝试解析为 JSON
                            obs_str = str(observation)
                            if obs_str.strip().startswith('{'):
                                obs_data = json.loads(obs_str)
                                logger.info(f"解析工具输出: {obs_data}")
                                
                                if isinstance(obs_data, dict) and "image_key" in obs_data:
                                    # 从缓存中获取图片
                                    from v1.logic.bot_tools import get_cached_image
                                    image_key = obs_data["image_key"]
                                    logger.info(f"提取图片缓存键: {image_key}")
                                    image_base64 = get_cached_image(image_key)
                                    if image_base64:
                                        logger.info(f"成功从缓存获取图片，长度: {len(image_base64)}")
                                    else:
                                        logger.warning(f"缓存中未找到图片: {image_key}")
                        except (json.JSONDecodeError, ValueError) as e:
                            # 不是 JSON 格式，跳过（正常情况，某些 Agent 不返回 JSON）
                            pass
                        except Exception as e:
                            logger.error(f"提取图片失败: {e}", exc_info=True)
            
            if image_base64:
                logger.info(f"Worker {self.name} 返回图片")
            else:
                logger.warning(f"Worker {self.name} 未返回图片")
            
            return AgentResult(
                success=True,
                answer=clean_output if clean_output else "处理完成。",
                worker_name=self.name,
                thoughts=thoughts,
                tool_outputs=tool_outputs,
                image=image_base64
            )
            
        except Exception as e:
            logger.error(f"{self.name} 执行失败: {e}", exc_info=True)
            return AgentResult(
                success=False,
                answer="处理失败，请稍后再试。",
                worker_name=self.name,
                error=str(e)
            )
    
    def _build_react_prompt(self) -> PromptTemplate:
        """构建 ReAct 格式的提示词模板。"""
        template = f"""{self.system_prompt}

## ⚠️ 核心强制指令
1. 你目前对特定猪只的数据（体重、月龄、环境等）一无所知！
2. **禁止凭空捏造任何数字或事实**。必须先调用工具获取真实数据。
3. 如果工具返回的是模拟数据或错误，也应如实告知用户，严禁生成虚假的“完美报告”。

## 可用工具
{{tools}}

## 严格推理格式（必须遵守）：
Question: 用户的问题
Thought: 你应当思考：我目前没有数据，我需要调用 [工具名] 来查询数据。
Action: 执行行动，必须是 [{{tool_names}}] 中的一个
Action Input: 行动参数（JSON 格式）
Observation: 工具返回的结果
... (如果你已经从 Observation 获取了答案，严禁重复查询，必须立即给出结论)
Thought: 我现在拿到了真实数据，可以给出答案了。
Final Answer: 最终回复用户的内容（必须基于 Observation 里的真实数据）

## 示例
Question: 12号猪几岁了？
Thought: 我需要查询12号猪的档案信息。
Action: get_pig_info_by_id
Action Input: {{{{"pig_id": "PIG012"}}}}
Observation: {{{{"id": "PIG012", "dayAge": 150}}}}
Thought: 150天约等于5个月。
Final Answer: 经过查询，12号猪现在的月龄是 5 个月。

⚠️ 格式警告：每次输出必须以 "Thought:" 开头，接着是 "Action:" 和 "Action Input:"，或者以 "Final Answer:" 结尾。不要在 Action Input 后面加多余的废话。

开始！

Question: {{input}}
Thought: {{agent_scratchpad}}"""
        
        return PromptTemplate.from_template(template)
    
    def _build_input(self, context: AgentContext) -> str:
        """构建输入文本"""
        input_text = ""
        
        # 添加历史对话
        if context.chat_history:
            input_text += "历史对话：\n"
            for msg in context.chat_history[-4:]:
                role = msg.get("role")
                content = msg.get("content", "")
                if role == "user":
                    input_text += f"用户: {content}\n"
                elif role == "assistant":
                    input_text += f"助手: {content}\n"
            input_text += "\n"
        
        input_text += f"当前问题：{context.user_input}"
        return input_text
    
    def _extract_final_answer(self, agent_output: str, intermediate_steps: list = None) -> str:
        """
        从 Agent 输出流中解析最终响应文本。
        增加了从异常/挂起的推理轨迹中恢复信息的能力。
        """
        if not agent_output:
            return ""
        
        # 1. 标准提取：匹配 Final Answer: 前缀
        match = re.search(r"Final Answer:\s*(.+)", agent_output, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        # 2. 异常恢复逻辑：如果 Agent 停止且没有 Final Answer
        if "Agent stopped" in agent_output or "Invalid Format" in agent_output:
            logger.warning(f"检测到 Agent 异常终止（{self.name}），尝试从轨迹中恢复关键信息...")
            findings = []
            
            # 从 Observation 中提取关键结论
            if intermediate_steps:
                seen_contents = set()
                for step in intermediate_steps:
                    if len(step) >= 2:
                        obs_val = step[1]
                        obs_str = str(obs_val)
                        
                        # 简单的去重逻辑：如果内容相似度很高则略过
                        content_hash = obs_str[:100] # 取前100字作为简易哈希
                        if content_hash in seen_contents:
                            continue
                        seen_contents.add(content_hash)
                        
                        # 疾病 RAG 返回的结论
                        if "relevant_diseases" in obs_str:
                            findings.append(f"【两头乌疾病知识库参考】：\n{obs_str}")
                        # 环境数据转换
                        elif "farm_stats" in obs_str:
                            try:
                                # 如果是对象，直接处理；如果是字符串，解析 JSON
                                data = obs_val if isinstance(obs_val, dict) else json.loads(obs_str)
                                stats = data.get("farm_stats", {})
                                if stats:
                                    table = "\n| 监测指标 | 数值 |\n|---|---|\n"
                                    table += f"| 总存栏数 | {stats.get('totalPigs', 'N/A')} |\n"
                                    table += f"| 异常猪只 | {stats.get('abnormalCount', 'N/A')} |\n"
                                    table += f"| 平均体温 | {stats.get('avgBodyTemp', 'N/A')} ℃ |\n"
                                    table += f"| 健康评分 | {stats.get('avgHealthScore', 'N/A')} |\n"
                                    findings.append(f"【猪场实时环境/统计采集】：{table}")
                                else:
                                    findings.append(f"【环境采集反馈】：{obs_str}")
                            except:
                                findings.append(f"【环境采集反馈】：{obs_str}")
            
            if findings:
                return "老乡，刚才智能诊断系统遇到了网络波动，但我已经通过离线链路为您同步到了关键结论：\n\n" + "\n\n".join(findings)
        
        # 3. 模式匹配：LLM 忘了写 Final Answer: 但内容带有诊断格式标记
        emoji_markers = ["[TEMP]", "[OBS]", "[MED]", "[WARN]", "[OK]", "[ERR]", "【", "###"]
        if any(marker in agent_output for marker in emoji_markers):
            lines = [line.strip() for line in agent_output.split('\n') if line.strip()]
            useful_lines = []
            for line in lines:
                if any(marker in line for marker in emoji_markers):
                    useful_lines.append(line)
                elif useful_lines and not any(m in line for m in ["Thought:", "Action:", "Observation:", "Question:", "Action Input:", "Invalid Format"]):
                    useful_lines.append(line)
            if useful_lines:
                return "\n".join(useful_lines)
        
        # 4. 过滤思考过程标记，取所有非标记行
        lines = [line.strip() for line in agent_output.split('\n') if line.strip()]
        react_markers = ["Thought:", "Action:", "Observation:", "Question:", "Action Input:", "Invalid Format", "Agent stopped"]
        filtered = [
            line for line in lines 
            if not any(marker in line for marker in react_markers)
        ]
        if filtered:
            return "\n".join(filtered)
        
        return agent_output.strip()


# ============================================================
# 具体 Worker 实现
# ============================================================

class VetAgent(WorkerAgent):
    """咱两头乌生猪的资深兽医（支持看病、看图，流程管得比较严）"""
    
    def __init__(self):
        system_prompt = """你是资深的畜牧兽医专家，专注于两头乌生猪的疾病诊断和健康管理。
你的任务是：**首先**调用病症知识库和类似病例，**然后**结合环境数据给出诊断。

## 严格准则
- **拒绝脑补**：严禁在未调用 query_pig_disease_rag 或 query_similar_cases 前给出具体病名或用药建议。
- **结合现场**：必须参考视觉分析报告（如果存在）以及环境数据。
- **专业与克制**：回复内容应保持在 3-5 句核心结论内，如有严重风险必须调用 publish_alert。"""
        
        super().__init__(name="VetAgent", system_prompt=system_prompt, tools=[])
    
    def get_tools(self) -> List[LCTool]:
        """获取兽医专家智能体可用的工具集。"""
        from v1.logic.bot_tools import list_tools
        
        all_tools = list_tools()
        vet_tool_names = [
            "query_env_status",          # 猪场环境数据
            "query_pig_disease_rag",     # 疾病知识库检索
            "query_similar_cases",       # 历史相似病例
            "query_pig_health_records",  # 猪只健康档案
            "get_farm_stats",            # 猪场统计概览
            "publish_alert",
        ]
        
        tools = []
        for name in vet_tool_names:
            if name in all_tools:
                tool = all_tools[name]
                tools.append(LCTool(
                    name=tool.name,
                    description=tool.description,
                    func=lambda x: "Sync execution not supported",
                    coroutine=tool.handler
                ))
        
        return tools
    

    async def execute(self, context: AgentContext, max_iterations: int = 4) -> AgentResult:
        """
        执行诊断逻辑。
        针对多模态输入（图片）与纯文本输入分别执行相应的处理流程。
        """
        if context.image_urls or context.audio_path:
            return await self._execute_multimodal_two_stage(context)
        
        # 纯文本模式：直接走增强版 ReAct（迭代次数设为 6 以应对复杂问诊）
        return await super().execute(context, max_iterations=6)

    def _preprocess_image(self, image_data: str) -> Optional[str]:
        """
        预处理图片：如果图片非 JPEG、体积过大或分辨率过高，则进行缩放和格式转换。
        为了配合 DashScope 原生 SDK，生成的图片将保存为本地临时文件并返回其绝对路径。
        """
        try:
            b64_str = image_data
            if "," in image_data:
                b64_str = image_data.split(",", 1)[1]
            
            # 解压 Base64
            img_bytes = base64.b64decode(b64_str)
            img = Image.open(io.BytesIO(img_bytes))
            
            orig_w, orig_h = img.size
            # 分辨率归一化 (最高 1024px)
            if max(orig_w, orig_h) > 1024:
                ratio = 1024 / max(orig_w, orig_h)
                new_size = (int(orig_w * ratio), int(orig_h * ratio))
                resample_filter = getattr(Image, 'LANCZOS', getattr(Image, 'ANTIALIAS', 1))
                img = img.resize(new_size, resample_filter)
                
            if img.mode in ('RGBA', 'P', 'LA'):
                img = img.convert('RGB')
            elif img.mode != 'RGB':
                img = img.convert('RGB')
                
            # 创建临时图片文件
            tmp_img = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
            tmp_path = tmp_img.name
            tmp_img.close()
            
            img.save(tmp_path, format="JPEG", quality=85, optimize=True)
            logger.info(f"Image preprocessed and saved: {tmp_path} ({orig_w}x{orig_h})")
            return tmp_path
        except Exception as e:
            logger.error(f"Image preprocessing or saving failed: {e}")
            return None

    def _convert_audio_to_wav(self, audio_path: str) -> Optional[str]:
        """
        将音频转码为标准 WAV 格式（16k, 单声道），以提升模型兼容性。
        """
        if not audio_path or not os.path.exists(audio_path):
            return None
        if audio_path.lower().endswith('.wav'):
            return audio_path
            
        try:
            target_path = audio_path + ".converted.wav"
            # 使用 ffmpeg 进行转码
            cmd = ['ffmpeg', '-y', '-i', audio_path, '-ar', '16000', '-ac', '1', target_path]
            logger.info(f"Transcoding audio for DashScope: {audio_path} -> WAV")
            subprocess.run(cmd, capture_output=True, check=True)
            if os.path.exists(target_path):
                return target_path
        except Exception as e:
            logger.error(f"FFmpeg transcode failed: {e}")
        return audio_path

    async def _execute_multimodal_two_stage(self, context: AgentContext) -> AgentResult:
        """
        执行多模态两阶段诊断流程。
        第一阶段：利用 Omni 模型进行跨模态特征提取。
        第二阶段：基于提取的特征，驱动 ReAct 专家链进行深度诊断。
        """
        # ============================================================
        # 阶段 1: 多模态观察与特征提取 (Omni Assistant)
        # ============================================================
        visual_and_audio_analysis = ""
        try:
            from v1.logic.agent_debug_controller import push_debug_event
            # 推送到前端展示：正在启动视觉识别
            await push_debug_event("thought", {"content": "检测到图片/语音输入，正在启动多模态感知引擎解析生猪体征..."}, context.client_id, agent="VetAgent", status="工作中")
            
            if HAS_RICH and console:
                console.print(Panel(
                    "执行中...",
                    title=f"[bold green][VetAgent 阶段1: 视觉/听觉识别][/]",
                    border_style="green"
                ))
            
            # 调用 Omni 提取特征
            await push_debug_event("action", {"tool": "VisualPerception", "input": "Image/Audio Streams", "thought": "正在进行跨模态特征提取，识别皮温、呼吸频率及行为模式..."}, context.client_id, agent="VetAgent", status="工作中")
            visual_and_audio_analysis = await self._execute_omni_feature_extraction(context)
            
            # 手动推送特征报告碎片（模拟流失反馈感）
            await push_debug_event("observation", {"output": f"体征提取完成：\n{visual_and_audio_analysis}"}, context.client_id, agent="VetAgent", status="工作中")
            
            # 💡 关键提示：视觉识别结束，开始专家逻辑
            await push_debug_event("thought", {"content": "视觉体征已锁定，正在关联两头乌疾病知识库进行逻辑对齐..."}, context.client_id, agent="VetAgent", status="工作中")
            
            if HAS_RICH and console:
                console.print(Panel(
                    Text(visual_and_audio_analysis, style="white"),
                    title="[bold cyan][阶段1完成: 特征报告][/]",
                    border_style="cyan"
                ))
            
            logger.info(f"阶段1特征提取完成: {visual_and_audio_analysis[:200]}...")
            
        except Exception as e:
            logger.error(f"阶段1特征提取失败: {e}", exc_info=True)
            visual_and_audio_analysis = f"多模态分析暂时不可用（{str(e)[:50]}），将尝试基于纯文本描述进行诊断。"

        # ============================================================
        # 阶段 2: 专家工具链诊断 (ReAct Loop)
        # ============================================================
        try:
            await push_debug_event("thought", {"content": "视觉分析完毕，已识别到关键体征。现在启动专家逻辑进行深度诊断方案交叉验证..."}, context.client_id, agent="VetAgent", status="工作中")
            
            if HAS_RICH and console:
                console.print(Panel(
                    Text("[二阶段诊断 - 开启工具链交叉验证]", style="white"),
                    title=f"[bold green][VetAgent 阶段2: 专家链启动][/]",
                    border_style="green"
                ))
            
            # 💡 优化：精简一阶段报告，防止上下文过长导致二阶段模型疲劳/重复
            short_analysis = visual_and_audio_analysis
            if len(visual_and_audio_analysis) > 300:
                # 提取关键评估和病灶信息，略过润色性文字
                lines = visual_and_audio_analysis.split("\n")
                important_lines = [l for l in lines if any(k in l for k in ["评估", "病灶", "状态", "特征", "建议"])]
                if important_lines:
                    short_analysis = "\n".join(important_lines[:8])

            # 构造增强的用户输入
            enhanced_input = "【视觉特征摘要】\n"
            enhanced_input += f"{short_analysis}\n\n"
            if context.user_input:
                enhanced_input += f"【用户最新反馈】\n{context.user_input}\n\n"
            enhanced_input += "请结合视觉摘要，严谨调用工具查阅环境和知识库。严禁重复调用相同工具！如果已经获取信息，必须立即给出 Final Answer。"
            
            # 创建纯文本上下文供 ReAct 使用
            text_context = AgentContext(
                user_id=context.user_id,
                user_input=enhanced_input,
                chat_history=context.chat_history,
                metadata=context.metadata,
                client_id=context.client_id,
                image_urls=None, # ReAct 阶段不需要再传图片 URLs
                audio_path=None  # ReAct 阶段不需要再传音频
            )
            
            # 如果阶段 1 已经给出了包含诊断结论的深入分析，且用户问题较简单，则可能提前结束
            # 💡 增强快轨识别逻辑：识别睡眠、健康、正常等状态
            fast_track_keywords = ["诊断结论", "处理建议", "初步评估", "建议", "深度休息", "睡眠", "健康姿态", "未见明显异常"]
            if any(k in visual_and_audio_analysis for k in fast_track_keywords):
                # 如果没有明显的病理词汇（如病、拉稀、咳嗽等），或者用户只是在问猪在干什么
                pathological_keywords = ["生病", "不舒服", "拉稀", "咳嗽", "发烧", "异常"]
                is_urgent = any(k in (context.user_input or "") for k in pathological_keywords)
                
                if not is_urgent or "处于健康状态" in visual_and_audio_analysis or "正常的休息" in visual_and_audio_analysis:
                    logger.info("阶段 1 报告已足够详尽且体征正常，触发快轨返回")
                    
                    # 构建一个友好的 Final Answer
                    final_ans = visual_and_audio_analysis
                    if "Final Answer:" in visual_and_audio_analysis:
                        final_ans = self._extract_final_answer(visual_and_audio_analysis)
                    
                    # 确保图片带回
                    b64_img = None
                    if context.image_urls:
                        for url in context.image_urls:
                            if url.startswith("data:image"):
                                b64_img = url.split(",", 1)[1] if "," in url else url
                                break
                    
                    return AgentResult(
                        success=True,
                        answer=final_ans,
                        worker_name=self.name,
                        image=b64_img,
                        metadata={"multimodal_mode": "fast_track_normal_vital"}
                    )

            # 执行 ReAct (专家诊断阶段，迭代次数设为 6)
            react_result = await self.execute(text_context, max_iterations=6)
            
            # 💡 核心修复：透传第一阶段的视觉体征图
            # 如果 react_result 本身没带图（工具链没产出），则把 Omni 阶段处理的图带上
            if not react_result.image and context.image_urls:
                for img_url in context.image_urls:
                    if img_url.startswith("data:image"):
                        react_result.image = img_url.split(",", 1)[1] if "," in img_url else img_url
                        logger.info("已从原始上下文透传图片到最终结果")
                        break
            
            # 丰富元数据
            react_result.metadata = react_result.metadata or {}
            react_result.metadata["multimodal_stage1"] = "omni-turbo"
            react_result.metadata["feature_description"] = visual_and_audio_analysis[:500]
            react_result.thoughts = [f"阶段1: 跨模态特征提取 (Omni)"] + (react_result.thoughts or [])
            
            return react_result
            
        except Exception as e:
            logger.error(f"阶段2专家链执行失败: {e}", exc_info=True)
            # 兜底：即使挂了也返回特征描述
            return AgentResult(
                success=True,
                answer=f"老乡，我通过多模态观察发现：\n{visual_and_audio_analysis}\n\n由于专家诊断系统暂时繁忙，建议参考上述观察现象并联系驻场兽医。",
                worker_name=self.name,
                metadata={"degraded_mode": True}
            )

    async def _execute_omni_feature_extraction(self, context: AgentContext) -> str:
        """
        利用原生多模态 SDK，将图片和音频识别为客观文本描述。
        """
        import dashscope
        from dashscope import MultiModalConversation
        
        api_key, _, _, omni_model = self._get_llm_config()
        if not api_key:
            return "API Key 未配置，无法进行特征提取。"

        # 视觉分析专用提示词：结合客观观察和初步专业建议
        visual_prompt = (
            "你是一名资深兽医助手。你需要仔细观察图片中的猪只以及听取语音内容，总结异常现象并给出初步评估。\n"
            "## 报告规范\n"
            "1. 【外观特征】毛色、皮肤、体型是否有异样\n"
            "2. 【典型病灶】红斑、溃疡、呼吸困难、异常分泌物等\n"
            "3. 【初步评估】根据视觉特征判断可能的健康风险\n"
            "4. 【建议】是否需要立即联系兽医或进行进一步检查\n\n"
            "**重要**：如果用户的问题仅涉及视觉识别（如'图里有几只猪'、'它在干什么'），请直接给出 'Final Answer: [你的详细回答]'。"
        )

        temp_image_paths = []
        final_audio_path = None
        
        try:
            content = [{'text': visual_prompt}]
            
            # 图片处理
            if context.image_urls:
                for url_or_path in context.image_urls[:3]:
                    target_file = None
                    if os.path.exists(url_or_path) and os.path.isfile(url_or_path):
                        try:
                            # 即使本身是文件，也进行预处理以确保格式和大小达标
                            with open(url_or_path, "rb") as f:
                                b64_data = base64.b64encode(f.read()).decode("utf-8")
                            target_file = self._preprocess_image(f"data:image/jpeg;base64,{b64_data}")
                        except: target_file = url_or_path
                    elif url_or_path.startswith("data:image"):
                        target_file = self._preprocess_image(url_or_path)
                    
                    if target_file and os.path.exists(target_file):
                        # 核心修正：Windows 下使用 file:// 路径 (移除导致报错的额外斜杠)
                        abs_path = os.path.abspath(target_file).replace('\\', '/')
                        if os.name == 'nt' and ':' in abs_path:
                            # Windows: file://C:/path
                            content.append({'image': f"file://{abs_path}"})
                        else:
                            # Linux/Unix: file:///path
                            if not abs_path.startswith('/'):
                                abs_path = '/' + abs_path
                            content.append({'image': f"file://{abs_path}"})
                        if target_file != url_or_path:
                            temp_image_paths.append(target_file)
            
            # 音频处理
            if context.audio_path:
                final_audio_path = self._convert_audio_to_wav(context.audio_path)
                if final_audio_path and os.path.exists(final_audio_path):
                    abs_audio_path = os.path.abspath(final_audio_path).replace('\\', '/')
                    if os.name == 'nt' and ':' in abs_audio_path:
                        content.append({'audio': f"file://{abs_audio_path}"})
                    else:
                        if not abs_audio_path.startswith('/'):
                            abs_audio_path = '/' + abs_audio_path
                        content.append({'audio': f"file://{abs_audio_path}"})

            def _call_dashscope():
                # 设置全局 API KEY 以防某些底层 SDK 调用需要
                import dashscope
                dashscope.api_key = api_key
                return MultiModalConversation.call(
                    model=omni_model,
                    messages=[{'role': 'user', 'content': content}],
                    api_key=api_key
                )
            
            response = await asyncio.to_thread(_call_dashscope)
            if response.status_code == 200:
                # 兼容不同版本的输出结构
                res_output = response.output
                if hasattr(res_output, 'choices') and res_output.choices:
                    msg_content = res_output.choices[0].message.content
                elif hasattr(res_output, 'choice') and res_output.choice:
                    msg_content = res_output.choice.message.content
                else:
                    msg_content = str(res_output)
                if isinstance(msg_content, list):
                    result_text = ""
                    for item in msg_content:
                        if isinstance(item, dict) and 'text' in item:
                            result_text += item['text']
                        elif isinstance(item, str):
                            result_text += item
                    result_text = result_text.strip()
                else:
                    result_text = str(msg_content).strip()
                
                if not result_text:
                    logger.warning(f"Feature extraction returned empty text for model {omni_model}")
                    return "未能从多模态输入中提取到有效特征信息。"
                return result_text
            else:
                err_msg = f"特征提取失败: {response.code} - {response.message}"
                logger.error(err_msg)
                return err_msg
        except Exception as e:
            return f"特征提取过程中发生异常: {str(e)}"
        finally:
            # 资源清理
            if final_audio_path and final_audio_path != context.audio_path:
                try: os.unlink(final_audio_path)
                except: pass
            for p in temp_image_paths:
                try: os.unlink(p)
                except: pass


class DataAgent(WorkerAgent):
    """
    生产数据分析智能体。
    负责猪只档案查询、增重预测及生产统计数据分析。
    """
    
    def __init__(self):
        system_prompt = """你作为生产数据分析专家，负责处理猪只档案查询及生长预测任务。
        
核心职责：
1. 猪只列表及详细档案信息检索。
2. 基于历史数据的生长曲线预测生成。
3. 生产统计数据的多维分析。

执行约束：
- 确保输出数据的准确性与客观性，杜绝编造。
- 采用结构化的格式输出，提升可读性。
- 响应内容需简洁、专业。"""
        
        system_prompt += """

濡傛灉鐢ㄦ埛鏄庣‘瑕佲€滅敓闀挎洸绾挎姤鍛娾€濄€侀娴嬫姤鍛娿€佹湀搴︿綋閲嶈〃鏍硷紝鎴栬€呰姹備綘杈撳嚭鍏煎鍓嶇鐨勭粨鏋滐紝鍒欏繀椤绘敼鐢ㄤ互涓嬬壒鍒鍒欙細
- 蹇呴』鍏堣皟鐢?get_pig_info_by_id锛屽啀璋冪敤 query_pig_growth_prediction
- 鍗虫椂宸ュ叿杩斿洖 JSON锛屼篃蹇呴』鑷繁鏁寸悊鎴?Markdown锛屼笉鑳界洿鎺ヨ创鍘熷 JSON
- 鏈€缁堝洖澶嶅繀椤诲寘鍚簿纭爣棰橈細### 棰勬祴鐢熼暱鏇茬嚎鏁版嵁 (Monthly)
- 鏈€缁堝洖澶嶅繀椤诲寘鍚〃鏍硷紝琛ㄥご蹇呴』鏄細| 鏈堜唤 (Month) | 鎷熷悎/棰勬祴浣撻噸 (kg) | 鐘舵€? |
- 琛ㄦ牸绗竴鍒楀彧鑳藉啓鏁板瓧鏈堜唤锛岀浜屽垪鍙兘鍐欐暟瀛椾綋閲嶏紝绗笁鍒楀啓鈥滃綋鍓嶁€濇垨鈥滈娴嬧€濈瓑鐘舵€佽鏄?
- 杩欑鎶ュ憡鍦烘櫙涓嶅啀闄愬埗 1-3 鍙ヨ瘽锛屼互鎶ュ憡瀹屾暣鎬т负浼樺厛"""

        super().__init__(name="DataAgent", system_prompt=system_prompt, tools=[])
    
    def get_tools(self) -> List[LCTool]:
        """获取数据分析智能体可用的工具集。"""
        from v1.logic.bot_tools import list_tools
        
        # 只暴露数据相关工具（现在通过 Java API）
        all_tools = list_tools()
        data_tool_names = [
            "list_pigs",
            "get_pig_info_by_id",
            "get_abnormal_pigs",
            "get_farm_stats",
            "query_pig_growth_prediction",
            "publish_alert"
        ]
        
        tools = []
        for name in data_tool_names:
            if name in all_tools:
                tool = all_tools[name]
                tools.append(LCTool(
                    name=tool.name,
                    description=tool.description,
                    func=lambda x: "Sync execution not supported",
                    coroutine=tool.handler
                ))
        
        return tools
    


    async def execute(self, context: AgentContext) -> AgentResult:
        """Use LangChain when available, otherwise fall back to direct tool orchestration."""
        if HAS_LANGCHAIN:
            return await super().execute(context)
        return await self._execute_without_langchain(context)

    async def _execute_without_langchain(self, context: AgentContext) -> AgentResult:
        from v1.logic.bot_tools import tool_get_pig_info_by_id, tool_query_pig_growth_prediction

        pig_id = str((context.metadata or {}).get("pig_id") or self._extract_pig_id(context.user_input) or "").strip()
        if not pig_id:
            return AgentResult(
                success=False,
                answer="处理失败，请提供猪只编号。",
                worker_name=self.name,
                error="missing pig_id for data-agent fallback",
            )

        logger.info("data_agent fallback start pig_id=%s", pig_id)

        try:
            pig_raw = await tool_get_pig_info_by_id(json.dumps({"pig_id": pig_id}, ensure_ascii=False))
            pig_info = self._loads_json_maybe(pig_raw)
            if not isinstance(pig_info, dict):
                raise ValueError(f"invalid pig info payload: {pig_raw[:200]}")
            if pig_info.get("error"):
                raise ValueError(str(pig_info["error"]))

            report = self._build_legacy_growth_curve_report(pig_id, pig_info)
            report_mode = "legacy_dual_track_report"

            if not report:
                growth_raw = await tool_query_pig_growth_prediction(json.dumps({"pig_id": pig_id}, ensure_ascii=False))
                growth_data = self._loads_json_maybe(growth_raw)
                if not isinstance(growth_data, dict):
                    raise ValueError(f"invalid growth payload: {growth_raw[:200]}")
                if growth_data.get("error"):
                    raise ValueError(str(growth_data["error"]))
                report = self._build_growth_curve_report_v2(pig_id, pig_info, growth_data)
                report_mode = "simple_growth_report"

            logger.info("data_agent fallback success pig_id=%s", pig_id)
            return AgentResult(
                success=True,
                answer=report,
                worker_name=self.name,
                metadata={
                    "mode": "fallback_without_langchain",
                    "report_mode": report_mode,
                    "pig_id": pig_id,
                },
            )
        except Exception as e:
            logger.error("data_agent fallback failed pig_id=%s error=%s", pig_id, e, exc_info=True)
            return AgentResult(
                success=False,
                answer="处理失败，请稍后再试。",
                worker_name=self.name,
                error=str(e),
            )

    def _extract_pig_id(self, text: str) -> Optional[str]:
        match = re.search(r"\b(?:PIG|LTW)[-_]?\d+\b", text or "", re.IGNORECASE)
        return match.group(0) if match else None

    def _loads_json_maybe(self, text: str):
        try:
            return json.loads(text)
        except Exception:
            return None

    def _build_legacy_growth_curve_report(self, pig_id: str, pig_info: dict) -> Optional[str]:
        try:
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            if base_dir not in sys.path:
                sys.path.insert(0, base_dir)

            from pig_rag.pig_agent import run_dual_track_inspection

            breed = str(pig_info.get("breed") or "两头乌")
            lifecycle = pig_info.get("lifecycle") or []
            weight_series = self._extract_weight_series(lifecycle)

            current_month = self._coerce_int(
                pig_info.get("current_month") or pig_info.get("currentMonth"),
                0,
            )
            current_weight = self._coerce_float(
                pig_info.get("current_weight_kg")
                or pig_info.get("currentWeightKg")
                or pig_info.get("currentWeight"),
                0.0,
            )

            if not current_month:
                current_month = len(weight_series) or (len(lifecycle) if isinstance(lifecycle, list) else 0)
            if not current_weight and weight_series:
                current_weight = weight_series[-1]

            if current_weight > 0 and (not weight_series or abs(weight_series[-1] - current_weight) > 1e-6):
                weight_series.append(current_weight)

            if not weight_series:
                logger.warning("data_agent legacy report skipped pig_id=%s reason=no_weight_series", pig_id)
                return None

            current_day_age = self._coerce_int(
                pig_info.get("current_day_age")
                or pig_info.get("currentDayAge")
                or pig_info.get("dayAge"),
                0,
            )
            if not current_day_age:
                current_day_age = max(current_month, len(weight_series), 1) * 30

            logger.info("data_agent fallback using legacy dual-track report pig_id=%s", pig_id)
            return run_dual_track_inspection(
                pig_id=pig_id,
                breed=breed,
                current_day_age=current_day_age,
                current_weight_series=weight_series,
                verbose=False,
            )
        except Exception as e:
            logger.warning(
                "data_agent legacy report failed pig_id=%s error=%s; falling back to simple report",
                pig_id,
                e,
                exc_info=True,
            )
            return None

    def _coerce_int(self, value, default: int = 0) -> int:
        try:
            return int(value)
        except Exception:
            return default

    def _coerce_float(self, value, default: float = 0.0) -> float:
        try:
            return float(value)
        except Exception:
            return default

    def _extract_weight_series(self, lifecycle: list) -> list[float]:
        if not isinstance(lifecycle, list):
            return []

        rows = [item for item in lifecycle if isinstance(item, dict)]
        rows.sort(key=lambda item: self._coerce_int(item.get("month"), 9999))

        weight_series: list[float] = []
        for item in rows:
            weight = self._coerce_float(
                item.get("weight_kg") or item.get("weightKg") or item.get("weight"),
                0.0,
            )
            if weight > 0:
                weight_series.append(weight)
        return weight_series

    def _pick_current_month_data(self, lifecycle: list, current_month: int) -> dict:
        for item in lifecycle:
            if isinstance(item, dict) and self._coerce_int(item.get("month"), -1) == current_month:
                return item
        if lifecycle and isinstance(lifecycle[-1], dict):
            return lifecycle[-1]
        return {}

    def _extract_historical_points(self, lifecycle: list, current_month: int) -> list[dict]:
        if not isinstance(lifecycle, list):
            return []

        rows = [item for item in lifecycle if isinstance(item, dict)]
        rows.sort(key=lambda item: self._coerce_int(item.get("month"), 9999))

        points: list[dict] = []
        for item in rows:
            month = self._coerce_int(item.get("month"), 0)
            weight = self._coerce_float(
                item.get("weight_kg") or item.get("weightKg") or item.get("weight"),
                0.0,
            )
            if month <= 0 or weight <= 0:
                continue
            if current_month and month > current_month:
                continue

            points.append(
                {
                    "month": month,
                    "weight_kg": round(weight, 2),
                    "status": "当前实测" if current_month and month == current_month else "历史实测",
                }
            )

        return points

    def _select_best_match(self, growth_data: dict) -> dict:
        matches = growth_data.get("top_matches") or []
        if not isinstance(matches, list) or not matches:
            return {}
        valid_matches = [m for m in matches if isinstance(m, dict)]
        if not valid_matches:
            return {}
        return sorted(
            valid_matches,
            key=lambda m: self._coerce_float(m.get("similarity_distance"), 9999.0),
        )[0]

    def _collect_future_points(self, growth_data: dict, current_month: int) -> tuple[list[dict], int]:
        matches = growth_data.get("top_matches") or []
        if not isinstance(matches, list):
            return [], 0

        valid_matches = sorted(
            [match for match in matches if isinstance(match, dict)],
            key=lambda match: self._coerce_float(match.get("similarity_distance"), 9999.0),
        )
        if not valid_matches:
            return [], 0

        month_buckets: dict[int, list[float]] = {}
        for match in valid_matches:
            future_track = match.get("historical_future_track") or []
            if not isinstance(future_track, list):
                continue

            for item in future_track:
                if not isinstance(item, dict):
                    continue

                month = self._coerce_int(item.get("month"), 0)
                weight = self._coerce_float(item.get("weight_kg") or item.get("weight"), 0.0)
                if month <= current_month or weight <= 0:
                    continue

                month_buckets.setdefault(month, []).append(weight)

        future_points: list[dict] = []
        for month in sorted(month_buckets.keys()):
            weights = month_buckets[month]
            avg_weight = round(sum(weights) / len(weights), 2)

            if avg_weight >= 100:
                status = "预计出栏"
            elif month == current_month + 1:
                status = "下月预测"
            else:
                status = "后期预测"

            future_points.append(
                {
                    "month": month,
                    "weight_kg": avg_weight,
                    "status": status,
                }
            )

        return future_points, len(valid_matches)

    def _build_growth_curve_report(self, pig_id: str, pig_info: dict, growth_data: dict) -> str:
        breed = str(pig_info.get("breed") or "未知")
        lifecycle = pig_info.get("lifecycle") or []
        current_month = self._coerce_int(pig_info.get("current_month") or pig_info.get("currentMonth"), 0)
        current_weight = self._coerce_float(
            pig_info.get("current_weight_kg") or pig_info.get("currentWeightKg") or pig_info.get("currentWeight"),
            0.0,
        )

        if not current_month and isinstance(lifecycle, list):
            current_month = len(lifecycle)
        if not current_weight and isinstance(lifecycle, list):
            month_data = self._pick_current_month_data(lifecycle, current_month or len(lifecycle))
            current_weight = self._coerce_float(
                month_data.get("weight_kg") or month_data.get("weightKg") or month_data.get("weight"),
                0.0,
            )

        best_match = self._select_best_match(growth_data)
        matched_pig = str(best_match.get("matched_pig") or "N/A")
        distance = self._coerce_float(best_match.get("similarity_distance"), 0.0)
        future_track = best_match.get("historical_future_track") or []

        points = []
        if current_month:
            points.append({"month": current_month, "weight_kg": round(current_weight, 2), "status": "当前"})

        if isinstance(future_track, list):
            sorted_track = sorted(
                [x for x in future_track if isinstance(x, dict)],
                key=lambda x: self._coerce_int(x.get("month"), 9999),
            )
            for item in sorted_track:
                month = self._coerce_int(item.get("month"), 0)
                weight = self._coerce_float(item.get("weight_kg"), 0.0)
                if month > 0 and weight > 0:
                    points.append(
                        {
                            "month": month,
                            "weight_kg": round(weight, 2),
                            "status": str(item.get("status") or "预测"),
                        }
                    )

        deduped = {}
        for item in points:
            deduped[item["month"]] = item
        points = [deduped[m] for m in sorted(deduped.keys())]

        last_point = points[-1] if points else {"month": current_month, "weight_kg": current_weight}
        last_month = self._coerce_int(last_point.get("month"), current_month)
        last_weight = self._coerce_float(last_point.get("weight_kg"), current_weight)
        gain = round(last_weight - current_weight, 2)

        lines = [
            f"## {pig_id} 生长曲线预测报告",
            "",
            f"- 品种：{breed}",
            f"- 当前月龄：{current_month}",
            f"- 当前体重：{current_weight:.2f} kg",
            "",
            "### 预测结论",
            f"- 本次参考的最相似历史个体为 `{matched_pig}`，相似距离约 {distance:.4f}。",
            f"- 若按该历史轨迹延续，预计到 {last_month} 月体重约 {last_weight:.2f} kg。",
            f"- 从当前到预测终点，累计增重约 {gain:.2f} kg。",
        ]

        if len(points) <= 1:
            lines.append("- 当前可用预测数据较少，后续补充更多历史样本后曲线会更完整。")

        lines.extend(
            [
                "",
                "### 预测生长曲线数据 (Monthly)",
                "| 月份 (Month) | 拟合/预测体重 (kg) | 状态 |",
                "| --- | --- | --- |",
            ]
        )

        for item in points:
            lines.append(
                f"| {self._coerce_int(item.get('month'))} | {self._coerce_float(item.get('weight_kg')):.2f} | {str(item.get('status') or '预测')} |"
            )

        return "\n".join(lines)

    def _build_growth_curve_report_v2(self, pig_id: str, pig_info: dict, growth_data: dict) -> str:
        breed = str(pig_info.get("breed") or "未知")
        lifecycle = pig_info.get("lifecycle") or []
        current_month = self._coerce_int(pig_info.get("current_month") or pig_info.get("currentMonth"), 0)
        current_weight = self._coerce_float(
            pig_info.get("current_weight_kg") or pig_info.get("currentWeightKg") or pig_info.get("currentWeight"),
            0.0,
        )

        if not current_month and isinstance(lifecycle, list):
            current_month = len(lifecycle)
        if not current_weight and isinstance(lifecycle, list):
            month_data = self._pick_current_month_data(lifecycle, current_month or len(lifecycle))
            current_weight = self._coerce_float(
                month_data.get("weight_kg") or month_data.get("weightKg") or month_data.get("weight"),
                0.0,
            )

        best_match = self._select_best_match(growth_data)
        matched_pig = str(best_match.get("matched_pig") or "N/A")
        distance = self._coerce_float(best_match.get("similarity_distance"), 0.0)

        points = self._extract_historical_points(lifecycle, current_month)
        if current_month and current_weight > 0 and not any(item.get("month") == current_month for item in points):
            points.append({"month": current_month, "weight_kg": round(current_weight, 2), "status": "当前实测"})

        future_points, match_count = self._collect_future_points(growth_data, current_month)
        points.extend(future_points)

        deduped: dict[int, dict] = {}
        for item in points:
            deduped[self._coerce_int(item.get("month"), 0)] = item
        points = [deduped[month] for month in sorted(deduped.keys()) if month > 0]

        last_point = points[-1] if points else {"month": current_month, "weight_kg": current_weight}
        last_month = self._coerce_int(last_point.get("month"), current_month)
        last_weight = self._coerce_float(last_point.get("weight_kg"), current_weight)
        gain = round(last_weight - current_weight, 2)

        lines = [
            f"## {pig_id} 生长曲线预测报告",
            "",
            f"- 品种：{breed}",
            f"- 当前月龄：{current_month}",
            f"- 当前体重：{current_weight:.2f} kg",
            "",
            "### 预测结论",
            f"- 本次共参考 {match_count} 个相似历史案例，最相似个体为 `{matched_pig}`，相似距离约 {distance:.4f}。",
            f"- 若按历史相似轨迹延续，预计到 {last_month} 月体重约 {last_weight:.2f} kg。",
            f"- 从当前到预测终点，累计增重约 {gain:.2f} kg。",
        ]

        if not future_points:
            lines.append("- 当前可用的未来预测月份较少，后续补充更多历史样本后曲线会更完整。")

        lines.extend(
            [
                "",
                "### 预测生长曲线数据 (Monthly)",
                "| 月份 (Month) | 拟合/预测体重 (kg) | 状态 |",
                "| --- | --- | --- |",
            ]
        )

        for item in points:
            lines.append(
                f"| {self._coerce_int(item.get('month'))} | {self._coerce_float(item.get('weight_kg')):.2f} | {str(item.get('status') or '预测')} |"
            )

        return "\n".join(lines)


class PerceptionAgent(WorkerAgent):
    """
    视觉感知智能体。
    负责监控视频流分析、猪只识别及现场环境状态检测。
    """
    
    def __init__(self):
        system_prompt = """你作为视觉感知专家，负责实时监控画面的特征提取与分析。
你的任务是：**必须先调用** capture_pig_farm_snapshot 获取画面，**绝不允许凭空猜测**画面内容。

## 执行约束
- **客观描述**：严格引用工具返回的 summary 与 detection_count。
- **环境反思**：若画面不清晰或没检测到猪只，需客观说明环境限制（光线、角度等）。
- **言简意赅**：保持回复专业且精炼。"""
        
        super().__init__(name="PerceptionAgent", system_prompt=system_prompt, tools=[])
    
    def get_tools(self) -> List[LCTool]:
        """获取视觉感知智能体可用的工具集。"""
        from v1.logic.bot_tools import list_tools
        
        all_tools = list_tools()
        perception_tool_names = ["capture_pig_farm_snapshot", "publish_alert"]
        
        tools = []
        for name in perception_tool_names:
            if name in all_tools:
                tool = all_tools[name]
                tools.append(LCTool(
                    name=tool.name,
                    description=tool.description,
                    func=lambda x: "Sync execution not supported",
                    coroutine=tool.handler
                ))
        
        return tools
    


# ============================================================
# 多智能体协调器
# ============================================================

# ============================================================
# GrowthCurveAgent - 生长曲线专属 Worker
# ============================================================

class GrowthCurveAgent(WorkerAgent):
    """
    生长曲线专项分析智能体。
    依据猪只历史数据与生长预测模型生成标准的 Markdown 格式报告。
    """

    def __init__(self):
        system_prompt = """你是生长曲线分析专家。
你的任务是：**首先**查询后台真实的生猪档案和预测轨迹，**然后**整合这些真实数据生成报告。

## 关键原则
- **数据真实性**：绝对禁止编造任何体重数字或月龄。
- **工具依赖**：必须调用 get_pig_info_by_id 获取基础档案，调用 query_pig_growth_prediction 获取预测曲线。
- **流程规范**：获取数据（Thought/Action/Observation） -> 整合分析 -> 格式化输出（Final Answer）。

## 输出报告规范（Final Answer 部分）：
1. 基本信息表格（ID、品种、月龄、当前体重）
2. 历史实测数据表格，标题必须为：### 历史实测数据 (Historical)。表格必须包含且仅包含三列：| 月龄 | 实测体重 (kg) | 状态 |
3. 预测增长表格，标题必须为：### 预测生长曲线数据 (Monthly)。表格必须包含且仅包含三列：| 月份 (Month) | 拟合/预测体重 (kg) | 状态 |
4. 针对性的生产建议（如饲喂调整、出栏评估等）"""

        super().__init__(name="GrowthCurveAgent", system_prompt=system_prompt, tools=[])

    def get_tools(self) -> List[LCTool]:
        from v1.logic.bot_tools import list_tools
        all_tools = list_tools()
        tool_names = ["get_pig_info_by_id", "query_pig_growth_prediction"]
        tools = []
        for name in tool_names:
            if name in all_tools:
                t = all_tools[name]
                tools.append(LCTool(
                    name=t.name,
                    description=t.description,
                    func=lambda x: "Sync execution not supported",
                    coroutine=t.handler
                ))
        return tools



    async def execute(self, context: AgentContext) -> AgentResult:
        if HAS_LANGCHAIN:
            return await self._execute_react(context)
        return await self._direct_tool_call(context)

    async def _execute_react(self, context: AgentContext) -> AgentResult:
        if not self.api_key:
            return AgentResult(success=False, answer="系统繁忙，请稍后再试。", worker_name=self.name, error="no api key")
        try:
            # 迁移到 DashScopeNativeChat
            llm = DashScopeNativeChat(model=self.model, api_key=self.api_key, temperature=0.1, max_tokens=3000, streaming=True)
            
            tools = self.get_tools()
            agent = create_react_agent(llm=llm, tools=tools, prompt=self._build_react_prompt())
            
            from v1.logic.central_agent_core import RichTraceHandler
            callbacks = [RichTraceHandler(client_id=context.client_id, agent_name=self.name)] if HAS_RICH else []
            
            executor = AgentExecutor(
                agent=agent,
                tools=tools,
                verbose=True,      # 开启调试日志
                handle_parsing_errors=True,
                max_iterations=6,
                return_intermediate_steps=True,
                callbacks=callbacks,
            )
            result = await executor.ainvoke({"input": self._build_input(context)})
            raw = result.get("output", "")
            answer = self._extract_final_answer(raw)
            steps = result.get("intermediate_steps", [])
            tool_outputs = [str(s[1]) for s in steps if len(s) >= 2]
            thoughts = [f"Action: {getattr(s[0], 'tool', '?')}" for s in steps if len(s) >= 2]
            return AgentResult(success=True, answer=answer or "报告生成完成。",
                worker_name=self.name, thoughts=thoughts, tool_outputs=tool_outputs)
        except Exception as e:
            logger.error("growth_curve_agent react failed: %s", e, exc_info=True)
            return await self._direct_tool_call(context)

    async def _direct_tool_call(self, context: AgentContext) -> AgentResult:
        """非 LangChain 环境下的降级处理逻辑。"""
        from v1.logic.bot_tools import tool_get_pig_info_by_id, tool_query_pig_growth_prediction
        meta_pig_id = str((context.metadata or {}).get("pig_id", "")).strip()
        match = re.search(r"\b(?:PIG|LTW)[-_]?\d+\b", context.user_input or "", re.IGNORECASE)
        pig_id = meta_pig_id or (match.group(0) if match else "")
        if not pig_id:
            return AgentResult(success=False, answer="缺少猪只编号，无法生成生长曲线报告。", worker_name=self.name, error="missing pig_id")
        try:
            growth_data = json.loads(growth_raw) if growth_raw.strip().startswith("{") else {}
            breed = pig_info.get("breed", "两头乌")
            current_month = pig_info.get("current_month") or pig_info.get("currentMonth") or 0
            current_weight = pig_info.get("current_weight_kg") or pig_info.get("currentWeightKg") or 0.0
            lifecycle = pig_info.get("lifecycle") or []
            hist_rows = []
            for d in lifecycle:
                m = d.get("month") or d.get("monthIndex", 0)
                w = d.get("weight_kg") or d.get("weightKg") or d.get("weight", 0)
                status = "当前实测" if m == current_month else "历史实测"
                hist_rows.append(f"| {m} | {w} | {status} |")
            pred_rows = []
            for pt in (growth_data.get("predictions") or growth_data.get("points") or []):
                mo = pt.get("month", 0)
                wt = float(pt.get("weight_kg") or pt.get("weight") or 0)
                st = pt.get("status", "预测")
                pred_rows.append(f"| {mo} | {wt:.2f} | {st} |")
            lines = [
                f"## 基本信息",
                f"- **猪只ID**：{pig_id}",
                f"- **品种**：{breed}",
                f"- **当前月龄**：{current_month}月",
                f"- **当前体重**：{current_weight}kg",
                "",
                "## 生长趋势分析",
                "- 已根据历史数据及相似案例生成预测曲线，请参见下方表格。",
                "",
                "### 历史实测数据 (Historical)",
                "| 月份 | 实测体重(kg) | 状态 |",
                "| --- | --- | --- |",
                *hist_rows,
                "",
                "### 预测生长曲线数据 (Monthly)",
                "| 月份 (Month) | 拟合/预测体重 (kg) | 状态 |",
                "| --- | --- | --- |",
                *pred_rows,
                "",
                "## AI 建议",
                "1. 对照预测曲线持续记录实测体重，偏差超过 5kg 时重新评估饲喂方案。",
                "2. 定期核对生猪月龄与体重的匹配度，确保生长进度符合预期。",
                "3. 按当前生长轨迹，适时调整饲料配比以满足快速增重阶段的营养需求。",
            ]
            return AgentResult(success=True, answer="\n".join(lines), worker_name=self.name)
        except Exception as e:
            logger.error("growth_curve_agent direct call failed pig_id=%s: %s", pig_id, e, exc_info=True)
            return AgentResult(success=False, answer="生长曲线报告生成失败，请稍后再试。", worker_name=self.name, error=str(e))


# ============================================================
# BriefingAgent - 每日简报专属 Worker
# ============================================================

class BriefingAgent(WorkerAgent):
    """
    每日简报汇总智能体。
    负责全场生产指标、环境参数及异常事件的聚合与报告生成。
    """

    def __init__(self):
        system_prompt = """你是两头乌养殖场每日简报专家。
你负责汇总全场实时数据并生成日报。

## 必须遵守：
- **拒绝虚构**：你目前对农场今日情况一无所知！必须调用工具获取全场统计、环境和健康记录。
- **完整性**：简报必须涵盖全场概览、环境参数、异常猪只及管理建议。
- **数据来源**：仅使用工具返回的真实数据进行组织，严禁为了“美观”或“完整”而虚构模拟数据。"""

        super().__init__(name="BriefingAgent", system_prompt=system_prompt, tools=[])

    def get_tools(self) -> List[LCTool]:
        from v1.logic.bot_tools import list_tools
        all_tools = list_tools()
        tool_names = ["get_farm_stats", "query_env_status", "query_pig_health_records"]
        tools = []
        for name in tool_names:
            if name in all_tools:
                t = all_tools[name]
                tools.append(LCTool(
                    name=t.name,
                    description=t.description,
                    func=lambda x: "Sync execution not supported",
                    coroutine=t.handler
                ))
        return tools



    async def execute(self, context: AgentContext) -> AgentResult:
        if HAS_LANGCHAIN:
            return await self._execute_react(context)
        return await self._direct_tool_call(context)

    async def _execute_react(self, context: AgentContext) -> AgentResult:
        if not self.api_key:
            return AgentResult(success=False, answer="系统繁忙，请稍后再试。", worker_name=self.name, error="no api key")
        try:
            # 迁移到 DashScopeNativeChat
            llm = DashScopeNativeChat(model=self.model, api_key=self.api_key, temperature=0.2, max_tokens=4000)
            
            tools = self.get_tools()
            agent = create_react_agent(llm=llm, tools=tools, prompt=self._build_react_prompt())
            
            from v1.logic.central_agent_core import RichTraceHandler
            callbacks = [RichTraceHandler(client_id=context.client_id, agent_name=self.name)] if HAS_RICH else []
            
            executor = AgentExecutor(
                agent=agent,
                tools=tools,
                verbose=True,      # 开启调试日志
                handle_parsing_errors=True,
                max_iterations=8,
                return_intermediate_steps=True,
                callbacks=callbacks,
            )
            result = await executor.ainvoke({"input": self._build_input(context)})
            raw = result.get("output", "")
            answer = self._extract_final_answer(raw)
            steps = result.get("intermediate_steps", [])
            tool_outputs = [str(s[1]) for s in steps if len(s) >= 2]
            thoughts = [f"Action: {getattr(s[0], 'tool', '?')}" for s in steps if len(s) >= 2]
            return AgentResult(success=True, answer=answer or "今日简报生成完成。",
                worker_name=self.name, thoughts=thoughts, tool_outputs=tool_outputs)
        except Exception as e:
            logger.error("briefing_agent react failed: %s", e, exc_info=True)
            return await self._direct_tool_call(context)

    async def _direct_tool_call(self, context: AgentContext) -> AgentResult:
        """非 LangChain 环境下的报表拼接逻辑。"""
        from v1.logic.bot_tools import tool_get_farm_stats, tool_query_env_status, tool_query_pig_health_records
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        try:
            farm_raw = await tool_get_farm_stats("")
            env_raw = await tool_query_env_status("")
            health_raw = await tool_query_pig_health_records(json.dumps({"abnormal_only": True}, ensure_ascii=False))
            farm = json.loads(farm_raw) if farm_raw.strip().startswith("{") else {}
            env = json.loads(env_raw) if env_raw.strip().startswith("{") else {}
            health = json.loads(health_raw) if health_raw.strip().startswith("{") else {}
            total = farm.get("total_count") or farm.get("totalCount") or "--"
            health_rate = farm.get("health_rate") or farm.get("healthRate") or "--"
            avg_weight = farm.get("avg_weight") or farm.get("avgWeight") or "--"
            env_info = env.get("environment") or {}
            temp = env_info.get("temperature_c", "--")
            humidity = env_info.get("humidity_pct", "--")
            ammonia = env_info.get("ammonia_ppm", "--")
            vent = env_info.get("ventilation_status", "--")
            env_alerts = env.get("alerts") or []
            abnormal_pigs = health.get("abnormal_pigs") or []
            abnormal_count = len(abnormal_pigs)
            lines = [
                f"# {today} 两头乌养殖场智能诊断简报", "",
                "## 📊 整体概况",
                f"今日全场在栏 **{total}** 头，健康率 **{health_rate}**，平均体重约 **{avg_weight}** kg。",
                "",
                "## 🌡️ 环境监测",
                f"- **舍内温度**：{temp}°C",
                f"- **相对湿度**：{humidity}%",
                f"- **氨气浓度**：{ammonia} ppm",
                f"- **通风状态**：{vent}",
            ]
            if env_alerts and not str(env_alerts[0]).startswith("✅"):
                lines += ["", "> ⚠️ 环境预警：" + "；".join(str(a) for a in env_alerts)]
            lines += ["", "## 🏥 健康状况"]
            if abnormal_count == 0:
                lines.append("今日全场无异常个体，所有猪只健康状态良好。")
            else:
                lines.append(f"当前共发现 **{abnormal_count}** 头异常个体：")
                for p in abnormal_pigs:
                    pid = p.get("pig_id") or p.get("pigId", "--")
                    score = p.get("health_score") or p.get("healthScore", "--")
                    syms = ", ".join(p.get("symptoms") or [])
                    lines.append(f"- {pid}（健康评分 {score}）：{syms or '待评估'}")
            try:
                ammonia_high = float(str(ammonia).strip()) > 12
            except Exception:
                ammonia_high = False
            lines += [
                "", "## 🍽️ 饲养管理",
                "数据来源于今日 IoT 采集，建议参照正常采食量标准核对，出现偏差时及时调整。",
                "", "## ⚠️ 今日预警",
                f"异常个体数：**{abnormal_count}** 头。" if abnormal_count > 0 else "**无异常事件** — 今日全场运行平稳。",
                "", "## 💡 AI 建议",
                "1. " + (f"对 {abnormal_count} 头异常个体加强观察，必要时联系兽医。" if abnormal_count > 0 else "继续常规健康巡检，保持现有管理节奏。"),
                "2. " + ("加强猪舍通风，空气质量超标时应立即处理。" if ammonia_high else "当前空气质量正常，保持通风频率。"),
                "3. 定期消毒猪舍，保持饮水设施清洁，做好防疫记录。",
                "", "---",
                f"*本简报由两头乌智能养殖系统自动生成 | {now_str}*",
            ]
            return AgentResult(success=True, answer="\n".join(lines), worker_name=self.name)
        except Exception as e:
            logger.error("briefing_agent direct call failed: %s", e, exc_info=True)
            return AgentResult(success=False, answer="每日简报生成失败，请稍后再试。", worker_name=self.name, error=str(e))



class MultiAgentOrchestrator:
    """
    多智能体任务调度协调器。
    """
    
    def __init__(self):
        self.supervisor = SupervisorAgent()
        self.workers = {
            "vet_agent": VetAgent(),
            "data_agent": DataAgent(),
            "perception_agent": PerceptionAgent(),
            "growth_curve_agent": GrowthCurveAgent(),
            "briefing_agent": BriefingAgent(),
        }
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """
        执行多智能体协作全流程。
        
        流程节点：
        1. 意图路由。
        2. 专家智能体执行。
        3. 结果聚合与响应生成。
        """
        # 路由（传递是否有图片及音频）
        has_image = bool(context.image_urls)
        has_audio = bool(context.audio_path)
        worker_name = await self.supervisor.route(
            context.user_input, 
            has_image=has_image, 
            has_audio=has_audio,
            client_id=context.client_id
        )
        
        # 直接回复（不需要 Worker）
        if worker_name == "direct_reply":
            return await self._direct_reply(context)
        
        # 调用 Worker
        if worker_name in self.workers:
            worker = self.workers[worker_name]
            return await worker.execute(context)
        
        # 兜底
        logger.warning(f"未知 worker: {worker_name}")
        return AgentResult(
            success=False,
            answer="系统繁忙，请稍后再试。",
            error=f"未知 worker: {worker_name}"
        )
    
    async def _direct_reply(self, context: AgentContext) -> AgentResult:
        """处理非任务型请求（如问候、通用咨询）的直接回复逻辑。"""
        from v1.logic.agent_debug_controller import push_debug_event
        await push_debug_event("thought", {"content": "检测到非业务类指令，正在准备友好回复..."}, context.client_id, agent="Supervisor", status="工作中")
        
        if not HAS_OPENAI:
            return AgentResult(
                success=True,
                answer="您好，有什么可以帮您的吗？",
                worker_name="direct_reply"
            )
        
        try:
            api_key, base_url, model, omni_model = self.supervisor._get_llm_config()
            
            # 使用流式驱动以输出实时 Token
            llm = DashScopeNativeChat(
                model=model,
                api_key=api_key,
                temperature=0.7,
                max_tokens=200,
                streaming=True
            )
            
            from langchain_core.messages import SystemMessage, HumanMessage
            messages = [
                SystemMessage(content="你是友好的助手。回复简短：1-2句，每句不超过20字。"),
                HumanMessage(content=context.user_input)
            ]
            
            from v1.logic.central_agent_core import RichTraceHandler
            handler = RichTraceHandler(client_id=context.client_id, agent_name="Supervisor", enable_filter=False)
            
            result = await llm.agenerate([messages], callbacks=[handler])
            answer = result.generations[0][0].message.content.strip()
            
            await push_debug_event("final_answer", {"answer": answer}, context.client_id, agent="Supervisor")
            
            return AgentResult(
                success=True,
                answer=answer,
                worker_name="direct_reply"
            )
            
        except Exception as e:
            logger.error(f"直接回复失败: {e}")
            return AgentResult(
                success=True,
                answer="您好，有什么可以帮您的吗？",
                worker_name="direct_reply"
            )
