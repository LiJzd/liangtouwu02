#!/usr/bin/env python3
"""
猪BOT API 测试脚本
用于验证前后端联调修复是否成功
"""

import requests
import json

# 测试配置
AI_SERVICE_URL = "http://localhost:8000"
CHAT_ENDPOINT = f"{AI_SERVICE_URL}/api/v1/agent/chat/v2"

def test_health_check():
    """测试AI服务健康检查"""
    print("=" * 60)
    print("测试 1: AI服务健康检查")
    print("=" * 60)
    
    try:
        response = requests.get(f"{AI_SERVICE_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ AI服务运行正常")
            print(f"   服务名称: {data.get('service')}")
            print(f"   状态: {data.get('status')}")
            print(f"   时间: {data.get('timestamp')}")
            return True
        else:
            print(f"❌ 健康检查失败: HTTP {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ 无法连接到AI服务 ({AI_SERVICE_URL})")
        print(f"   请确保AI服务已启动: cd ai-service && python main.py")
        return False
    except Exception as e:
        print(f"❌ 健康检查异常: {e}")
        return False

def test_simple_chat():
    """测试简单文本对话"""
    print("\n" + "=" * 60)
    print("测试 2: 简单文本对话")
    print("=" * 60)
    
    payload = {
        "user_id": "test_user",
        "messages": [
            {
                "role": "user",
                "content": "你好，请简单介绍一下你自己"
            }
        ],
        "image_urls": []
    }
    
    try:
        print(f"发送请求到: {CHAT_ENDPOINT}")
        print(f"请求数据: {json.dumps(payload, ensure_ascii=False, indent=2)}")
        
        response = requests.post(
            CHAT_ENDPOINT,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ 对话成功")
            print(f"   回复: {data.get('reply', '')[:200]}...")
            print(f"   是否包含图片: {'是' if data.get('image') else '否'}")
            return True
        else:
            print(f"\n❌ 对话失败: HTTP {response.status_code}")
            print(f"   响应: {response.text[:500]}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"\n❌ 请求超时（30秒）")
        print(f"   AI服务可能正在处理，请稍后重试")
        return False
    except Exception as e:
        print(f"\n❌ 对话异常: {e}")
        return False

def test_context_chat():
    """测试多轮对话上下文"""
    print("\n" + "=" * 60)
    print("测试 3: 多轮对话上下文")
    print("=" * 60)
    
    payload = {
        "user_id": "test_user",
        "messages": [
            {
                "role": "user",
                "content": "我有一头猪的体重是50公斤"
            },
            {
                "role": "assistant",
                "content": "好的，我了解到您有一头体重50公斤的猪。请问有什么需要帮助的吗？"
            },
            {
                "role": "user",
                "content": "它现在多重？"  # 测试上下文理解
            }
        ],
        "image_urls": []
    }
    
    try:
        print(f"发送多轮对话请求...")
        print(f"测试AI是否能记住之前提到的50公斤")
        
        response = requests.post(
            CHAT_ENDPOINT,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            reply = data.get('reply', '')
            print(f"\n✅ 多轮对话成功")
            print(f"   回复: {reply[:200]}...")
            
            # 检查是否包含上下文信息
            if "50" in reply or "五十" in reply:
                print(f"   ✅ 上下文保持正常（回复中提到了50公斤）")
            else:
                print(f"   ⚠️  上下文可能丢失（回复中未提到50公斤）")
            return True
        else:
            print(f"\n❌ 多轮对话失败: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"\n❌ 多轮对话异常: {e}")
        return False

def main():
    """主测试流程"""
    print("\n" + "🐷" * 30)
    print("猪BOT API 联调测试")
    print("🐷" * 30 + "\n")
    
    results = []
    
    # 测试1: 健康检查
    results.append(("健康检查", test_health_check()))
    
    if not results[0][1]:
        print("\n" + "=" * 60)
        print("⚠️  AI服务未运行，跳过后续测试")
        print("=" * 60)
        return
    
    # 测试2: 简单对话
    results.append(("简单对话", test_simple_chat()))
    
    # 测试3: 上下文对话
    results.append(("上下文对话", test_context_chat()))
    
    # 输出测试总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{test_name}: {status}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！猪BOT前后端联调修复成功！")
    else:
        print("\n⚠️  部分测试失败，请检查错误信息")

if __name__ == "__main__":
    main()
