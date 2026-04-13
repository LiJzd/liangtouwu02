import os
import dashscope
from dashscope import MultiModalConversation

def test_mm_structure():
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key: return print("No API key")

    # Mock content
    system_instructions = "You are a vet. Give a long report."
    prompt_body = "Analyze this dummy request."
    
    try:
        # We'll use a public image URL or just text to test structure
        content = [{'text': prompt_body}]
        
        # Test with incremental_output=True
        it = MultiModalConversation.call(
            model='qwen3.5-plus', 
            messages=[
                {'role': 'system', 'content': system_instructions},
                {'role': 'user', 'content': content}
            ],
            stream=True,
            incremental_output=True,
            api_key=api_key
        )
        
        full_text = ""
        for res in it:
            if res.status_code == 200:
                # Print the raw object structure for the first chunk
                if not full_text:
                    print("Chunk Structure:")
                    print(res)
                
                # Check how to extract content
                output = res.output
                if hasattr(output, 'choices') and output.choices:
                    content_obj = output.choices[0].message.content
                    print(f"Content Type: {type(content_obj)}")
                    print(f"Content Sample: {content_obj}")
                    if isinstance(content_obj, list):
                        text = "".join([i.get('text', '') for i in content_obj if isinstance(i, dict)])
                    else:
                        text = str(content_obj)
                    
                    full_text += text
        
        print(f"\nTotal length: {len(full_text)}")
        print(f"Full Text:\n{full_text}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_mm_structure()
