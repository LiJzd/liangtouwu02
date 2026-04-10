# -*- coding: utf-8 -*-
import asyncio
import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from v1.common.langchain_compat import (
    HAS_LANGCHAIN,
    AgentExecutor,
    BaseCallbackHandler,
    create_react_agent,
    LCTool,
    PromptTemplate,
    ChatOpenAI
)

class TestHandler(BaseCallbackHandler):
    def on_agent_action(self, action, **kwargs):
        print(f"Action: {action}")

async def test_agent_executor_validation():
    print("Testing AgentExecutor validation...")
    if not HAS_LANGCHAIN:
        print("HAS_LANGCHAIN is False, skipping test.")
        return

    # Use dashscope native chat for testing
    from v1.logic.multi_agent_core import DashScopeNativeChat
    from v1.common.config import get_settings
    
    settings = get_settings()
    api_key = os.environ.get("DASHSCOPE_API_KEY") or settings.dashscope_api_key
    
    llm = DashScopeNativeChat(
        model="qwen-plus",
        api_key=api_key or "fake-key",
        temperature=0.1
    )
    
    tools = [
        LCTool(
            name="dummy_tool",
            description="A dummy tool",
            func=lambda x: "done"
        )
    ]
    
    prompt = PromptTemplate.from_template("Answer {input}\n{agent_scratchpad}")
    agent = create_react_agent(llm=llm, tools=tools, prompt=prompt)
    
    handler = TestHandler()
    
    try:
        executor = AgentExecutor(
            agent=agent,
            tools=tools,
            callbacks=[handler]
        )
        print("AgentExecutor successfully initialized with callbacks.")
    except Exception as e:
        print(f"AgentExecutor initialization FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(test_agent_executor_validation())
