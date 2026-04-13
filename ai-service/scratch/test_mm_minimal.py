import os
import dashscope
from dashscope import MultiModalConversation

def test_mm_minimal():
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key: return print("No API key")

    # Use a real public image for testing
    img_url = "https://dashscope.oss-cn-beijing.aliyuncs.com/images/dog_and_girl.jpeg"
    prompt = "Describe the image."
    
    try:
        content = [{'image': img_url}, {'text': prompt}]
        
        it = MultiModalConversation.call(
            model='qwen3.5-plus', 
            messages=[{'role': 'user', 'content': content}],
            stream=True,
            incremental_output=True,
            api_key=api_key
        )
        
        full_text = ""
        for res in it:
            if res.status_code == 200:
                text = ""
                choices = res.output.choices
                if choices:
                    content_obj = choices[0].message.content
                    if isinstance(content_obj, list):
                        text = "".join([i.get('text', '') for i in content_obj if isinstance(i, dict)])
                    else:
                        text = str(content_obj)
                
                # In incremental_output=True, 'text' should be the delta? 
                # Actually for MM it might be the whole thing so far.
                print(f"[{len(full_text)}] -> {text}")
                full_text = text
        
        print(f"\nFinal Result:\n{full_text}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_mm_minimal()
