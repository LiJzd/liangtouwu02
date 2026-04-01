import re

with open('v1/logic/bot_tools.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace any garbled string on the capture_pig_farm_snapshot decorator
# Find: @tool(name="capture_pig_farm_snapshot", description="..."
pattern = re.compile(r'@tool\(name="capture_pig_farm_snapshot",\s*description="[^"]*"\)')
content = pattern.sub('@tool(name="capture_pig_farm_snapshot", description="截取猪场视频图像并进行 AI 识别，返回检测到的猪只位置和状态")', content)

with open('v1/logic/bot_tools.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Replacement done!")
