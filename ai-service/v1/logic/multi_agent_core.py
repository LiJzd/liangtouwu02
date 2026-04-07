"""
多智能体架构核心 - Supervisor + Worker 模式
==========================================

本模块实现了基于意图路由的多智能体协作系统，采用经典的 Supervisor-Worker 架构。

架构设计：
┌─────────────────────────────────────────────────────────┐
│                    用户输入                              │
│              (文本 + 可选图片)                           │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │  SupervisorAgent      │  ← 意图路由中心
         │  (意图识别与分发)      │
         └───────────┬───────────┘
                     │
         ┌───────────┼───────────┐
         │           │           │
         ▼           ▼           ▼
    ┌────────┐  ┌────────┐  ┌────────┐
    │VetAgent│  │DataAgent│ │Perception│  ← 专家Worker
    │兽医诊断│  │数据查询│  │视觉识别│
    └────────┘  └────────┘  └────────┘
         │           │           │
         └───────────┼───────────┘
                     │
                     ▼
              ┌─────────────┐
              │  最终答案    │
              └─────────────┘

核心组件：
1. SupervisorAgent：意图路由器
   - 分析用户输入，判断需要哪个专家处理
   - 支持基于LLM的智能路由和基于规则的降级路由
   - 多模态支持：检测到图片时自动路由到兽医Agent

2. WorkerAgent：专家基类
   - 定义了所有专家Agent的通用接口
   - 实现了标准的ReAct推理循环
   - 提供工具调用、结果提取等通用功能

3. 具体Worker实现：
   - VetAgent：兽医诊断专家（支持多模态图片问诊）
   - DataAgent：数据查询专家（猪只档案、生长曲线）
   - PerceptionAgent：视觉识别专家（视频监控分析）

4. MultiAgentOrchestrator：协调器
   - 统一的多智能体执行入口
   - 管理所有Worker实例
   - 处理路由和结果返回

技术特性：
- ReAct推理：Thought → Action → Observation 循环
- 工具链调用：每个Worker有专属的工具集
- 多模态支持：文本 + 图片混合输入
- 降级机制：LLM不可用时自动切换到规则引擎
- Rich美化：终端输出带颜色和格式化
- 调试支持：集成SSE调试流，实时查看推理过程

使用示例：
    # 创建协调器
    orchestrator = MultiAgentOrchestrator()
    
    # 构建上下文
    context = AgentContext(
        user_id="user_001",
        user_input="查询猪只LTW-001的生长曲线",
        chat_history=[],
        metadata={},
        client_id="web_client_001"
    )
    
    # 执行
    result = await orchestrator.execute(context)
    print(result.answer)
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

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

try:
    from langchain.agents import create_react_agent, AgentExecutor
    from langchain_core.callbacks import BaseCallbackHandler
    from langchain_core.prompts import PromptTemplate
    from langchain_core.tools import Tool as LCTool
    from langchain_openai import ChatOpenAI
    HAS_LANGCHAIN = True
except Exception:
    BaseCallbackHandler = object  # type: ignore[assignment]
    HAS_LANGCHAIN = False

try:
    from openai import OpenAI
    HAS_OPENAI = True
except Exception:
    HAS_OPENAI = False


# ============================================================
# 数据结构定义
# ============================================================

@dataclass
class AgentContext:
    """
    Agent执行上下文
    
    封装了Agent执行所需的所有输入信息，包括用户输入、历史对话、元数据等。
    
    Attributes:
        user_id: 用户唯一标识符
        user_input: 用户当前输入的文本
        chat_history: 历史对话记录列表（每条记录包含role和content）
        metadata: 额外的元数据（如pig_id等）
        client_id: 客户端标识符（用于SSE调试流）
        image_urls: 多模态图片URL列表（可选，用于图片问诊）
    """
    user_id: str
    user_input: str
    chat_history: list
    metadata: dict
    client_id: str = "default"
    image_urls: Optional[List[str]] = None  # 多模态图片URL列表


@dataclass
class AgentResult:
    """
    Agent执行结果
    
    封装了Agent执行后的所有输出信息，包括答案、思考过程、工具调用记录等。
    
    Attributes:
        success: 执行是否成功
        answer: 最终答案（返回给用户的文本）
        worker_name: 执行该任务的Worker名称（可选）
        thoughts: 思考过程列表（ReAct的Thought步骤）
        tool_outputs: 工具调用输出列表（ReAct的Observation步骤）
        error: 错误信息（如果执行失败）
        image: Base64编码的图片（可选，用于返回生成的图片）
        metadata: 额外的元数据（如执行模式、工具调用次数等）
    """
    success: bool
    answer: str
    worker_name: Optional[str] = None
    thoughts: List[str] = None
    tool_outputs: List[str] = None
    error: Optional[str] = None
    image: Optional[str] = None  # Base64 编码的图片
    metadata: Optional[dict] = None  # 额外的元数据

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
    """意图路由 Agent"""
    
    def __init__(self):
        self.api_key, self.base_url, self.model = self._get_llm_config()
    
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
        return api_key, base_url, model
    
    def route(self, user_input: str, has_image: bool = False) -> str:
        """
        路由用户请求到合适的 Worker
        
        Args:
            user_input: 用户文本输入
            has_image: 是否包含图片（多模态问诊）
        
        Returns:
            worker_name: vet_agent, data_agent, perception_agent, 或 direct_reply
        """
        # 有图片时直接路由到兽医Agent进行视觉诊断
        if has_image:
            if HAS_RICH and console:
                console.print(Panel(
                    Text(f"检测到图片，直接路由到: vet_agent (多模态问诊)", style="bold cyan"),
                    title="[bold magenta]🎯 Supervisor 决策 (多模态)[/]",
                    border_style="magenta"
                ))
            else:
                logger.info(f"Supervisor 路由: 检测到图片 -> vet_agent (多模态问诊)")
            return "vet_agent"
        
        if not HAS_OPENAI or not self.api_key:
            # 降级到规则引擎
            return self._rule_based_route(user_input)
        
        try:
            client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            prompt = SUPERVISOR_PROMPT.format(user_input=user_input)
            
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,  # 低温度，确保路由稳定
                max_tokens=50,
            )
            
            worker_name = response.choices[0].message.content.strip().lower()
            
            # 验证返回值
            valid_workers = ["vet_agent", "data_agent", "perception_agent", "growth_curve_agent", "briefing_agent", "direct_reply"]
            if worker_name not in valid_workers:
                logger.warning(f"Supervisor 返回无效 worker: {worker_name}，降级到规则引擎")
                return self._rule_based_route(user_input)
            
            if HAS_RICH and console:
                console.print(Panel(
                    Text(f"路由到: {worker_name}", style="bold cyan"),
                    title="[bold magenta]🎯 Supervisor 决策[/]",
                    border_style="magenta"
                ))
            else:
                logger.info(f"Supervisor 路由: {user_input[:50]} -> {worker_name}")
            
            return worker_name
            
        except Exception as e:
            logger.error(f"Supervisor 路由失败: {e}，降级到规则引擎")
            return self._rule_based_route(user_input)
    
    def _rule_based_route(self, user_input: str) -> str:
        """规则引擎兜底路由"""
        text = user_input.lower()

        # 每日简报关键词（优先最高）
        briefing_keywords = [
            "每日简报", "日报", "今日简报", "全场简报", "每日诊断简报",
            "farm_daily_briefing", "daily_briefing", "briefing",
            "全场报告", "场内简报", "日常巡检汇总",
        ]
        if any(k in text for k in briefing_keywords):
            return "briefing_agent"

        # 生长曲线关键词（单只猪分析）
        growth_curve_keywords = [
            "生长曲线", "生长曲线报告", "growth_curve", "growth curve",
            "体重预测", "月增重", "生长分析", "喂食趋势", "饮水趋势",
            "日增重", "生长预测",
        ]
        if any(k in text for k in growth_curve_keywords):
            return "growth_curve_agent"

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
            return "data_agent"

        # 视觉识别关键词
        perception_keywords = [
            "图片", "照片", "视频", "监控", "摄像", "现场", "情况",
            "状态", "截图", "识别", "检测", "看看", "看下"
        ]
        if any(k in text for k in perception_keywords):
            return "perception_agent"

        # 默认直接回复
        return "direct_reply"


# ============================================================
# Worker Agent 基类
# ============================================================

class WorkerAgent(ABC):
    """Worker Agent 抽象基类"""
    
    def __init__(self, name: str, system_prompt: str, tools: List[LCTool]):
        self.name = name
        self.system_prompt = system_prompt
        self.tools = tools
        self.api_key, self.base_url, self.model = self._get_llm_config()
    
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
        return api_key, base_url, model
    
    @abstractmethod
    def get_tools(self) -> List[LCTool]:
        """获取该 Worker 可用的工具"""
        pass
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """
        执行 Worker 的 ReAct 循环
        
        Args:
            context: 执行上下文
        
        Returns:
            AgentResult: 执行结果
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
            # 显示 Worker 启动
            if HAS_RICH and console:
                console.print(Panel(
                    Text(f"Worker: {self.name}\n任务: {context.user_input}", style="white"),
                    title=f"[bold green]🤖 {self.name.upper()} 启动[/]",
                    border_style="green"
                ))
            
            # 构建 LLM
            try:
                llm = ChatOpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url,
                    model=self.model,
                    temperature=0.1,
                    max_tokens=500,
                )
            except TypeError:
                llm = ChatOpenAI(
                    openai_api_key=self.api_key,
                    openai_api_base=self.base_url,
                    model=self.model,
                    temperature=0.1,
                    max_tokens=500,
                )
            
            # 获取工具
            tools = self.get_tools()
            
            # 标准 ReAct 流程
            # 构建 ReAct 提示词
            react_prompt = self._build_react_prompt()
            
            # 创建 Agent
            agent = create_react_agent(llm=llm, tools=tools, prompt=react_prompt)
            
            # 创建 Executor
            from v1.logic.central_agent_core import RichTraceHandler
            callbacks = [RichTraceHandler(client_id=context.client_id)] if HAS_RICH else []
            
            # 添加日志确认 callbacks 被创建
            logger.info(f"创建 AgentExecutor，callbacks 数量: {len(callbacks)}")
            
            agent_executor = AgentExecutor(
                agent=agent,
                tools=tools,
                verbose=True,  # 改为 True 以触发回调
                handle_parsing_errors=True,
                max_iterations=3,
                return_intermediate_steps=True,
                callbacks=callbacks,
            )
            
            # 构建输入
            input_text = self._build_input(context)
            
            # 执行
            result = await agent_executor.ainvoke({"input": input_text})
            
            # 提取结果
            raw_output = result.get("output", "")
            clean_output = self._extract_final_answer(raw_output)
            
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
        """构建 ReAct 提示词模板"""
        template = f"""{self.system_prompt}

你可以使用以下工具：

{{tools}}

严格按照以下格式进行推理和行动（格式不能有任何偏差）：

Question: 用户的问题
Thought: 你应该思考要做什么
Action: 要采取的行动，必须是 [{{tool_names}}] 中的一个
Action Input: 行动的输入参数（JSON 格式）
Observation: 行动的结果
... (这个 Thought/Action/Action Input/Observation 可以重复N次)
Thought: 我现在知道最终答案了
Final Answer: 对原始问题的最终答案

⚠️ 绝对不可违反的格式规则：
1. 每次输出只能是 "Thought: + Action: + Action Input:" 或者 "Thought: + Final Answer:" 二选一
2. "Final Answer:" 这个前缀绝对不能省略！答案必须紧跟在 "Final Answer:" 后面
3. 正确示例：
   Thought: 我现在知道最终答案了
   Final Answer: 🌡️ 环境正常...💊 建议...
4. 错误示例（绝对禁止）：
   Thought: 我现在知道最终答案了
   🌡️ 环境正常...（❌ 缺少 Final Answer: 前缀！）
5. Action 必须是工具列表中的一个，不能自己编造
6. 使用表情符号让回答更友好

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
    
    def _extract_final_answer(self, agent_output: str) -> str:
        """提取 Final Answer（增强版，能从多种格式中提取有用答案）"""
        if not agent_output:
            return ""
        
        # 1. 标准提取：匹配 Final Answer: 前缀
        match = re.search(r"Final Answer:\s*(.+)", agent_output, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        # 2. 模式匹配：LLM 忘了写 Final Answer: 但内容带有诊断格式标记
        emoji_markers = ["🌡️", "🔍", "💊", "⚠️", "✅", "❌"]
        if any(marker in agent_output for marker in emoji_markers):
            lines = [line.strip() for line in agent_output.split('\n') if line.strip()]
            # 提取包含表情符号的行和紧随其后的行
            useful_lines = []
            for line in lines:
                if any(marker in line for marker in emoji_markers):
                    useful_lines.append(line)
                elif useful_lines and not any(m in line for m in ["Thought:", "Action:", "Observation:", "Question:", "Action Input:", "Invalid Format"]):
                    useful_lines.append(line)
            if useful_lines:
                return "\n".join(useful_lines)
        
        # 3. 过滤思考过程标记，取所有非标记行
        lines = [line.strip() for line in agent_output.split('\n') if line.strip()]
        react_markers = ["Thought:", "Action:", "Observation:", "Question:", "Action Input:", "Invalid Format", "Agent stopped"]
        filtered = [
            line for line in lines 
            if not any(marker in line for marker in react_markers)
        ]
        if filtered:
            return "\n".join(filtered)  # 保留全部有意义内容，不再限制为最后5行
        
        return agent_output.strip()


# ============================================================
# 具体 Worker 实现
# ============================================================

class VetAgent(WorkerAgent):
    """兽医诊断专家（支持多模态图片问诊 + 强制工具链诊断）"""
    
    def __init__(self):
        system_prompt = """你是资深的畜牧兽医专家，专注于两头乌生猪的疾病诊断和健康管理。

