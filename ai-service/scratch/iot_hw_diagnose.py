import serial
import time
import sys
import threading

def read_from_port(ser):
    while ser.is_open:
        try:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    print(f"\n[硬件实时反馈] >>> {line}")
                    print("请输入指令 [1/0/s/q]: ", end="", flush=True)
        except Exception as e:
            print(f"\n读取异常: {e}")
            break

def diagnose():
    port = "COM11"
    baud = 115200
    
    print(f"--- 💡 ESP32 硬件链路深度诊断工具 (2.0 多线程版) ---")
    print(f"正在尝试打开串口: {port} (Baud: {baud})...")
    
    try:
        ser = serial.Serial(port, baud, timeout=1)
        print(f"✅ 串口已连接。")
        print(f"提示：此时请按一下 ESP32 上的 [EN/RESET] 按钮，查看是否有启动日志。")
        print("-" * 40)
        
        # 启动背景读取线程
        reader_thread = threading.Thread(target=read_from_port, args=(ser,), daemon=True)
        reader_thread.start()
        
        print("指令说明: 输入 '1' 开启, '0' 关闭, 's' 查询状态, 'q' 退出\n")
        
        while True:
            cmd = input("请输入指令 [1/0/s/q]: ").strip().lower()
            
            if cmd == 'q':
                break
            elif cmd in ['1', '0', 's']:
                ser.write(cmd.encode())
                # 稍微等一下让反馈先打印
                time.sleep(0.1)
            else:
                print("无效指令。")
                
        ser.close()
        print("\n--- 诊断结束 ---")
        
    except serial.SerialException as e:
        print(f"❌ 无法连接串口: {e}")
        print("请检查：1. 串口号是否正确 2. 硬件是否插好 3. main.py 是否已关闭")
    except KeyboardInterrupt:
        print("\n诊断已由用户中断")

if __name__ == "__main__":
    diagnose()

if __name__ == "__main__":
    diagnose()
