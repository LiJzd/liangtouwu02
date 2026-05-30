# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import List, Optional, Tuple, Any

from v1.common.config import get_settings
from v1.logic.agent_debug_controller import push_debug_event

logger = logging.getLogger("central_agent")

# Rich 控制台美化
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
    from openai import OpenAI
    HAS_OPENAI = True
except Exception:
    HAS_OPENAI = False

from v1.common.langchain_compat import (
    HAS_LANGCHAIN,
    AgentExecutor,
    BaseCallbackHandler,
    create_react_agent,
    AIMessage,
    HumanMessage,
    LCTool,
    PromptTemplate,
    ChatOpenAI
)


# Use unicode escapes to avoid Windows console encoding issues.
_ZH_AGENT = "智能体"
_ZH_TOOL_START = "工具开始"
_ZH_TOOL_END = "工具结束"
_ZH_TOOL_CALL = "工具调用"
_ZH_INPUT = "输入"
_ZH_OUTPUT = "输出"

# ReAct 思考模式的模板
REACT_PROMPT_TEMPLATE = """你是一个智能助手，可以使用工具来回答问题。

你可以使用以下工具：

{tools}

使用以下格式进行推理和行动：

Question: 用户的问题
Thought: 你应该思考要做什么
Action: 要采取的行动，必须是 [{tool_names}] 中的一个
Action Input: 行动的输入参数
Observation: 行动的结果
... (这个 Thought/Action/Action Input/Observation 可以重复N次)
Thought: 我现在知道最终答案了
Final Answer: 对原始问题的最终答案

重要规则：
1. 必须严格按照上述格式输出
2. Action 必须是工具列表中的一个
3. 如果不需要工具，直接给出 Final Answer
4. 回答要简洁、通俗易懂
5. 使用表情符号让回答更友好

开始！

Question: {input}
Thought: {agent_scratchpad}"""


from langchain_core.callbacks import AsyncCallbackHandler

