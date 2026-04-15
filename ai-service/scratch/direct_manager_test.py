import sys
import os
import asyncio
import logging

# 配置日志输出到控制台
logging.basicConfig(level=logging.INFO)

# 添加项目路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

async def test_manager_direct():
    print("\n" + "="*50)
    print("IoTManager 直连测试")
    print("="*50)

    try:
        from v1.logic.iot_controller import iot_manager
        
        print("\n[测试 1] 执行开启操作 ('1')...")
        success = await iot_manager.set_switch(True)
        if success:
            print("[SUCCESS] 指令下发逻辑成功")
        else:
            print("[FAILED] 指令下发失败 (可能是串口未连接或端口错误)")

        print("\n[测试 2] 执行查询操作 ('s')...")
        status = await iot_manager.get_status()
        print(f"当前状态记录: {status}")

    except Exception as e:
        print(f"[ERROR] 测试发生异常: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*50)
    print("请查看上方日志输出中的串口反馈内容。")
    print("="*50)

if __name__ == "__main__":
    asyncio.run(test_manager_direct())
