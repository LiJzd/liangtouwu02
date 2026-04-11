import asyncio
import sys
import os
from unittest.mock import MagicMock, AsyncMock

# 设置路径以导入 v1
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), "..")))

from v1.logic.multi_agent_core import VetAgent, AgentContext, AgentResult

async def verify_fix():
    print("开始验证 VetAgent._execute_multimodal_two_stage 逻辑修复...")
    
    agent = VetAgent()
    
    # 模拟 context
    context = AgentContext(
        user_id="test",
        user_input="测试",
        chat_history=[],
        metadata={},
        client_id="test_client",
        image_urls=["test.jpg"]
    )
    
    # Mock 阶段 1 和阶段 2 的具体执行方法，以避免网络调用
    agent._execute_omni_feature_extraction = AsyncMock(return_value="这是测试图片描述，包含结论。")
    agent._execute_with_more_iterations = AsyncMock(return_value=AgentResult(
        success=True,
        answer="这是最终诊断。",
        worker_name="vet_agent",
        thoughts=["Thought 1"]
    ))
    # Mock 预处理和 debug 推送
    agent._preprocess_image = MagicMock(return_value="path/to/img.jpg")
    from v1.logic import agent_debug_controller
    agent_debug_controller.push_debug_event = AsyncMock()
    
    print("调用 _execute_multimodal_two_stage...")
    result = await agent._execute_multimodal_two_stage(context)
    
    print(f"返回值类型: {type(result)}")
    if result is None:
        print("错误：返回值仍为 None！修复失败。")
        sys.exit(1)
    else:
        print(f"成功：返回值不为 None。结果内容: {result.answer}")
        
    print("验证完成。")

if __name__ == "__main__":
    asyncio.run(verify_fix())
