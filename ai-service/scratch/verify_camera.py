# -*- coding: utf-8 -*-
import cv2
import os
import sys

# 注入系统路径以导入配置
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from v1.common.config import get_settings

def verify_camera():
    settings = get_settings()
    
    # 构造 RTSP URL
    # 海康标准格式: rtsp://admin:password@ip:554/Streaming/Channels/101
    rtsp_url = f"rtsp://{settings.camera_user}:{settings.camera_password}@{settings.camera_ip}:{settings.camera_rtsp_port}/Streaming/Channels/101"
    
    # 1. 彻底屏蔽代理干扰
    for key in ['HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'http_proxy', 'https_proxy']:
        os.environ.pop(key, None)
    os.environ['no_proxy'] = '*'

    # 2. 强制使用 TCP 传输模式，提高局域网稳定性
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp;stimeout;5000000"

    print(f"[*] 正在尝试连接摄像头...")
    print(f"[*] 目标地址: {settings.camera_ip}")
    print(f"[*] RTSP URL: {rtsp_url.replace(settings.camera_password, '******')}") # 隐藏密码打印
    
    cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
    
    if not cap.isOpened():
        print("[!] 错误: 无法打开 RTSP 流。请检查：")
        print(f"    1. 电脑是否能 ping 通 {settings.camera_ip}")
        print(f"    2. 账号密码是否正确")
        print(f"    3. 摄像头是否开启了预览权限")
        return False
    
    print("[+] 连接成功！正在抓取一帧画面...")
    
    # 设置缓冲区
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    
    # 读取一帧
    ret, frame = cap.read()
    
    if ret and frame is not None:
        save_path = os.path.join(os.path.dirname(__file__), "camera_test_snapshot.jpg")
        
        # 修复：OpenCV 的 imwrite 在中文路径下可能会失败
        # 使用 imencode + 写入字节流的方式来规避路径编码问题
        try:
            success, buffer = cv2.imencode(".jpg", frame)
            if success:
                with open(save_path, "wb") as f:
                    f.write(buffer)
                print(f"[+] 抓拍成功！画面已保存至: {save_path}")
                print(f"[+] 画面尺寸: {frame.shape[1]}x{frame.shape[0]}")
                return True
            else:
                print("[!] 错误: 图像编码失败。")
                return False
        except Exception as e:
            print(f"[!] 错误: 保存文件时发生异常: {e}")
            return False
    else:
        print("[!] 错误: 连接成功但无法读取数据帧。")
        return False

if __name__ == "__main__":
    success = verify_camera()
    if success:
        print("\n[SUCCESS] 摄像头接入验证通过！")
    else:
        print("\n[FAILURE] 摄像头接入验证失败。")
