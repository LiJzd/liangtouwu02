import os
import dashscope
from dashscope import MultiModalConversation

def test_multimodal_path():
    # Set your API key if needed, or it might be in env
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        print("Please set DASHSCOPE_API_KEY environment variable.")
        return

    # Create a dummy image
    from PIL import Image
    import tempfile
    
    img = Image.new('RGB', (100, 100), color = 'red')
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as t:
        p = t.name
        img.save(p)
    
    print(f"Temporary file created at: {p}")
    
    # Try different path formats
    abs_p = os.path.abspath(p)
    formats = [
        abs_p,
        abs_p.replace('\\', '/'),
        f"file:///{abs_p.replace('\\', '/')}"
    ]
    
    for fmt in formats:
        print(f"\nTesting format: {fmt}")
        content = [{'image': fmt}, {'text': 'What is in this image?'}]
        try:
            responses = MultiModalConversation.call(
                model='qwen-vl-plus', # or any other mm model
                messages=[{'role': 'user', 'content': content}],
                api_key=api_key
            )
            print(f"Status Code: {responses.status_code}")
            if responses.status_code != 200:
                print(f"Message: {responses.message}")
        except Exception as e:
            print(f"Error with format {fmt}: {e}")

    # Cleanup
    if os.path.exists(p):
        os.remove(p)

if __name__ == "__main__":
    test_multimodal_path()
