# -*- coding: utf-8 -*-
"""
测试视频截图识别工具
"""
import asyncio
import sys
import os

# 添加项目路径
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "v1"))

from v1.logic.bot_tools import tool_capture_pig_farm_snapshot


async def test_capture_snapshot():
    """测试视频截图识别功能"""
    print("=" * 60)
    print("测试: 视频截图识别工具")
    print("=" * 60)
    
    # 测试 1: 使用默认参数
    print("\n[测试 1] 使用默认参数截取视频帧...")
    result = await tool_capture_pig_farm_snapshot("")
    print(result)
    
    # 测试 2: 指定置信度阈值
    print("\n[测试 2] 使用自定义置信度 (70%)...")
    result = await tool_capture_pig_farm_snapshot("confidence=70")
    print(result)
    
    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_capture_snapshot())