## 强制诊断流程（必须严格遵守，禁止跳过任何步骤）

你必须按照以下固定步骤完成诊断，**每一步都必须调用对应的工具**：

### Step 1 - 环境排查
调用 query_env_status 获取猪场当前环境数据（温湿度、氨气、通风等）。
分析环境因素是否可能导致或加重病情。

### Step 2 - 知识库检索
调用 query_pig_disease_rag 查询两头乌病症知识库。
根据用户描述的症状，检索可能的疾病及治疗方案。

### Step 3 - 历史病例比对
调用 query_similar_cases 查询历史相似病例。
看看以前类似情况是怎么处理的，结果如何。

### Step 4 - 网页端告警发布与语音播报（强制执行）
**重要：对于所有异常情况（包括模拟异常），你必须调用 publish_alert 工具！**
- 如果用户输入中包含"模拟事件"、"建议 publish_alert 参数"等关键词，说明这是一个需要发布告警的异常事件
- 如果你判定当前生猪或环境存在明确异常（如生病、发热、指标超标），必须调用此工具
- 只有当你确认这是普通问答（没有任何异常）时，才能跳过此步
- 调用时使用用户提供的参数草稿，或根据你的分析结果构建参数

### Step 5 - 综合诊断
基于排查收集到的真实数据，分析原因并给出最终的诊断结论。

