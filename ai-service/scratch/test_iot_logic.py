# -*- coding: utf-8 -*-
import sys
import os
import asyncio

# 添加项目路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

async def test_iot_commands():
    print("--- 开始测试 IOT 控制逻辑 ---")
    try:
        from v1.logic.iot_controller import IoTManager
        iot = IoTManager()
        
        print("\n[测试1] 发送开启指令 (ON)...")
        # 拦截 send_command 以便在此打印字节
        original_send = iot.send_command
        
        async def mock_send(cmd_bytes):
            print(f"生成的字节流: {bytes(cmd_bytes).hex().upper()}")
            # 预期: A4 09 FF 00 00 37 37 37 37 37 37
            return True
        
        iot.send_command = mock_send
        await iot.set_switch(True)
        
        print("\n[测试2] 发送关闭指令 (OFF)...")
        await iot.set_switch(False)
        # 预期: A4 09 00 00 00 37 37 37 37 37 37
        
        print("\n[测试3] 状态查询指令...")
        async def mock_send_status(cmd_bytes):
            print(f"生成的字节流: {bytes(cmd_bytes).hex().upper()}")
            # 预期: A5 00
            return True
            
        iot.send_command = mock_send_status
        await iot.get_status()
        
        print("\n--- 测试完成: 指令构造正确 ---")
        
    except Exception as e:
        print(f"测试过程中出现异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_iot_commands())
