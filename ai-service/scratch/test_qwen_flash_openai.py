import os
from openai import OpenAI
from v1.common.config import get_settings

def test_model_openai():
    settings = get_settings()
    api_key = os.environ.get("DASHSCOPE_API_KEY") or settings.dashscope_api_key
    base_url = os.environ.get("DASHSCOPE_BASE_URL") or settings.dashscope_base_url
    model = os.environ.get("DASHSCOPE_MODEL") or settings.dashscope_model
    
    # 强制使用特定环境中的 .env 值进行测试
    print(f"Testing model: {model}")
    print(f"Base URL: {base_url}")
    print(f"Using API Key: {api_key[:10]}...")
    
    client = OpenAI(
        api_key=api_key,
        base_url=base_url
    )
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{'role': 'user', 'content': '你好，请介绍一下你自己。'}],
        )
        print("Success!")
        print("Response:", response.choices[0].message.content)
    except Exception as e:
        print(f"Failed! Error: {e}")

if __name__ == "__main__":
    test_model_openai()