## 严格约束（违反将被系统拒绝）
- ⚠️ 你必须调用至少 2 个工具后才能给出 Final Answer
- ⚠️ 禁止在没有调用工具的情况下直接编造诊断结果
- ⚠️ Final Answer 中必须引用工具返回的具体数据作为诊断依据

## 输出要求
- 极度通俗化，避免专业术语，像跟老乡面对面聊天
- 使用表情符号分段（🌡️ 💊 ⚠️ 等）
- 称呼用"老乡/师傅"
- 回复控制在 3-5 句话
- 格式示例：
  🌡️ 环境：舍温XX度，正常/偏高
  🔍 判断：根据XX症状，可能是XX病
  💊 建议：先XXX，再XXX
  ⚠️ 注意：如果XX，要联系畜牧局"""
        
        super().__init__(name="vet_agent", system_prompt=system_prompt, tools=[])
    
    def get_tools(self) -> List[LCTool]:
        """兽医 Agent 可用的全部诊断工具"""
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
    

    async def execute(self, context: AgentContext) -> AgentResult:
        """
        执行兽医诊断。
        有图片时走二阶段流程（视觉分析→工具链），无图片走标准 ReAct。
        """
        if context.image_urls:
            return await self._execute_multimodal_two_stage(context)
        
        # 纯文本模式：直接走增强版 ReAct（已在 system_prompt 中强制 CoT）
        return await self._execute_with_more_iterations(context)
    
    async def _execute_with_more_iterations(self, context: AgentContext) -> AgentResult:
        """增加迭代次数的 ReAct 执行（需要更多轮工具调用）"""
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
            if HAS_RICH and console:
                console.print(Panel(
                    Text(f"执行单元: {self.name}\n任务内容: {context.user_input}", style="white"),
                    title=f"[bold green]🤖 {self.name.upper()} 智能助手启动[/]",
                    border_style="green"
                ))
            
            # 构建 LLM（增加 max_tokens 以支持多步推理）
            try:
                llm = ChatOpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url,
                    model=self.model,
                    temperature=0.1,
                    max_tokens=800,
                )
            except TypeError:
                llm = ChatOpenAI(
                    openai_api_key=self.api_key,
                    openai_api_base=self.base_url,
                    model=self.model,
                    temperature=0.1,
                    max_tokens=800,
                )
            
            tools = self.get_tools()
            react_prompt = self._build_react_prompt()
            agent = create_react_agent(llm=llm, tools=tools, prompt=react_prompt)
            
            from v1.logic.central_agent_core import RichTraceHandler
            callbacks = [RichTraceHandler(client_id=context.client_id)] if HAS_RICH else []
            
            agent_executor = AgentExecutor(
                agent=agent,
                tools=tools,
                verbose=False,
                handle_parsing_errors=True,
                max_iterations=8,      # 增加到8次：3次工具调用 + 格式重试余量 + Final Answer
                return_intermediate_steps=True,
                callbacks=callbacks,
            )
            
            input_text = self._build_input(context)
            try:
                result = await agent_executor.ainvoke({"input": input_text})
            except Exception as e:
                import logging
                logging.getLogger("multi_agent_core").error(f"ReAct Exception: {e}")
                
                # 兜底容错返回
                raw_output = f"[系统保护强制接管] 诊断执行异常，错误详情：{str(e)[:150]}... 请尝试精简提问。"
                return AgentResult(
                    text=raw_output,
                    tools_called=["publish_alert"] if "publish_alert" in input_text else [],
                    confidence=0.5
                )
            
            raw_output = result.get("output", "")
            clean_output = self._extract_final_answer(raw_output)
            
            intermediate_steps = result.get("intermediate_steps", [])
            tool_outputs = []
            thoughts = []
            
            for step in intermediate_steps:
                if len(step) >= 2:
                    action, observation = step[0], step[1]
                    tool_name = getattr(action, "tool", "unknown")
                    tool_input = getattr(action, "tool_input", "")
                    thoughts.append(f"Action: {tool_name}")
                    thoughts.append(f"Action Input: {tool_input}")
                    tool_outputs.append(str(observation))
                    thoughts.append(f"Observation: {observation}")
            
            # 如果 AgentExecutor 超限但中间步骤有有用内容，尝试从 _Exception 中提取
            if (not clean_output or "Agent stopped" in raw_output) and intermediate_steps:
                logger.warning("AgentExecutor 超限，尝试从中间步骤提取答案")
                for step in reversed(intermediate_steps):
                    if len(step) >= 2:
                        observation = str(step[1])
                        # _Exception 的 observation 中包含 LLM 生成的完整答案
                        extracted = self._extract_final_answer(observation)
                        if extracted and len(extracted) > 20:
                            clean_output = extracted
                            logger.info(f"成功从中间步骤提取答案，长度: {len(clean_output)}")
                            break
            
            # 检查是否调用了足够的工具
            tool_count = len([t for t in thoughts if t.startswith("Action: ") and not t.startswith("Action: _Exception")])
            if tool_count < 2:
                logger.warning(f"VetAgent 只调用了 {tool_count} 个工具，不满足最低要求")
            
            return AgentResult(
                success=True,
                answer=clean_output if clean_output else "诊断完成。",
                worker_name=self.name,
                thoughts=thoughts,
                tool_outputs=tool_outputs,
                metadata={"tool_calls": tool_count, "mode": "react_cot"}
            )
            
        except Exception as e:
            logger.error(f"{self.name} 执行失败: {e}", exc_info=True)
            return AgentResult(
                success=False,
                answer="诊断过程出了点问题，老乡您再说一遍症状，我重新帮您看。",
                worker_name=self.name,
                error=str(e)
            )
    
    async def _execute_multimodal_two_stage(self, context: AgentContext) -> AgentResult:
        """
        二阶段多模态诊断：
        阶段1：立即调用视觉模型分析图片（趁URL未过期），提取观察到的症状
        阶段2：将视觉分析结果作为症状描述，走 ReAct 工具链进行交叉验证和综合诊断
        """
        import os
        settings = get_settings()
        
        api_key = os.environ.get("DASHSCOPE_API_KEY") or settings.dashscope_api_key
        base_url = (
            os.environ.get("DASHSCOPE_BASE_URL")
            or settings.dashscope_base_url
            or "https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        vl_model = os.environ.get("DASHSCOPE_VL_MODEL") or settings.dashscope_vl_model or "qwen-vl-max"
        
        if not HAS_OPENAI or not api_key:
            return AgentResult(
                success=False,
                answer="系统繁忙，暂时无法进行图片诊断。",
                worker_name=self.name,
                error="缺少 API Key 或 OpenAI 客户端不可用"
            )
        
        # ============================================================
        # 阶段 1: 视觉分析（尽早调用，防止图片URL过期）
        # ============================================================
        visual_analysis = ""
        try:
            if HAS_RICH and console:
                console.print(Panel(
                    Text(f"🖼️ 二阶段诊断 - 阶段1: 视觉分析\n模型: {vl_model}\n图片数: {len(context.image_urls)}", style="white"),
                    title=f"[bold green]🔬 VET_AGENT 阶段1: 视觉识别[/]",
                    border_style="green"
                ))
            
            # 视觉分析专用提示词：只提取客观观察，不做最终诊断
            visual_prompt = (
                "你是一名经验丰富的兽医助理，你的任务是仔细观察图片并**客观描述**你看到的情况。\n"
                "请按以下格式输出你的观察结果：\n\n"
                "【外观】描述猪的毛色、皮肤状况、体型\n"
                "【病灶】是否有红肿、溃疡、出血、皮疹等\n"
                "【姿态】站立/趴卧/行走姿态是否正常\n"
                "【精神】精神状态是否活泼或萎靡\n"
                "【疑似症状】列出你观察到的异常症状关键词\n\n"
                "注意：只描述你看到的，不要给出诊断结论。诊断将由后续步骤完成。"
            )
            
            user_content = []
            if context.user_input:
                user_content.append({"type": "text", "text": f"用户描述：{context.user_input}\n请分析以下图片："})
            else:
                user_content.append({"type": "text", "text": "请分析以下猪只图片的状况："})
            
            for url in context.image_urls:
                user_content.append({
                    "type": "image_url",
                    "image_url": {"url": url}
                })
            
            messages = [
                {"role": "system", "content": visual_prompt},
                {"role": "user", "content": user_content}
            ]
            
            logger.info(f"阶段1: 调用 {vl_model} 进行视觉分析，图片数: {len(context.image_urls)}")
            
            client = OpenAI(api_key=api_key, base_url=base_url)
            response = client.chat.completions.create(
                model=vl_model,
                messages=messages,
                temperature=0.2,
                max_tokens=400,
            )
            
            visual_analysis = response.choices[0].message.content.strip()
            
            if HAS_RICH and console:
                console.print(Panel(
                    Text(visual_analysis, style="white"),
                    title="[bold cyan]📋 阶段1完成: 视觉观察结果[/]",
                    border_style="cyan"
                ))
            
            logger.info(f"阶段1完成，视觉分析: {visual_analysis[:200]}")
            
        except Exception as e:
            logger.error(f"阶段1视觉分析失败: {e}", exc_info=True)
            visual_analysis = f"图片分析失败（{str(e)[:50]}），将基于用户文字描述进行诊断"
        
        # ============================================================
        # 阶段 2: 工具链交叉验证（用视觉分析结果 + 用户描述走 ReAct）
        # ============================================================
        try:
            if HAS_RICH and console:
                console.print(Panel(
                    Text(f"🔗 二阶段诊断 - 阶段2: 工具链交叉验证\n将基于视觉分析结果调用诊断工具", style="white"),
                    title=f"[bold green]🔬 VET_AGENT 阶段2: 工具链诊断[/]",
                    border_style="green"
                ))
            
            # 构造增强的用户输入（视觉分析 + 用户原始描述）
            enhanced_input = f"用户发来了一张猪的照片。\n\n"
            if context.user_input:
                enhanced_input += f"用户描述：{context.user_input}\n\n"
            enhanced_input += f"图片视觉分析结果：\n{visual_analysis}\n\n"
            enhanced_input += "请根据以上信息，按照强制诊断流程（环境排查→知识库→历史病例）进行综合诊断。"
            
            # 创建一个新的上下文（不含图片，走纯文本 ReAct）
            text_context = AgentContext(
                user_id=context.user_id,
                user_input=enhanced_input,
                chat_history=context.chat_history,
                metadata=context.metadata,
                client_id=context.client_id,
                image_urls=None,  # 阶段2不需要图片了
            )
            
            # 走增强版 ReAct 工具链
            react_result = await self._execute_with_more_iterations(text_context)
            
            # 合并元数据
            react_result.metadata = react_result.metadata or {}
            react_result.metadata["multimodal"] = True
            react_result.metadata["vl_model"] = vl_model
            react_result.metadata["visual_analysis"] = visual_analysis[:200]
            react_result.thoughts = [f"阶段1: 视觉分析 ({vl_model})"] + (react_result.thoughts or [])
            
            return react_result
            
        except Exception as e:
            logger.error(f"阶段2工具链诊断失败: {e}", exc_info=True)
            # 降级：如果阶段2失败，至少返回阶段1的视觉分析结果
            if visual_analysis and "失败" not in visual_analysis:
                return AgentResult(
                    success=True,
                    answer=f"老乡，我看了照片的情况：\n{visual_analysis}\n\n💊 建议先隔离观察，如症状加重请联系当地兽医站。",
                    worker_name=self.name,
                    thoughts=[f"阶段1视觉分析完成，阶段2工具链失败，降级输出"],
                    metadata={"multimodal": True, "degraded": True}
                )
            return AgentResult(
                success=False,
                answer="图片分析暂时失败了，老乡您先用文字描述一下猪的情况，我来帮您判断。",
                worker_name=self.name,
                error=str(e)
            )


class DataAgent(WorkerAgent):
    """数据查询专家"""
    
    def __init__(self):
        system_prompt = """你是数据查询专家，负责猪只档案查询和生长预测。

