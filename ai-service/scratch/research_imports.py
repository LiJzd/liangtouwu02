# -*- coding: utf-8 -*-
import sys
import os

# Add the project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

print("--- Testing Imports ---")
try:
    from langchain.agents import create_react_agent, AgentExecutor
    print("Found langchain.agents")
except ImportError:
    print("Failed langchain.agents")

try:
    from langchain_classic.agents import create_react_agent, AgentExecutor
    print("Found langchain_classic.agents")
except ImportError:
    print("Failed langchain_classic.agents")

try:
    from langchain_core.callbacks import BaseCallbackHandler
    print("Found langchain_core.callbacks")
except ImportError:
    print("Failed langchain_core.callbacks")

try:
    from langchain_core.prompts import PromptTemplate
    print("Found langchain_core.prompts")
except ImportError:
    print("Failed langchain_core.prompts")

try:
    from langchain_openai import ChatOpenAI
    print("Found langchain_openai")
except ImportError:
    print("Failed langchain_openai")

from v1.logic.multi_agent_core import HAS_LANGCHAIN
print(f"HAS_LANGCHAIN in multi_agent_core: {HAS_LANGCHAIN}")

print("\n--- Testing MultiModal SDK ---")
import dashscope
from dashscope import MultiModalConversation, Generation
from v1.common.config import get_settings

settings = get_settings()
api_key = os.environ.get("DASHSCOPE_API_KEY") or settings.dashscope_api_key
print(f"API Key present: {bool(api_key)}")

if api_key:
    # Test a simple native call if possible
    # We won't actually call the API to save tokens, but we check if components are present
    print("MultiModalConversation and Generation are imported.")
else:
    print("API Key missing, cannot test SDK fully.")

print("\n--- Testing PIL ---")
try:
    from PIL import Image
    print("PIL found")
except ImportError:
    print("PIL missing")
