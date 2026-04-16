# -*- coding: utf-8 -*-
import cv2
import os
import sys
import time

def test_new_password():
    target_ip = "192.168.1.102"
    user = "admin"
    verification_code = "YNWWOY"
    original_password = "jhc20260414"
    
    passwords = [verification_code, original_password]
    
    # 强制清理代理
    for key in ['HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'http_proxy', 'https_proxy']:
        os.environ.pop(key, None)
    os.environ['no_proxy'] = '*'

    print(f"[*] 诊断开始...")
    print(f"[*] 目标摄像机: {target_ip}")
    
    for pwd in passwords:
        print(f"\n[+] 正在尝试密码: {pwd}")
        rtsp_url = f"rtsp://{user}:{pwd}@{target_ip}:554/Streaming/Channels/101"
        
        # 强制 TCP 传输
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
        
        cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
        
        start_time = time.time()
        if cap.isOpened():
            print(f"    [SUCCESS] 密码 {pwd} 验证通过！流已打开。")
            ret, frame = cap.read()
            if ret:
                print(f"    [SUCCESS] 画面抓取成功！")
                save_path = os.path.join(os.path.dirname(__file__), f"test_pwd_{pwd}.jpg")
                cv2.imwrite(save_path, frame)
                cap.release()
                return pwd
        else:
            elapsed = time.time() - start_time
            print(f"    [FAILURE] 无法打开流 (耗时 {elapsed:.2f}s)")
        cap.release()
        
    return None

if __name__ == "__main__":
    correct_pwd = test_new_password()
    if correct_pwd:
        print(f"\n[FINAL] 确定正确的 RTSP 密码是: {correct_pwd}")
    else:
        print(f"\n[FINAL] 所有已知密码组合尝试失败。")
