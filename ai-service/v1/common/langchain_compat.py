# -*- coding: utf-8 -*-
"""
LangChain 兼容性层
由 Antigravity 优化：已锁定依赖版本，建立确定性导入。
"""
import logging
from typing import Any

logger = logging.getLogger("langchain_compat")

try:
    # 1. 核心定义导入 (langchain-core)
    from langchain_core.callbacks import BaseCallbackHandler
    from langchain_core.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder
    from langchain_core.tools import Tool as LCTool
    from langchain_core.messages import (
        AIMessage, 
        HumanMessage, 
        SystemMessage, 
        ToolMessage, 
        AIMessageChunk
    )
    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.outputs import ChatResult, ChatGeneration, ChatGenerationChunk
    
    # 2. 运行时执行单元 (在当前环境锁定为 langchain-classic)
    from langchain_classic.agents import create_tool_calling_agent, AgentExecutor
    from langchain_classic.agents import create_react_agent
    
    # 3. LLM 驱动 (langchain-openai)
    from langchain_openai import ChatOpenAI

    HAS_LANGCHAIN = True
    logger.info("LangChain compatibility layer initialized successfully (Classic Mode).")

except ImportError as e:
    logger.error(f"Critical failure in LangChain compatible imports: {e}")
    HAS_LANGCHAIN = False
    
    # 回退空定义以防止后续逻辑 import 崩溃
    BaseCallbackHandler = object
    BaseChatModel = object
    PromptTemplate = ChatPromptTemplate = MessagesPlaceholder = None
    LCTool = None
    AIMessage = HumanMessage = SystemMessage = ToolMessage = AIMessageChunk = None
    ChatResult = ChatGeneration = ChatGenerationChunk = None
    create_tool_calling_agent = AgentExecutor = create_react_agent = None
    ChatOpenAI = None
