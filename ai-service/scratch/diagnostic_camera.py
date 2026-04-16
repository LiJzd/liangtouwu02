# -*- coding: utf-8 -*-
import cv2
import os
import sys
import time

# 注入系统路径以导入配置
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from v1.common.config import get_settings

def diagnostic_camera():
    settings = get_settings()
    
    # 强制设置基础环境变量以使用 TCP (解决 UDP 被墙或丢包导致的超时)
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
    
    # 常见的各种海康路径格式
    paths = [
        "/Streaming/Channels/101",
        "/h264/ch1/main/av_stream",
        "/live/ch0"
    ]
    
    print(f"[*] 诊断开始...")
    print(f"[*] 目标 IP: {settings.camera_ip} (Ping 已确认可行)")
    print(f"[*] 正在尝试以 TCP 模式连接...")

    for path in paths:
        rtsp_url = f"rtsp://{settings.camera_user}:{settings.camera_password}@{settings.camera_ip}:{settings.camera_rtsp_port}{path}"
        print(f"\n[+] 正在尝试路径: {path}")
        # print(f"    URL: {rtsp_url.replace(settings.camera_password, '******')}")
        
        # 增加超时设置
        cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
        
        start_time = time.time()
        # OpenCV 无法直接设置 VideoCapture 的打开超时，但我们可以检查 isOpened
        if cap.isOpened():
            print(f"    [SUCCESS] 路径 {path} 连接成功！")
            ret, frame = cap.read()
            if ret:
                print(f"    [SUCCESS] 成功读取到画面帧！")
                save_path = os.path.join(os.path.dirname(__file__), f"diag_{path.replace('/', '_')}.jpg")
                cv2.imwrite(save_path, frame)
                print(f"    [INFO] 预览图已保存至: {save_path}")
                cap.release()
                return True
            else:
                print(f"    [WARN] 连接成功但读取帧动作超时或失败。")
        else:
            elapsed = time.time() - start_time
            print(f"    [ERROR] 无法打开流 (耗时 {elapsed:.2f}s)")
        
        cap.release()

    print("\n[!] 所有已知路径尝试失败。")
    print("[?] 建议排查:")
    print("    1. 登录摄像头网页界面 (http://192.168.1.64)，在 [配置] -> [网络] -> [高级配置] -> [集成协议] 中确认是否启用了 [启用ONVIF] 和 [启用RTSP]。")
    print("    2. 部分海康固件需要手动创建一个专用用于 ONVIF/RTSP 的用户，而非直接使用管理员 admin。")
    return False

if __name__ == "__main__":
    diagnostic_camera()
