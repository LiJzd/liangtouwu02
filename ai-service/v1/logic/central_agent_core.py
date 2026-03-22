from __future__ import annotations

import asyncio
import logging
import os
import threading
from typing import List, Optional, Tuple

from v1.common.config import get_settings

logger = logging.getLogger("central_agent")

try:
    from openai import OpenAI
    HAS_OPENAI = True
except Exception:
    HAS_OPENAI = False

try:
    from langchain.agents import create_react_agent, AgentExecutor
    from langchain_core.callbacks import BaseCallbackHandler
    from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
    from langchain_core.tools import Tool as LCTool
    from langchain_core.prompts import PromptTemplate
    from langchain_openai import ChatOpenAI
    HAS_LANGCHAIN = True
except Exception:
    BaseCallbackHandler = object  # type: ignore[assignment]
    HAS_LANGCHAIN = False


# Use unicode escapes to avoid Windows console encoding issues.
_ZH_AGENT = "智能体"
_ZH_TOOL_START = "工具开始"
_ZH_TOOL_END = "工具结束"
_ZH_TOOL_CALL = "工具调用"
_ZH_INPUT = "输入"
_ZH_OUTPUT = "输出"

# ReAct 提示词模板（中文版）
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


class ConsoleToolTraceHandler(BaseCallbackHandler):
    """Print tool execution steps to stdout (no chain-of-thought)."""

    def on_tool_start(self, serialized, input_str, **kwargs):  # type: ignore[override]
        name = (serialized or {}).get("name", "tool")
        print(f"[{_ZH_AGENT}][{_ZH_TOOL_START}] {name} {_ZH_INPUT}={input_str}")

    def on_tool_end(self, output, **kwargs):  # type: ignore[override]
        print(f"[{_ZH_AGENT}][{_ZH_TOOL_END}] {_ZH_OUTPUT}={output}")


def _get_llm_config() -> Tuple[str, str, str]:
    """Resolve LLM config from env or Settings."""
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
    """Create a LangChain ChatOpenAI client with compatible args."""
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
    """Run async tool handlers safely from sync agent context."""
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
    """Adapt internal tool registry to LangChain tools."""
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
    """Split incoming messages into system prompt, chat history, and user input."""
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
    """Heuristic: queries that should hit tools (avoid hallucinated data)."""
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
    """Parse tool output for error field when it's JSON."""
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


def _run_agent_once(
    system_prompt: str,
    chat_history: list,
    user_input: str,
    force_tool: bool = False,
) -> tuple[Optional[str], list[str], list[str]]:
    """Run ReAct agent once and return output + intermediate steps + thoughts."""
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
    
    # 创建Agent Executor（带详细日志）
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,  # 启用详细日志，显示思考过程
        handle_parsing_errors=True,  # 处理解析错误
        max_iterations=5,  # 最大迭代次数
        return_intermediate_steps=True,  # 返回中间步骤
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
        
        # 提取输出
        output = result.get("output", "")
        
        # 提取中间步骤
        intermediate_steps = result.get("intermediate_steps", [])
        tool_outputs = []
        thoughts = []
        
        for step in intermediate_steps:
            if len(step) >= 2:
                action, observation = step[0], step[1]
                # 记录工具调用
                tool_name = getattr(action, "tool", "unknown")
                tool_input = getattr(action, "tool_input", "")
                thoughts.append(f"Action: {tool_name}")
                thoughts.append(f"Action Input: {tool_input}")
                tool_outputs.append(str(observation))
                thoughts.append(f"Observation: {observation}")
        
        return (output.strip() if output else None, tool_outputs, thoughts)
        
    except Exception as e:
        logger.error(f"ReAct Agent执行失败: {str(e)}", exc_info=True)
        return (None, [], [f"Error: {str(e)}"])


def _call_agent(messages: List[dict]) -> Optional[str]:
    """Use LangChain ReAct Agent with tool calling."""
    if not HAS_LANGCHAIN:
        logger.warning("LangChain \u672a\u5b89\u88c5\uff0c\u667a\u80fd\u4f53\u5df2\u7981\u7528\u3002")
        print(f"[{_ZH_AGENT}] LangChain \u672a\u5b89\u88c5\uff0c\u5df2\u7981\u7528\u667a\u80fd\u4f53\u3002")
        return None

    api_key, base_url, model = _get_llm_config()
    if not api_key:
        logger.warning("\u7f3a\u5c11 DASHSCOPE_API_KEY\uff0c\u667a\u80fd\u4f53\u5df2\u7981\u7528\u3002")
        print(f"[{_ZH_AGENT}] \u7f3a\u5c11 DASHSCOPE_API_KEY\uff0c\u5df2\u7981\u7528\u667a\u80fd\u4f53\u3002")
        return None

    system_prompt, chat_history, user_input = _split_messages(messages)
    if not user_input:
        return None

    print(f"\n[{_ZH_AGENT}] ========== ReAct 推理开始 ==========")
    output, tool_outputs, thoughts = _run_agent_once(system_prompt, chat_history, user_input, force_tool=False)

    # 打印思考过程
    if thoughts:
        print(f"[{_ZH_AGENT}] 思考过程:")
        for thought in thoughts:
            print(f"  {thought}")

    # If tool is required but none used, retry with hard requirement.
    if _requires_tool(user_input) and not tool_outputs:
        print(f"[{_ZH_AGENT}] 需要工具但未触发，已强制重试调用工具。")
        output, tool_outputs, thoughts = _run_agent_once(system_prompt, chat_history, user_input, force_tool=True)
        
        if thoughts:
            print(f"[{_ZH_AGENT}] 重试思考过程:")
            for thought in thoughts:
                print(f"  {thought}")

    if _requires_tool(user_input) and not tool_outputs:
        print(f"[{_ZH_AGENT}] 仍未触发工具，返回提示信息。")
        return (
            "需要调用工具才能回答，"
            "但未成功触发工具。"
            "请稍后再试。"
        )

    # If tool output contains error, surface it directly to avoid hallucination.
    for observation in tool_outputs:
        err = _extract_tool_error(observation)
        if err:
            return f"工具调用失败：{err}"

    print(f"[{_ZH_AGENT}] ========== ReAct 推理结束 ==========\n")
    return output


def _call_llm(messages: List[dict]) -> Optional[str]:
    """Fallback: direct OpenAI-compatible call without tools."""
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


def generate_reply(messages: List[dict]) -> str:
    """Main entry: try agent first, then fallback LLM."""
    agent_reply = _call_agent(messages)
    if agent_reply:
        return agent_reply
    llm_reply = _call_llm(messages)
    if llm_reply:
        return llm_reply
    return _fallback_reply()
