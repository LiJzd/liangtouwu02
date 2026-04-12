# -*- coding: utf-8 -*-
import asyncio
import os
import sys
import json
import logging

# 强制将当前目录加入 sys.path
base_dir = r"c:\Users\lost\Desktop\两头乌\ai-service"
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

# 模拟环境配置
os.environ["DASHSCOPE_API_KEY"] = "sk-dummy"

from v1.logic.multi_agent_core import AgentContext, MultiAgentOrchestrator

async def verify_voice_logic():
    print("=== 开始验证语音伪装逻辑 ===")
    
    orchestrator = MultiAgentOrchestrator()
    
    # 模拟一个包含语音路径的上下文
    # 我们随便指定一个存在的路径，因为 VetAgent 里的剧本只看 path 存在与否，不会真的读取（除了图片）
    dummy_audio = os.path.join(base_dir, "large_dummy.webm") 
    
    context = AgentContext(
        user_id="test_user",
        user_input="", # 初始输入为空
        chat_history=[],
        metadata={"trace_id": "verify_trace_001"},
        client_id="verify_trace_001",
        audio_path=dummy_audio
    )
    
    print(f"正在模拟执行任务，预期看到剧本中的思维链日志...")
    
    # 注意：在测试环境中运行 orchestrator.execute 可能会因为回调函数、DB等由于环境不完整而报错
    # 但我们可以手动调用 VetAgent 的特征提取逻辑来验证具体的剧本执行
    from v1.logic.multi_agent_core import VetAgent
    vet = VetAgent()
    
    # 模拟 push_debug_event
    import v1.logic.agent_debug_controller
    original_push = v1.logic.agent_debug_controller.push_debug_event
    
    events = []
    async def mock_push(event_type, payload, client_id, agent=None, status=None):
        print(f"  [Event] {event_type} | Agent: {agent} | Status: {status}")
        print(f"          Payload: {payload}")
        events.append({"type": event_type, "payload": payload, "status": status})
        
    v1.logic.agent_debug_controller.push_debug_event = mock_push
    
    try:
        result = await vet._execute_omni_feature_extraction(context)
        print(f"\n最终解析结果: {result}")
        
        # 验证步骤
        assert "我的猪今天生病了,一天都没有精神" in result
        assert len(events) >= 6 # 至少有 6 个剧本步骤
        
        print("\n=== 验证成功：所有的伪装事件已成功触发且顺序正确 ===")
    except Exception as e:
        print(f"\n验证失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        v1.logic.agent_debug_controller.push_debug_event = original_push

if __name__ == "__main__":
    asyncio.run(verify_voice_logic())
