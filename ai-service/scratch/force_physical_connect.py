# -*- coding: utf-8 -*-
import socket
import os
import cv2
import time

def test_physical_direct():
    target_ip = "192.168.1.64"
    local_ip = "192.168.1.13" # 您的物理以太网 IP
    port = 554
    
    # 1. 彻底清除代理环境变量，确保应用层直连
    for key in ['HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'http_proxy', 'https_proxy']:
        os.environ.pop(key, None)
    os.environ['no_proxy'] = '*' # 禁止所有代理尝试

    print(f"[*] 诊断开始...")
    print(f"[*] 强制物理源地址: {local_ip}")
    print(f"[*] 强制禁用代理环境...")

    # 2. 尝试低级 Socket 握手（强制绑定网卡）
    print(f"[*] 步骤 1: 尝试 TCP 物理握手...")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5)
    try:
        s.bind((local_ip, 0)) # 强制走以太网这块卡
        s.connect((target_ip, port))
        print(f"[SUCCESS] 物理网卡与摄像头握手成功！链路已打通。")
        s.close()
    except Exception as e:
        print(f"[ERROR] 物理链路不通: {e}")
        print("请检查：网线是否插紧？路由器或交换机是否正常？")
        print(f"建议操作：请尝试拔掉 WiFi，再次运行此脚本。")
        return

    # 3. 尝试 OpenCV 抓流（配合 TCP 传输选项）
    print(f"\n[*] 步骤 2: 尝试抓取视频流...")
    # 设置环境变量以强制 OpenCV 使用 TCP 传输
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
    
    rtsp_url = f"rtsp://admin:jhc20260414@{target_ip}:554/Streaming/Channels/101"
    
    # 使用 cv2.CAP_FFMPEG 明确后端
    cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
    
    start_time = time.time()
    if cap.isOpened():
        print("[SUCCESS] 摄像头视频流已成功打开！")
        # 针对高延迟或初始帧缓慢，尝试多次读取
        for _ in range(5):
            ret, frame = cap.read()
            if ret and frame is not None:
                save_path = os.path.join(os.path.dirname(__file__), "physical_test_ok.jpg")
                cv2.imwrite(save_path, frame)
                print(f"[SUCCESS] 画面抓取成功，已保存至: {save_path}")
                break
            time.sleep(0.5)
        cap.release()
    else:
        elapsed = time.time() - start_time
        print(f"[ERROR] 虽然 TCP 通了，但 OpenCV 无法解析流 (耗时 {elapsed:.2f}s)。")
        print("可能原因：账号密码(jhc20260414)错误，或摄像头里关闭了 RTSP 服务。")

if __name__ == "__main__":
    test_physical_direct()
