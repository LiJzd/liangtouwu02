# -*- coding: utf-8 -*-
"""
LangChain 兼容性层
统一处理不同环境下的 LangChain 导入逻辑，确保类身份唯一。
"""
import logging

logger = logging.getLogger("langchain_compat")

try:
    # 1. 尝试从 langchain_core 导入基础定义（这是目前最通用的回调基类来源）
    try:
        from langchain_core.callbacks import BaseCallbackHandler
        from langchain_core.prompts import PromptTemplate
        from langchain_core.tools import Tool as LCTool
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
        from langchain_core.language_models.chat_models import BaseChatModel
        from langchain_core.outputs import ChatResult, ChatGeneration
    except (ImportError, ModuleNotFoundError):
        BaseCallbackHandler = object
        PromptTemplate = LCTool = None
        AIMessage = HumanMessage = SystemMessage = ToolMessage = None
        BaseChatModel = None
        ChatResult = ChatGeneration = None

    # 2. 尝试导入执行器
    try:
        from langchain.agents import create_react_agent, AgentExecutor
        logger.info("Imported AgentExecutor from standard langchain.")
    except (ImportError, ModuleNotFoundError):
        try:
            from langchain_classic.agents import create_react_agent, AgentExecutor
            logger.info("Imported AgentExecutor from langchain-classic.")
        except (ImportError, ModuleNotFoundError):
            try:
                from langgraph.prebuilt import create_react_agent
                from langchain_classic.agents import AgentExecutor
                logger.info("Imported AgentExecutor from langgraph/classic mixture.")
            except (ImportError, ModuleNotFoundError):
                create_react_agent = None
                AgentExecutor = None
                logger.warning("AgentExecutor components not found in any standard path.")

    # 4. 其他核心组件统一导入
    from langchain_core.prompts import PromptTemplate
    from langchain_core.tools import Tool as LCTool
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.outputs import ChatResult, ChatGeneration

    HAS_LANGCHAIN = (create_react_agent is not None) and (AgentExecutor is not None)

except Exception as e:
    logger.error(f"Critical failure in LangChain compatibility layer: {e}")
    create_react_agent = None
    AgentExecutor = None
    BaseCallbackHandler = object
    PromptTemplate = None
    LCTool = None
    ChatOpenAI = None
    AIMessage = HumanMessage = SystemMessage = ToolMessage = None
    BaseChatModel = None
    ChatResult = ChatGeneration = None
    HAS_LANGCHAIN = False
