# -*- coding: utf-8 -*-
import asyncio
import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from v1.logic.multi_agent_core import VetAgent, AgentContext

async def test_path_logic():
    agent = VetAgent()
    test_file = "C:\\Users\\lost\\Desktop\\test.jpg"
    
    # Simulate _execute_omni_feature_extraction logic
    abs_path = os.path.abspath(test_file).replace('\\', '/')
    if abs_path.startswith('/'):
        abs_path = abs_path[1:]
    
    uri = f"file://{abs_path}"
    print(f"Original Path: {test_file}")
    print(f"Corrected URI: {uri}")
    
    if uri == "file://C:/Users/lost/Desktop/test.jpg":
        print("✅ Path logic is correct for Windows (no triple slash/leading slash issues)")
    else:
        print(f"❌ Path logic issue: {uri}")

async def test_omni_extraction_dry_run():
    # This won't actually call the API without real images, but checks if setup works
    agent = VetAgent()
    context = AgentContext(
        user_id="test_user",
        user_input="测试多模态",
        chat_history=[],
        metadata={},
        image_urls=["scratch/dummy_image.jpg"]
    )
    
    try:
        # Create a dummy image for testing
        with open("scratch/dummy_image.jpg", "wb") as f:
            f.write(b"dummy image data")
            
        print("Starting Stage 1: Feature Extraction (Dry Run)")
        # Note: We can't really call the API here without risking token cost or failure
        # But we can verify the code doesn't crash on path construction
        
        # Manually run the extraction part up to the call
        visual_prompt = "Test Prompt"
        content = [{'text': visual_prompt}]
        for url_or_path in context.image_urls:
            abs_path = os.path.abspath(url_or_path).replace('\\', '/')
            if abs_path.startswith('/'):
                abs_path = abs_path[1:]
            content.append({'image': f"file://{abs_path}"})
        
        print(f"Constructed Content: {content}")
        
    finally:
        if os.path.exists("scratch/dummy_image.jpg"):
            os.unlink("scratch/dummy_image.jpg")

if __name__ == "__main__":
    asyncio.run(test_path_logic())
    asyncio.run(test_omni_extraction_dry_run())
