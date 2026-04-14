import os
import dashscope
from dashscope import Generation
from v1.common.config import get_settings

def test_model():
    settings = get_settings()
    api_key = os.environ.get("DASHSCOPE_API_KEY") or settings.dashscope_api_key
    model = os.environ.get("DASHSCOPE_MODEL") or settings.dashscope_model
    
    print(f"Testing model: {model}")
    print(f"Using API Key: {api_key[:10]}...")
    
    dashscope.api_key = api_key
    response = Generation.call(
        model=model,
        messages=[{'role': 'user', 'content': '你好，请介绍一下你自己。'}],
        result_format='message'
    )
    
    if response.status_code == 200:
        print("Success!")
        print("Response:", response.output.choices[0].message.content)
    else:
        print(f"Failed! Code: {response.status_code}, Message: {response.message}")

if __name__ == "__main__":
    test_model()
