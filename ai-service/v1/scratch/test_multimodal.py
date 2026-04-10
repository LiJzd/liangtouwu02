import asyncio
import os
import sys

# 将 v1 加入路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from v1.logic.multi_agent_core import VetAgent, AgentContext
from v1.common.config import get_settings

async def test_multimodal():
    settings = get_settings()
    print(f"Using model: {settings.dashscope_omni_model}")
    print(f"API Key start: {settings.dashscope_api_key[:10]}...")
    
    agent = VetAgent()
    context = AgentContext(
        user_id="test_user",
        user_input="分析这张图片",
        chat_history=[],
        metadata={},
        image_urls=["https://help-static-aliyun-doc.oss-cn-beijing.aliyuncs.com/assets/img/zh-CN/1553018961/p715003.png"] # 示例图片
    )
    
    print("Starting feature extraction...")
    try:
        # 仅测试第一阶段
        result = await agent._execute_omni_feature_extraction(context)
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_multimodal())