class RichTraceHandler(AsyncCallbackHandler):
    """这个类主要负责把 Agent 的“内心戏”用漂亮的方式打印出来，顺便同步给前端调试看。"""

    def __init__(self, client_id: str = "default", agent_name: str = "Agent", enable_filter: bool = True):
        super().__init__()
        self.client_id = client_id
        self.agent_name = agent_name
        self.enable_filter = enable_filter
        self._streaming_final_answer = not enable_filter # 如果禁用了过滤，默认就处于推送状态
        self._token_buffer = ""

    async def on_agent_action(self, action, **kwargs: Any) -> Any:
        """当 Agent 决定要做啥动作（调啥工具）的时候，就会触发这里。"""
        tool_name = getattr(action, "tool", "unknown")
        tool_input = getattr(action, "tool_input", "")
        log_text = getattr(action, "log", "")
        
        # 提取 Thought
        thought = log_text.split("Action:")[0].strip()
        if thought.startswith("Thought:"):
            thought = thought[8:].strip()
        
        # 推送到 SSE 调试流
        try:
            # 尝试清理并美化 JSON 参数
            clean_input = str(tool_input).strip()
            if clean_input.startswith("Action Input:"):
                clean_input = clean_input[13:].strip()
            
            # 格式化 JSON 以便前端代码块展示
            try:
                import json
                if clean_input.startswith("{") or clean_input.startswith("["):
                    parsed_json = json.loads(clean_input)
                    clean_input = json.dumps(parsed_json, indent=2, ensure_ascii=False)
            except Exception:
                pass # 解析失败则保持原样
            
            await push_debug_event("action", {
                "tool": tool_name,
                "input": clean_input,
                "thought": thought or "正在进行方案决策..."
            }, self.client_id, agent=self.agent_name, status="思索中")
        except Exception:
            pass

        if HAS_RICH and console:
            content = Text()
            if thought:
                content.append("[Thought]: ", style="bold green")
                content.append(f"{thought}\n", style="white")
            content.append("[Action]: ", style="bold cyan")
            content.append(f"{tool_name}\n", style="cyan")
            content.append("📝 参数: ", style="bold yellow")
            content.append(str(tool_input), style="yellow")
            
            console.print(Panel(
                content,
                title=f"[bold magenta][{self.agent_name} 思维链][/]",
                border_style="magenta",
                expand=False
            ))

    async def on_llm_start(self, serialized, prompts, **kwargs):
        """每一轮 LLM 调用开始前，重置流式过滤状态。"""
        self._streaming_final_answer = not self.enable_filter
        self._token_buffer = ""

    async def on_tool_end(self, output, **kwargs):
        """工具干完活儿返回结果后，推送观测结果。"""
        try:
            await push_debug_event("observation", {
                "output": str(output)[:1000]
            }, self.client_id, agent=self.agent_name, status="工作中")
        except Exception:
            pass

        if HAS_RICH and console:
            console.print(Panel(
                Text(str(output)[:500] + ("..." if len(str(output)) > 500 else ""), style="italic"),
                title=f"[bold blue][{self.agent_name} 观测][/]",
                border_style="blue",
                expand=False
            ))

    async def on_agent_finish(self, finish, **kwargs: Any) -> Any:
        """Agent 搞定了，给出一个最终结论。"""
        output = getattr(finish, "return_values", {}).get("output", "")
        
        # 推送到 SSE 调试流
        try:
            await push_debug_event("final_answer", {
                "answer": str(output)
            }, self.client_id, agent=self.agent_name, status="决策完成")
        except Exception:
            pass

        if HAS_RICH and console:
            console.print(Panel(
                Text(str(output), style="bold white"),
                title=f"[bold green][{self.agent_name} 结论][/]",
                border_style="green",
                expand=False
            ))

    async def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        """当 LLM 产出新的 Token 时，实时推送给前端（带过滤逻辑）。"""
        if not token:
            return

        # 1. 如果已经进入最终答案阶段，直接推送
        if self._streaming_final_answer:
            try:
                await push_debug_event("final_answer_chunk", {
                    "text": token
                }, self.client_id, agent=self.agent_name)
            except Exception:
                pass
            return

        # 2. 累加到缓冲区并检测标记
        self._token_buffer += token
        
        # 使用正则进行模糊匹配，支持中英文标识
        patterns = [
            r"(?i)Final\s*Answer\s*[:：]",
            r"最终回答\s*[:：]",
            r"结论\s*[:：]",
            r"(?i)Conclusion\s*:",
            r"(?i)Answer\s*:"
        ]
        
        matched_pattern = None
        for p in patterns:
            match = re.search(p, self._token_buffer)
            if match:
                matched_pattern = match.group(0)
                break
        
        # 情况 A: 匹配到了结论标识
        if matched_pattern:
            self._streaming_final_answer = True
            parts = self._token_buffer.split(matched_pattern, 1)
            if len(parts) > 1:
                answer_part = parts[1]
                if answer_part:
                    try:
                        # 只推送标识符之后的内容
                        await push_debug_event("final_answer_chunk", {
                            "text": answer_part.lstrip()
                        }, self.client_id, agent=self.agent_name)
                    except Exception:
                        pass
            self._token_buffer = "" # 清空，节省内存
            return

        # 情况 B: 缓冲区溢出保护（缩短到 200 字符还没检测到结论，强制开启流式显示）
        if len(self._token_buffer) > 200:
            logger.warning(f"[{self.agent_name}] 缓冲区溢出 (200 chars)，强制开启流式显示。")
            self._streaming_final_answer = True
            try:
                await push_debug_event("final_answer_chunk", {
                    "text": self._token_buffer
                }, self.client_id, agent=self.agent_name)
            except Exception:
                pass
            self._token_buffer = ""

    async def _push_event(self, event_type: str, data: dict, status: str = None):
        """推送辅助事件到调试流"""
        try:
            await push_debug_event(event_type, data, self.client_id, agent=self.agent_name, status=status)
        except Exception:
            pass