你的任务：
1. 查询猪只列表和档案信息
2. 生成生长曲线预测
3. 统计数据分析

输出要求：
- 数据准确，不编造
- 格式清晰，易于理解
- 回复简短：1-3句"""
        
        system_prompt += """

濡傛灉鐢ㄦ埛鏄庣‘瑕佲€滅敓闀挎洸绾挎姤鍛娾€濄€侀娴嬫姤鍛娿€佹湀搴︿綋閲嶈〃鏍硷紝鎴栬€呰姹備綘杈撳嚭鍏煎鍓嶇鐨勭粨鏋滐紝鍒欏繀椤绘敼鐢ㄤ互涓嬬壒鍒鍒欙細
- 蹇呴』鍏堣皟鐢?get_pig_info_by_id锛屽啀璋冪敤 query_pig_growth_prediction
- 鍗虫椂宸ュ叿杩斿洖 JSON锛屼篃蹇呴』鑷繁鏁寸悊鎴?Markdown锛屼笉鑳界洿鎺ヨ创鍘熷 JSON
- 鏈€缁堝洖澶嶅繀椤诲寘鍚簿纭爣棰橈細### 棰勬祴鐢熼暱鏇茬嚎鏁版嵁 (Monthly)
- 鏈€缁堝洖澶嶅繀椤诲寘鍚〃鏍硷紝琛ㄥご蹇呴』鏄細| 鏈堜唤 (Month) | 鎷熷悎/棰勬祴浣撻噸 (kg) | 鐘舵€? |
- 琛ㄦ牸绗竴鍒楀彧鑳藉啓鏁板瓧鏈堜唤锛岀浜屽垪鍙兘鍐欐暟瀛椾綋閲嶏紝绗笁鍒楀啓鈥滃綋鍓嶁€濇垨鈥滈娴嬧€濈瓑鐘舵€佽鏄?
- 杩欑鎶ュ憡鍦烘櫙涓嶅啀闄愬埗 1-3 鍙ヨ瘽锛屼互鎶ュ憡瀹屾暣鎬т负浼樺厛"""

        super().__init__(name="data_agent", system_prompt=system_prompt, tools=[])
    
    def get_tools(self) -> List[LCTool]:
        """数据 Agent 可用的工具"""
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
    """视觉识别专家"""
    
    def __init__(self):
        system_prompt = """你是视觉识别专家，负责分析猪场监控图像。

