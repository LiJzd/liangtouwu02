"""
多智能体架构核心 - Supervisor + Worker 模式
实现意图路由和专家分工
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
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
# 数据结构
# ============================================================

@dataclass
class AgentContext:
    """Agent 执行上下文"""
    user_id: str
    user_input: str
    chat_history: list
    metadata: dict
    client_id: str = "default"


@dataclass
class AgentResult:
    """Agent 执行结果"""
    success: bool
    answer: str
    worker_name: Optional[str] = None
    thoughts: List[str] = None
    tool_outputs: List[str] = None
    error: Optional[str] = None
    image: Optional[str] = None  # Base64 编码的图片
    metadata: Optional[dict] = None  # 额外的元数据

    def __post_init__(self):
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
- vet_agent: 兽医诊断、疾病分析、用药建议、健康评估
- data_agent: 猪只档案查询、生长曲线预测、数据统计、列表查询
- perception_agent: 视频监控、图像识别、现场情况、截图分析

规则：
1. 只输出专家名称，不要解释
2. 如果不需要专家（如闲聊、问候），输出 "direct_reply"
3. 一次只选一个专家
4. 优先选择最专业的专家

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
    
    def route(self, user_input: str) -> str:
        """
        路由用户请求到合适的 Worker
        
        Returns:
            worker_name: vet_agent, data_agent, perception_agent, 或 direct_reply
        """
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
            valid_workers = ["vet_agent", "data_agent", "perception_agent", "direct_reply"]
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
        
        # 兽医诊断关键词
        vet_keywords = [
            "病", "诊断", "治疗", "用药", "症状", "拉稀", "咳嗽", 
            "发烧", "体温", "不吃", "精神", "健康", "兽医"
        ]
        if any(k in text for k in vet_keywords):
            return "vet_agent"
        
        # 数据查询关键词
        data_keywords = [
            "查", "档案", "列表", "有哪些", "多少", "生长", "曲线", 
            "预测", "轨迹", "体重", "月龄", "id", "编号"
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
            
            # 简化方案：对于只有一个工具的情况，直接调用
            if len(tools) == 1:
                try:
                    tool = tools[0]
                    logger.info(f"直接调用工具: {tool.name}")
                    
                    # 调用工具
                    observation = tool.func({})
                    logger.info(f"工具返回: {observation}")
                    
                    # 解析工具输出
                    import json
                    obs_data = json.loads(str(observation))
                    summary = obs_data.get("summary", "处理完成")
                    image_key = obs_data.get("image_key")
                    
                    # 从缓存获取图片
                    image_base64 = None
                    if image_key:
                        from v1.logic.bot_tools import get_cached_image
                        image_base64 = get_cached_image(image_key)
                        if image_base64:
                            logger.info(f"成功获取图片，长度: {len(image_base64)}")
                        else:
                            logger.warning(f"缓存中未找到图片: {image_key}")
                    
                    # 使用 LLM 生成友好的回复
                    from langchain_core.messages import HumanMessage, SystemMessage
                    messages = [
                        SystemMessage(content=self.system_prompt),
                        HumanMessage(content=f"工具返回结果：{summary}\n\n请用简短、友好的语言告诉用户当前猪场的情况。")
                    ]
                    response = llm.invoke(messages)
                    answer = response.content if hasattr(response, 'content') else str(response)
                    
                    return AgentResult(
                        success=True,
                        answer=answer,
                        worker_name=self.name,
                        image=image_base64,
                        thoughts=[f"调用工具: {tool.name}", f"工具返回: {summary}"],
                        tool_outputs=[summary]
                    )
                except Exception as e:
                    logger.error(f"简化工具调用失败: {e}", exc_info=True)
                    # 继续使用标准 ReAct 流程
            
            # 标准 ReAct 流程（作为降级方案）
            # 构建 ReAct 提示词
            react_prompt = self._build_react_prompt()
            
            # 创建 Agent
            agent = create_react_agent(llm=llm, tools=tools, prompt=react_prompt)
            
            # 创建 Executor
            from v1.logic.central_agent_core import RichTraceHandler
            callbacks = [RichTraceHandler(client_id=context.client_id)] if HAS_RICH else []
            
            agent_executor = AgentExecutor(
                agent=agent,
                tools=tools,
                verbose=False,
                handle_parsing_errors=True,
                max_iterations=3,
                return_intermediate_steps=True,
                callbacks=callbacks,
            )
            
            # 构建输入
            input_text = self._build_input(context)
            
            # 执行
            result = agent_executor.invoke({"input": input_text})
            
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

使用以下格式进行推理和行动：

Question: 用户的问题
Thought: 你应该思考要做什么
Action: 要采取的行动，必须是 [{{tool_names}}] 中的一个
Action Input: 行动的输入参数（JSON 格式）
Observation: 行动的结果
... (这个 Thought/Action/Action Input/Observation 可以重复N次)
Thought: 我现在知道最终答案了
Final Answer: 对原始问题的最终答案

重要规则：
1. 必须严格按照上述格式输出，每个关键词后面必须有冒号和空格
2. Action 必须是工具列表中的一个，不能自己编造
3. 如果工具已经执行完成，直接输出 "Thought: 我现在知道最终答案了" 然后给出 Final Answer
4. Final Answer 必须简洁、通俗易懂，不要包含 Thought/Action/Observation 等关键词
5. 使用表情符号让回答更友好

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
        """提取 Final Answer"""
        if not agent_output:
            return ""
        
        match = re.search(r"Final Answer:\s*(.+)", agent_output, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        # 过滤思考过程标记
        lines = [line.strip() for line in agent_output.split('\n') if line.strip()]
        filtered = [
            line for line in lines 
            if not any(marker in line for marker in ["Thought:", "Action:", "Observation:", "Question:"])
        ]
        if filtered:
            return filtered[-1]
        
        return agent_output.strip()


# ============================================================
# 具体 Worker 实现
# ============================================================

class VetAgent(WorkerAgent):
    """兽医诊断专家"""
    
    def __init__(self):
        system_prompt = """你是资深的畜牧兽医专家，专注于生猪疾病诊断和健康管理。