def _get_llm_config() -> Tuple[str, str, str]:
    """去环境变量或者配置文件里把 AI 的账号密码翻出来。"""
    settings = get_settings()
    api_key = os.environ.get("DASHSCOPE_API_KEY") or settings.dashscope_api_key
    base_url = (
        os.environ.get("DASHSCOPE_BASE_URL")
        or settings.dashscope_base_url
        or "https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    model = os.environ.get("DASHSCOPE_MODEL") or settings.dashscope_model or "qwen-plus"
    return api_key, base_url, model


def _build_llm(api_key: str, base_url: str, model: str) -> ChatOpenAI:
    """初始化一个 LangChain 版的聊天客户端。"""
    try:
        return ChatOpenAI(
            api_key=api_key,
            base_url=base_url,
            model=model,
            temperature=0.3,
            max_tokens=200,
        )
    except TypeError:
        return ChatOpenAI(
            openai_api_key=api_key,
            openai_api_base=base_url,
            model=model,
            temperature=0.3,
            max_tokens=200,
        )


def _run_async(coro) -> str:
    """Agent 环境目前主要是同步的活儿，咱们得想个招儿在同步代码里把异步接口给跑通。"""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    box: dict[str, str] = {}

    def _worker() -> None:
        box["value"] = asyncio.run(coro)

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
    thread.join()
    return box.get("value", "")


def _build_lc_tools() -> list[LCTool]:
    """把咱系统里那套自定义工具，打包成 LangChain 能认出来的样子。"""
    from v1.logic.bot_tools import list_tools

    tools = []
    for tool in list_tools().values():
        # Bind current tool inside closure to avoid late-binding.
        def _make(t):
            def _call(arg: str) -> str:
                print(f"[{_ZH_AGENT}][{_ZH_TOOL_START}] {t.name} {_ZH_INPUT}={arg}")
                result = _run_async(t.handler(arg))
                print(f"[{_ZH_AGENT}][{_ZH_TOOL_END}] {_ZH_OUTPUT}={result}")
                return result

            return LCTool(name=t.name, description=t.description, func=_call)

        tools.append(_make(tool))
    return tools


def _split_messages(messages: List[dict]) -> tuple[str, list, str]:
    """把这一坨消息拆开，看看哪些是人说的，哪些是 AI 以前回的，还有系统定的规矩。"""
    system_prompt = ""
    rest = messages or []
    if rest and rest[0].get("role") == "system":
        system_prompt = rest[0].get("content", "")
        rest = rest[1:]

    user_input = ""
    history = rest
    if rest and rest[-1].get("role") == "user":
        user_input = rest[-1].get("content", "")
        history = rest[:-1]

    chat_history = []
    for item in history:
        role = item.get("role")
        content = item.get("content", "")
        if role == "user":
            chat_history.append(HumanMessage(content=content))
        elif role == "assistant":
            chat_history.append(AIMessage(content=content))
    return system_prompt, chat_history, user_input


def _requires_tool(user_input: str) -> bool:
    """预判一下：如果是查库相关的关键词，说明用户想看实锤数据，必须让 Agent 动真格去调用工具。"""
    text = (user_input or "").strip().lower()
    if not text:
        return False
    keywords = [
        "工具",
        "功能",
        "能做什么",
        "能干什么",
        "能干啥",
        "列表",
        "查",
        "查询",
        "看看",
        "看下",
        "猪场",
        "有哪些猪",
        "哪几头",
        "猪只",
        "档案",
        "id",
        "编号",
        "\u751f\u957f\u66f2\u7ebf",  # 生长曲线
        "\u9884\u6d4b",  # 预测
        "\u8f68\u8ff9",  # 轨迹
        "\u56fe\u7247",  # 图片
        "\u7167\u7247",  # 照片
        "\u89c6\u9891",  # 视频
        "\u76d1\u63a7",  # 监控
        "\u6444\u50cf",  # 摄像
        "\u73b0\u573a",  # 现场
        "\u60c5\u51b5",  # 情况
        "\u72b6\u6001",  # 状态
        "\u73b0\u5728",  # 现在
        "\u5f53\u524d",  # 当前
        "\u622a\u56fe",  # 截图
        "\u622a\u53d6",  # 截取
        "\u8bc6\u522b",  # 识别
        "\u68c0\u6d4b",  # 检测
        "\u6709\u591a\u5c11",  # 有多少
        "\u591a\u5c11\u53ea",  # 多少只
    ]
    return any(k in text for k in keywords)


def _extract_tool_error(observation: str) -> Optional[str]:
    """如果工具报了错（返回了带 error 字段的 JSON），咱得把它抓出来告诉用户。"""
    if not observation:
        return None
    try:
        import json

        data = json.loads(observation)
        if isinstance(data, dict) and data.get("error"):
            return str(data["error"])
    except Exception:
        return None
    return None


def _extract_final_answer(agent_output: str) -> str:
    """
    从 Agent 输出中提取 Final Answer，严格隔离思考过程。
    这是防止"思考链污染"的核心函数。
    """
    if not agent_output:
        return ""
    
    # 正则匹配 "Final Answer: xxx"
    match = re.search(r"Final Answer:\s*(.+)", agent_output, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    # 如果没有 Final Answer 标记，说明 Agent 格式错误
    logger.warning(f"Agent 输出缺少 Final Answer 标记，原始输出: {agent_output[:200]}")
    
    # 尝试提取最后一段非空文本作为兜底
    lines = [line.strip() for line in agent_output.split('\n') if line.strip()]
    if lines:
        # 过滤掉明显的思考过程标记
        filtered = [
            line for line in lines 
            if not any(marker in line for marker in ["Thought:", "Action:", "Observation:", "Question:"])
        ]
        if filtered:
            return filtered[-1]
    
    return agent_output.strip()


def _run_agent_once(
    system_prompt: str,
    chat_history: list,
    user_input: str,
    force_tool: bool = False,
    client_id: str = "default",
) -> tuple[Optional[str], list[str], list[str]]:
    """跑一遍 ReAct 流程，把最后的答案、中间用过的工具输出还有它的内心戏都拿回来。"""
    api_key, base_url, model = _get_llm_config()
    llm = _build_llm(api_key, base_url, model)
    tools = _build_lc_tools()
    
    # 构建ReAct提示词
    react_prompt = PromptTemplate.from_template(REACT_PROMPT_TEMPLATE)
    
    # 如果强制使用工具，在系统提示词中添加要求
    if force_tool:
        system_instruction = (
            system_prompt
            + "\n\n重要：必须调用工具获取结果，禁止凭空编造；若工具不可用，请说明失败原因。"
        )
    else:
        system_instruction = system_prompt
    
    # 创建ReAct Agent
    agent = create_react_agent(llm=llm, tools=tools, prompt=react_prompt)
    
    # 创建Agent Executor（带 Rich 追踪）
    callbacks = [RichTraceHandler(client_id=client_id)] if (HAS_RICH and HAS_LANGCHAIN) else []
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=False,  # 关闭 LangChain 自带的冗长日志，使用 Rich 替代
        max_iterations=5,
        return_intermediate_steps=True,
        callbacks=callbacks,
    )

    # 构建输入（包含历史对话和系统指令）
    input_text = f"{system_instruction}\n\n"
    if chat_history:
        input_text += "历史对话：\n"
        for msg in chat_history[-4:]:  # 只保留最近4轮
            if isinstance(msg, HumanMessage):
                input_text += f"用户: {msg.content}\n"
            elif isinstance(msg, AIMessage):
                input_text += f"助手: {msg.content}\n"
        input_text += "\n"
    input_text += f"当前问题：{user_input}"
    
    # 执行Agent
    try:
        result = agent_executor.invoke({"input": input_text})
        
        # 提取原始输出
        raw_output = result.get("output", "")
        
        # 【关键】严格提取 Final Answer，丢弃所有思考过程
        clean_output = _extract_final_answer(raw_output)
        
        # 提取中间步骤（仅用于日志和调试）
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
        
        return (clean_output if clean_output else None, tool_outputs, thoughts)
        
    except Exception as e:
        logger.error(f"ReAct Agent执行失败: {str(e)}", exc_info=True)
        # 推送错误事件
        asyncio.create_task(_push_error_event(str(e), client_id))
        return (None, [], [f"Error: {str(e)}"])


async def _push_error_event(error: str, client_id: str):
    """推送错误事件到调试流"""
    try:
        from v1.logic.agent_debug_controller import push_debug_event
        await push_debug_event("error", {"message": error}, client_id)
    except Exception:
        pass


def _call_agent(messages: List[dict], client_id: str = "default") -> Optional[str]:
    """大招：开启带工具调用的 Agent 模式。"""
    if not HAS_LANGCHAIN:
        logger.warning("LangChain 未安装，智能体已禁用。")
        if HAS_RICH and console:
            console.print("[bold red]⚠️  LangChain 未安装，智能体已禁用[/]")
        else:
            print(f"[{_ZH_AGENT}] LangChain 未安装，已禁用智能体。")
        return None

    api_key, base_url, model = _get_llm_config()
    if not api_key:
        logger.warning("缺少 DASHSCOPE_API_KEY，智能体已禁用。")
        if HAS_RICH and console:
            console.print("[bold red]⚠️  缺少 DASHSCOPE_API_KEY，智能体已禁用[/]")
        else:
            print(f"[{_ZH_AGENT}] 缺少 DASHSCOPE_API_KEY，已禁用智能体。")
        return None

    system_prompt, chat_history, user_input = _split_messages(messages)
    if not user_input:
        return None

    # Rich 美化的开始标记
    if HAS_RICH and console:
        console.print("\n" + "="*60, style="bold blue")
        console.print("🚀 ReAct 推理引擎启动", style="bold blue", justify="center")
        console.print("="*60 + "\n", style="bold blue")
        console.print(Panel(
            Text(user_input, style="white"),
            title="[bold cyan]用户问题[/]",
            border_style="cyan"
        ))
    else:
        print(f"\n[{_ZH_AGENT}] ========== ReAct 推理开始 ==========")

    output, tool_outputs, thoughts = _run_agent_once(system_prompt, chat_history, user_input, force_tool=False, client_id=client_id)

    # 【关键】思考过程仅记录到日志，不返回给用户
    if thoughts:
        logger.debug(f"Agent 思考过程: {thoughts}")

    # If tool is required but none used, retry with hard requirement.
    if _requires_tool(user_input) and not tool_outputs:
        if HAS_RICH and console:
            console.print("[bold yellow]⚠️  需要工具但未触发，强制重试[/]")
        else:
            print(f"[{_ZH_AGENT}] 需要工具但未触发，已强制重试调用工具。")
        
        output, tool_outputs, thoughts = _run_agent_once(system_prompt, chat_history, user_input, force_tool=True, client_id=client_id)
        
        if thoughts:
            logger.debug(f"Agent 重试思考过程: {thoughts}")

    if _requires_tool(user_input) and not tool_outputs:
        if HAS_RICH and console:
            console.print("[bold red]❌ 仍未触发工具[/]")
        else:
            print(f"[{_ZH_AGENT}] 仍未触发工具，返回提示信息。")
        return "需要调用工具才能回答，但未成功触发工具。请稍后再试。"

    # If tool output contains error, surface it directly to avoid hallucination.
    for observation in tool_outputs:
        err = _extract_tool_error(observation)
        if err:
            return f"工具调用失败：{err}"

    # Rich 美化的结束标记
    if HAS_RICH and console:
        console.print("\n" + "="*60, style="bold green")
        console.print("✅ ReAct 推理完成", style="bold green", justify="center")
        console.print("="*60 + "\n", style="bold green")
    else:
        print(f"[{_ZH_AGENT}] ========== ReAct 推理结束 ==========\n")
    
    return output


def _call_llm(messages: List[dict]) -> Optional[str]:
    """备选：如果 Agent 不给力或者没必要用工具，就让普通 LLM 直接回一下算了。"""
    if not HAS_OPENAI:
        logger.warning("OpenAI \u5ba2\u6237\u7aef\u4e0d\u53ef\u7528\uff0cLLM \u5df2\u7981\u7528\u3002")
        return None
    api_key, base_url, model = _get_llm_config()
    if not api_key:
        logger.warning("\u7f3a\u5c11 DASHSCOPE_API_KEY\uff0cLLM \u5df2\u7981\u7528\u3002")
        return None
    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.3,
            max_tokens=200,
        )
        content = response.choices[0].message.content
        if content:
            return content.strip()
    except Exception as exc:
        logger.exception("LLM \u8c03\u7528\u5931\u8d25: %s", exc)
    return None


def _fallback_reply() -> str:
    return "\u7cfb\u7edf\u7e41\u5fd9\uff0c\u60a8\u5148\u8bf4\u60c5\u51b5\uff0c\u6211\u9a6c\u4e0a\u56de\u590d\u3002"


def generate_reply(messages: List[dict], client_id: str = "default") -> str:
    """对外暴露的总入口：先试 Agent，Agent 挂了或没回就让备选 LLM 顶上。"""
    agent_reply = _call_agent(messages, client_id=client_id)
    if agent_reply:
        return agent_reply
    llm_reply = _call_llm(messages)
    if llm_reply:
        return llm_reply
    return _fallback_reply()