你的任务：
1. 使用 capture_pig_farm_snapshot 工具截取并分析猪场视频画面
2. 根据工具返回的检测结果，向用户报告猪场情况
3. 如果检测到猪只，说明数量和状态
4. 如果未检测到猪只，提醒用户可能的原因（盲区、趴卧、设备问题等）

重要提示：
- 工具返回的 "summary" 字段包含检测结果摘要
- "detection_count" 表示检测到的猪只数量
- 即使 detection_count 为 0，也要给出友好的回复，不要说"无法查看"或"技术难题"
- 回复要简短友好，1-3句话，使用表情符号

输出要求：
- 描述清晰具体
- 突出异常情况
- 回复简短：1-3句"""
        
        super().__init__(name="perception_agent", system_prompt=system_prompt, tools=[])
    
    def get_tools(self) -> List[LCTool]:
        """视觉 Agent 可用的工具"""
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
    """生长曲线分析专家（专为生长曲线页面设计，输出含两张标准表格的 Markdown 报告）"""

    def __init__(self):
        system_prompt = """你是生长曲线分析专家，专门为两头乌猪只生成标准生长曲线报告。

执行流程（必须严格按顺序，禁止跳过）：
1. 调用 get_pig_info_by_id 查询猪只档案，获取 lifecycle 数据（含喂食/饮水记录）。
2. 调用 query_pig_growth_prediction 获取该猪只的预测生长轨迹。
3. 综合两步结果，输出严格格式的报告。

