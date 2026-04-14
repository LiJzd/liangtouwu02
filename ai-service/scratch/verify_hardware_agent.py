import asyncio
import os
import sys

# 添加项目根目录到路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from v1.logic.multi_agent_core import SupervisorAgent, MultiAgentOrchestrator, AgentContext

async def test_minimal():
    from v1.logic.multi_agent_core import SupervisorAgent, MultiAgentOrchestrator
    
    # 1. 测试关键词路由
    supervisor = SupervisorAgent()
    route = await supervisor.route("帮我看下监控")
    print(f"监控指令路由结果: {route}")
    
    # 2. 测试注册
    orchestrator = MultiAgentOrchestrator()
    print(f"已注册 Agent 列表: {list(orchestrator.workers.keys())}")
    
    if "hardware_agent" in orchestrator.workers:
        print("✅ HardwareAgent 注册成功")
    else:
        print("❌ HardwareAgent 注册失败")

if __name__ == "__main__":
    asyncio.run(test_minimal())