你的任务：
1. 使用 query_pig_disease_rag 工具查询两头乌病症知识库
2. 根据工具返回的疾病信息进行诊断
3. 提供用药建议和护理方案
4. 评估疾病风险等级
5. 给出明确的行动指令

重要提示：
- 必须先调用 query_pig_disease_rag 工具查询病症知识库
- 工具返回的 "relevant_diseases" 包含相关疾病信息
- 根据 "similarity" 相似度选择最可能的疾病
- 参考 "treatment" 和 "prevention" 给出建议

输出要求：
- 极度通俗化，避免专业术语
- 使用表情符号分段
- 称呼用"老乡/师傅"
- 回复简短：1-3句，每句不超过20字
- 高风险疾病提示联系畜牧局"""
        
        super().__init__(name="vet_agent", system_prompt=system_prompt, tools=[])
    
    def get_tools(self) -> List[LCTool]:
        """兽医 Agent 可用的工具"""
        from v1.logic.bot_tools import list_tools
        
        all_tools = list_tools()
        vet_tool_names = ["query_pig_disease_rag"]
        
        tools = []
        for name in vet_tool_names:
            if name in all_tools:
                tool = all_tools[name]
                tools.append(LCTool(
                    name=tool.name,
                    description=tool.description,
                    func=lambda arg, t=tool: self._run_async_tool(t.handler(arg))
                ))
        
        return tools
    
    def _run_async_tool(self, coro):
        """同步执行异步工具"""
        import asyncio
        import threading
        
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)
        
        box = {}
        
        def _worker():
            box["value"] = asyncio.run(coro)
        
        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()
        thread.join()
        return box.get("value", "")


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
            "query_pig_growth_prediction"
        ]
        
        tools = []
        for name in data_tool_names:
            if name in all_tools:
                tool = all_tools[name]
                tools.append(LCTool(
                    name=tool.name,
                    description=tool.description,
                    func=lambda arg, t=tool: self._run_async_tool(t.handler(arg))
                ))
        
        return tools
    
    def _run_async_tool(self, coro):
        """同步执行异步工具"""
        import asyncio
        import threading
        
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)
        
        box = {}
        
        def _worker():
            box["value"] = asyncio.run(coro)
        
        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()
        thread.join()
        return box.get("value", "")


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
        perception_tool_names = ["capture_pig_farm_snapshot"]
        
        tools = []
        for name in perception_tool_names:
            if name in all_tools:
                tool = all_tools[name]
                tools.append(LCTool(
                    name=tool.name,
                    description=tool.description,
                    func=lambda arg, t=tool: self._run_async_tool(t.handler(arg))
                ))
        
        return tools
    
    def _run_async_tool(self, coro):
        """同步执行异步工具"""
        import asyncio
        import threading
        
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)
        
        box = {}
        
        def _worker():
            box["value"] = asyncio.run(coro)
        
        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()
        thread.join()
        return box.get("value", "")


# ============================================================
# 多智能体协调器
# ============================================================

class MultiAgentOrchestrator:
    """多智能体协调器"""
    
    def __init__(self):
        self.supervisor = SupervisorAgent()
        self.workers = {
            "vet_agent": VetAgent(),
            "data_agent": DataAgent(),
            "perception_agent": PerceptionAgent(),
        }
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """
        执行多智能体协作流程
        
        1. Supervisor 路由
        2. Worker 执行
        3. 返回结果
        """
        # 路由
        worker_name = self.supervisor.route(context.user_input)
        
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
