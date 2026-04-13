import asyncio
import os
import sys

# 添加项目路径
sys.path.append(r"c:\Users\lost\Desktop\两头乌\ai-service")

# 模拟配置环境
os.environ["DASHSCOPE_API_KEY"] = "sk-..." # 实际上系统中应该已经有配置了

from v1.logic.multi_agent_core import SupervisorAgent

async def test_routing():
    supervisor = SupervisorAgent()
    
    test_cases = [
        "猪最近长得怎么样？",
        "查询编号为 PIG123 的健康状态",
        "今天有什么出栏报表吗？",
        "有只猪在咳嗽，怎么办？",
        "你好啊",
    ]
    
    print("--- 路由测试开始 ---")
    for case in test_cases:
        route = await supervisor.route(case)
        print(f"输入: {case} -> 路由: {route}")
    print("--- 路由测试结束 ---")

if __name__ == "__main__":
    asyncio.run(test_routing())