输出格式（必须完整，缺少任何一个标题将被判为格式错误）：

## 基本信息
- **猪只ID**：（填被查询的猪只ID）
- **品种**：（从工具结果填写）
- **当前月龄**：（填数字）月
- **当前体重**：（填数字）kg

## 生长趋势分析
（2到4条简短的预测结论和建议）

### 历史实测数据 (Historical)
| 月份 | 实测体重(kg) | 喂食次数 | 喂食时长(min) | 饮水次数 | 饮水时长(min) |
| --- | --- | --- | --- | --- | --- |
（从 get_pig_info_by_id 返回的 lifecycle 字段逐月填写）

### 预测生长曲线数据 (Monthly)
| 月份 (Month) | 拟合/预测体重 (kg) | 状态 |
| --- | --- | --- |
（从 query_pig_growth_prediction 获取，历史月份标"已记录"，未来月份标"预测"，当前月标"当前"）

## AI 建议
（3条针对该猪只当前状态的具体建议，结合喂食/饮水数据给出）

严格约束：
- 必须同时输出以上两个表格，缺一不可。
- 不要返回 JSON 格式内容。所有数字列只写纯数字，不含单位。
- 回复全程使用中文，以完整报告为优先。"""

        super().__init__(name="growth_curve_agent", system_prompt=system_prompt, tools=[])

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
            try:
                llm = ChatOpenAI(api_key=self.api_key, base_url=self.base_url, model=self.model, temperature=0.1, max_tokens=3000)
            except TypeError:
                llm = ChatOpenAI(openai_api_key=self.api_key, openai_api_base=self.base_url, model=self.model, temperature=0.1, max_tokens=3000)
            tools = self.get_tools()
            agent = create_react_agent(llm=llm, tools=tools, prompt=self._build_react_prompt())
            from v1.logic.central_agent_core import RichTraceHandler
            callbacks = [RichTraceHandler(client_id=context.client_id)] if HAS_RICH else []
            executor = AgentExecutor(agent=agent, tools=tools, verbose=False,
                handle_parsing_errors=True, max_iterations=6, return_intermediate_steps=True, callbacks=callbacks)
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
        """LangChain 不可用时的降级路径"""
        from v1.logic.bot_tools import tool_get_pig_info_by_id, tool_query_pig_growth_prediction
        meta_pig_id = str((context.metadata or {}).get("pig_id", "")).strip()
        match = re.search(r"\b(?:PIG|LTW)[-_]?\d+\b", context.user_input or "", re.IGNORECASE)
        pig_id = meta_pig_id or (match.group(0) if match else "")
        if not pig_id:
            return AgentResult(success=False, answer="缺少猪只编号，无法生成生长曲线报告。", worker_name=self.name, error="missing pig_id")
        try:
            pig_raw = await tool_get_pig_info_by_id(json.dumps({"pig_id": pig_id}, ensure_ascii=False))
            pig_info = json.loads(pig_raw) if pig_raw.strip().startswith("{") else {}
            growth_raw = await tool_query_pig_growth_prediction(json.dumps({"pig_id": pig_id}, ensure_ascii=False))
            growth_data = json.loads(growth_raw) if growth_raw.strip().startswith("{") else {}
            breed = pig_info.get("breed", "两头乌")
            current_month = pig_info.get("current_month") or pig_info.get("currentMonth") or 0
            current_weight = pig_info.get("current_weight_kg") or pig_info.get("currentWeightKg") or 0.0
            lifecycle = pig_info.get("lifecycle") or []
            hist_rows = []
            for d in lifecycle:
                m = d.get("month") or d.get("monthIndex", 0)
                w = d.get("weight_kg") or d.get("weightKg") or d.get("weight", 0)
                fc = d.get("feed_count") or d.get("feedCount", 0)
                fd = d.get("feed_duration_mins") or d.get("feedDurationMins", 0)
                wc = d.get("water_count") or d.get("waterCount", 0)
                wd = d.get("water_duration_mins") or d.get("waterDurationMins", 0)
                hist_rows.append(f"| {m} | {w} | {fc} | {fd} | {wc} | {wd} |")
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
                "| 月份 | 实测体重(kg) | 喂食次数 | 喂食时长(min) | 饮水次数 | 饮水时长(min) |",
                "| --- | --- | --- | --- | --- | --- |",
                *hist_rows,
                "",
                "### 预测生长曲线数据 (Monthly)",
                "| 月份 (Month) | 拟合/预测体重 (kg) | 状态 |",
                "| --- | --- | --- |",
                *pred_rows,
                "",
                "## AI 建议",
                "1. 对照预测曲线持续记录实测体重，偏差超过 5kg 时重新评估饲喂方案。",
                "2. 关注喂食次数与饮水时长变化，若出现异常下降，建议检查猪只健康状态。",
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
    """每日简报专家（汇总全场健康、环境、饲养数据，生成 Markdown 日报）"""

    def __init__(self):
        system_prompt = """你是两头乌养殖场智能日报生成专家，每日汇总全场状态并生成结构化简报。

