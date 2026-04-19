# -*- coding: utf-8 -*-
import cv2
import os
import sys
import asyncio
import time
import json
import logging

# 注入系统路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from v1.common.config import get_settings

# 模拟 suppress_stderr
import contextlib
@contextlib.contextmanager
def suppress_stderr():
    stderr_fd = sys.stderr.fileno()
    with open(os.devnull, 'w') as devnull:
        old_stderr = os.dup(stderr_fd)
        os.dup2(devnull.fileno(), stderr_fd)
        try:
            yield
        finally:
            os.dup2(old_stderr, stderr_fd)
            os.close(old_stderr)

async def test_capture():
    settings = get_settings()
    rtsp_url = f"rtsp://{settings.camera_user}:{settings.camera_password}@{settings.camera_ip}:{settings.camera_rtsp_port}/Streaming/Channels/101"
    
    print(f"[*] Testing with URL: {rtsp_url.replace(settings.camera_password, '***')}")
    
    # Set identical options as bot_tools.py
    for key in ['HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'http_proxy', 'https_proxy']:
        os.environ.pop(key, None)
    os.environ['no_proxy'] = '*'
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp;stimeout;5000000"
    
    print("[*] Starting VideoCapture with suppress_stderr...")
    start_time = time.time()
    
    with suppress_stderr():
        cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
        if cap.isOpened():
            print(f"[+] Opened in {time.time() - start_time:.2f}s")
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            success, frame = cap.read()
            if success:
                print(f"[+] Read frame in {time.time() - start_time:.2f}s")
            else:
                print(f"[!] Failed to read frame")
            cap.release()
        else:
            print(f"[!] Failed to open in {time.time() - start_time:.2f}s")

if __name__ == "__main__":
    asyncio.run(test_capture())
