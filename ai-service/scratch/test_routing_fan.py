import asyncio
import os
import sys

# 添加项目路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

async def test_routing():
    from v1.logic.multi_agent_core import SupervisorAgent
    
    supervisor = SupervisorAgent()
    
    test_inputs = ["开启风扇", "帮我关一下风扇", "查看风扇状态", "监控画面怎么样"]
    
    print("\n" + "="*50)
    print("Supervisor 路由意图识别测试")
    print("="*50)

    for text in test_inputs:
        # 使用 client_id='test' 避免触发真实推送
        route = await supervisor.route(text, client_id="test_client")
        print(f"输入: '{text}' -> 分发至: {route}")
        if route == "hardware_agent":
            print("  [SUCCESS] 路由正确")
        else:
            print("  [FAILED] 路由错误")

    print("\n" + "="*50)

if __name__ == "__main__":
    asyncio.run(test_routing())
