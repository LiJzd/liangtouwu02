"""
测试多智能体架构
验证 Supervisor 路由和 Worker 执行
"""
import asyncio
import httpx


async def test_multi_agent_chat(question: str):
    """测试多智能体对话"""
    url = "http://localhost:8000/api/v1/agent/chat/v2"
    
    payload = {
        "user_id": "test_user_multi",
        "messages": [
            {
                "role": "system",
                "content": "你是掌上明猪的智能助手"
            },
            {
                "role": "user",
                "content": question
            }
        ],
        "metadata": {
            "channel": "test",
            "source": "pytest"
        }
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        print(f"\n📤 问题: {question}")
        response = await client.post(url, json=payload)
        print(f"📥 响应状态: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 回复: {data.get('reply')}")
        else:
            print(f"❌ 请求失败: {response.text}")


async def test_supervisor_routing():
    """测试 Supervisor 路由逻辑"""
    test_cases = [
        ("我的猪场有哪些猪？", "data_agent"),
        ("猪拉稀了怎么办？", "vet_agent"),
        ("看看猪场现场情况", "perception_agent"),
        ("你好", "direct_reply"),
        ("今天天气怎么样", "direct_reply"),
    ]
    
    print("\n" + "=" * 60)
    print("🧪 测试 Supervisor 路由")
    print("=" * 60)
    
    for question, expected_worker in test_cases:
        print(f"\n问题: {question}")
        print(f"期望路由: {expected_worker}")
        await test_multi_agent_chat(question)
        await asyncio.sleep(1)  # 避免 API 限流


async def test_worker_execution():
    """测试 Worker 执行"""
    test_cases = [
        {
            "name": "DataAgent - 列出猪只",
            "question": "我的猪场有哪些猪？"
        },
        {
            "name": "DataAgent - 查询档案",
            "question": "查询 PIG001 的档案"
        },
        {
            "name": "PerceptionAgent - 截图识别",
            "question": "看看猪场现场有多少猪"
        },
        {
            "name": "VetAgent - 疾病诊断",
            "question": "猪不吃食，精神不好，怎么办？"
        },
    ]
    
    print("\n" + "=" * 60)
    print("🧪 测试 Worker 执行")
    print("=" * 60)
    
    for case in test_cases:
        print(f"\n【{case['name']}】")
        await test_multi_agent_chat(case["question"])
        await asyncio.sleep(2)


if __name__ == "__main__":
    print("=" * 60)
    print("🧪 多智能体架构测试")
    print("=" * 60)
    print("\n提示：请先启动 FastAPI 服务 (python main.py)\n")
    
    # 测试 1: Supervisor 路由
    asyncio.run(test_supervisor_routing())
    
    # 测试 2: Worker 执行
    print("\n\n按 Enter 继续测试 Worker 执行...")
    input()
    asyncio.run(test_worker_execution())
    
    print("\n\n✅ 测试完成")
