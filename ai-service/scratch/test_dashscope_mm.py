import dashscope
from dashscope import MultiModalConversation, Generation
import os
from dotenv import load_dotenv

load_dotenv(r"C:\Users\lost\Desktop\两头乌\ai-service\.env")

api_key = os.environ.get("DASHSCOPE_API_KEY")
model = os.environ.get("DASHSCOPE_MODEL")

print(f"Testing model: {model}")

def test_multimodal():
    print("\n--- Testing MultiModalConversation ---")
    messages = [{'role': 'user', 'content': [{'text': 'Hello, who are you?'}]}]
    response = MultiModalConversation.call(
        model=model,
        messages=messages,
        api_key=api_key,
    )
    print(f"Response Status: {response.status_code}")
    print(f"Response Code: {response.code}")
    print(f"Response Message: {response.message}")
    if response.status_code == 200:
        print(f"Output: {response.output.choices[0].message.content}")
    else:
        print(f"Full Response: {response}")

def test_generation_list_format():
    print("\n--- Testing Generation with list format ---")
    messages = [{'role': 'user', 'content': [{'text': 'Hello, who are you?'}]}]
    response = Generation.call(
        model=model,
        messages=messages,
        api_key=api_key,
        result_format='message'
    )
    print(f"Response Status: {response.status_code}")
    if response.status_code == 200:
        print(f"Output: {response.output.choices[0].message.content}")
    else:
        print(f"Full Response: {response}")

if __name__ == "__main__":
    test_multimodal()
    test_generation_list_format()