执行流程（必须全部调用，禁止编造数据）：
1. 调用 get_farm_stats 获取全场猪只统计概览。
2. 调用 query_env_status 获取当前环境数据。
3. 调用 query_pig_health_records 传入 abnormal_only=true 获取异常猪只列表。
4. 综合以上数据，生成完整每日简报。

输出格式（Markdown）：
# （填入今日日期） 两头乌养殖场智能诊断简报
## 📊 整体概况
（在栏总数、健康率、平均体重等核心指标）
## 🌡️ 环境监测
（温湿度、氨气浓度、通风状态）
## 🏥 健康状况
（异常猪只列表，无异常时说明全场健康）
## 🍽️ 饲养管理
（采食量和饮水量状况及建议）
## ⚠️ 今日预警
（汇总异常事件）
## 💡 AI 建议
（3条基于当日数据的具体行动建议）
---
*本简报由两头乌智能养殖系统自动生成 | （填入当前时间）*

严格约束：全程中文，简报完整详实，不受长度限制。"""

        super().__init__(name="briefing_agent", system_prompt=system_prompt, tools=[])

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
            try:
                llm = ChatOpenAI(api_key=self.api_key, base_url=self.base_url, model=self.model, temperature=0.2, max_tokens=4000)
            except TypeError:
                llm = ChatOpenAI(openai_api_key=self.api_key, openai_api_base=self.base_url, model=self.model, temperature=0.2, max_tokens=4000)
            tools = self.get_tools()
            agent = create_react_agent(llm=llm, tools=tools, prompt=self._build_react_prompt())
            from v1.logic.central_agent_core import RichTraceHandler
            callbacks = [RichTraceHandler(client_id=context.client_id)] if HAS_RICH else []
            executor = AgentExecutor(agent=agent, tools=tools, verbose=False,
                handle_parsing_errors=True, max_iterations=8, return_intermediate_steps=True, callbacks=callbacks)
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
        """LangChain 不可用时直接调3个工具拼接 Markdown 简报"""
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
    """多智能体协调器"""
    
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
        执行多智能体协作流程
        
        1. Supervisor 路由
        2. Worker 执行
        3. 返回结果
        """
        # 路由（传递是否有图片）
        has_image = bool(context.image_urls)
        worker_name = self.supervisor.route(context.user_input, has_image=has_image)
        
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
        """直接回复（闲聊、问候等）"""
        if not HAS_OPENAI:
            return AgentResult(
                success=True,
                answer="您好，有什么可以帮您的吗？",
                worker_name="direct_reply"
            )
        
        try:
            api_key, base_url, model = self.supervisor._get_llm_config()
            client = OpenAI(api_key=api_key, base_url=base_url)
            
            messages = [
                {"role": "system", "content": "你是友好的助手。回复简短：1-2句，每句不超过20字。"},
                {"role": "user", "content": context.user_input}
            ]
            
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.7,
                max_tokens=100,
            )
            
            answer = response.choices[0].message.content.strip()
            
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
