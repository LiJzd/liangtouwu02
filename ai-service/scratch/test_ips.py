import cv2
import os

def test_rtsp(ip):
    url = f"rtsp://admin:jhc20260414@{ip}:554/Streaming/Channels/101"
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp;stimeout;2000000"
    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    if cap.isOpened():
        ret, frame = cap.read()
        cap.release()
        return ret
    return False

if __name__ == "__main__":
    targets = ["192.168.1.64", "192.168.1.102"]
    for ip in targets:
        print(f"[*] 正在测试 {ip} ...")
        if test_rtsp(ip):
            print(f"[SUCCESS] {ip} 画面抓取成功！")
        else:
            print(f"[FAILURE] {ip} 无法连接。")
