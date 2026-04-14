# -*- coding: utf-8 -*-
import asyncio
import json
import os
from typing import List, Optional, Any
from dataclasses import dataclass

# 模拟环境与导入
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ai-service")))

# 直接从文件中提取我们要测试的内容（由于 multi_agent_core 依赖较多，我们在这里直接模拟其关键逻辑）
from v1.logic.multi_agent_core import _is_multimodal_model, _convert_to_dashscope_tool, DashScopeNativeChat
from v1.common.langchain_compat import LCTool, AIMessage

async def test_logic():
    print("=== 开始逻辑验证 ===")
    
    # 1. 验证模型判定
    print(f"Check qwen-plus: {_is_multimodal_model('qwen-plus')}")
    print(f"Check qwen-vl-plus: {_is_multimodal_model('qwen-vl-plus')}")
    
    # 2. 验证工具转换
    mock_tool = LCTool(name="test_tool", description="A test tool", func=lambda x: x)
    ds_tools = _convert_to_dashscope_tool([mock_tool])
    print(f"Converted Tools: {json.dumps(ds_tools, ensure_ascii=False)}")
    
    # 3. 验证 DashScopeNativeChat 实例属性
    llm = DashScopeNativeChat(model="qwen-plus", api_key="test-key")
    llm.bind_tools([mock_tool])
    print(f"LLM Bound Tools exists: {llm.bound_tools is not None}")
    
    print("\n=== 逻辑验证完成 ===")

if __name__ == "__main__":
    asyncio.run(test_logic())
