import sys
import asyncio

sys.path.insert(0, r"C:\Users\lost\Desktop\两头乌\ai-service")
from v1.logic.bot_tools import tool_capture_pig_farm_snapshot
from v1.common.config import get_settings

settings = get_settings()
settings.camera_use_real = False
video_path = r"C:\Users\lost\Desktop\两头乌\frontend\public\保育-东南角_20250409000000-20250411000000_19.mp4"

async def test():
    args = '{"video_file": "' + video_path.replace("\\", "\\\\") + '"}'
    res = await tool_capture_pig_farm_snapshot(args)
    print("Tool Output:", res)

asyncio.run(test())
