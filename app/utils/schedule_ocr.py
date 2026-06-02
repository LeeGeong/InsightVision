import sys
import os
import cv2
from ultralytics import YOLO
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(current_dir)
sys.path.append(parent_dir)

import time
from datetime import datetime
import requests
from camera_onvif import Camera
import math
from loguru import logger

"""
定时采集ocr图片程序 
"""

# 配置日志记录
logger.add("camera_capture.log", 
           format="{time:YYYY-MM-DD HH:mm:ss} - {level} - {message}",
           level="INFO",
           rotation="10 MB",
           retention="7 days",
           encoding="utf-8")

# 假设这是华为相机的API接口
CAMERA_IP = '192.168.3.55'
CAMERA_USER = 'admin'
CAMERA_PASSWORD = 'Bgitv45654'
SAVE_PATH = './ocr_data/'
IMAGE_FORMAT = 'jpg'  # 可以根据需要修改为jpeg/png等
# rtsp = "rtsp://admin:Bgitv45654@192.168.3.55:554/LiveMedia/ch1/Media1/trackID=1"
rtsp = "rtsp://192.168.3.55:554/LiveMedia/ch1/Media1"
# 加载YOLO模型
model = YOLO(r".\best.pt")
camera = Camera(CAMERA_IP, CAMERA_USER, CAMERA_PASSWORD, 0, 0)
camera.connect_ONVIF()


local_list = [
    [-0.712222219, -0.0220952351, 0.189999998],
    [-0.832222223, -0.347809494, 0.148636356],
    [-0.395611078, -0.387999982, 0.114090912],
    [-0.467222244, -0.0868571699, 0.232272729],
    [0.104999997, -0.643238008, 0.109090917],
    [0.313888878, -0.285142869, 0.106818177],
    [0.618888915,-0.113714308,0.110909097],
    # [0.728333354, -0.286857158, 0.102727272],
    [0.789999962, -0.422095239, 0.104999997]
]

# 确保保存图片的目录存在
if not os.path.exists(SAVE_PATH):
    os.makedirs(SAVE_PATH)


# 获取当前时间的文件名
def get_file_name():
    return CAMERA_IP + '_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.' + IMAGE_FORMAT


# 连接相机并获取图片的函数
def capture_image():
    try:
        # 模拟相机API请求，返回图像数据
        # 这里假设相机有一个GET接口，使用基本认证获取图片

        for local in local_list:
            camera.ptz_absolute_move(local[0], local[1], local[2])
            time.sleep(3)
            file_name = get_file_name()
            file_path = os.path.join(SAVE_PATH, file_name)
            # image_data = camera.get_picture()
            cap = cv2.VideoCapture(rtsp, cv2.CAP_FFMPEG)
            ret, frame = cap.read()
            if ret:
                results = model.predict(
                    source=frame,  # 输入图像路径
                    conf=0.3,  # 置信度阈值
                    iou=0.4,  # IoU 阈值
                    imgsz=640,  # 图像大小
                    half=False,  # 使用半精度推理
                    device=None,  # 使用设备，None表示自动选择，比如'cpu','0'
                    max_det=1000,  # 最大检测数量
                    save=False,  # 保存推理结果
                    save_txt=False,  # 保存检测结果到文本文件
                    save_conf=False,  # 保存置信度到文本文件
                    show=False,  # 是否显示推理图像
                )
                if len(results[0].obb.cls > 0):
                    cv2.imwrite(file_path, frame)
                    logger.info(f"Image saved successfully: {file_path}")
                else:
                    logger.info(f"Image is rubbish")
                cap.release()
            else:
                cap = cv2.VideoCapture(rtsp, cv2.CAP_FFMPEG)





    except requests.RequestException as e:
        logger.error(f"Error connecting to the camera: {e}")
    except Exception as e:
        logger.error(f"Unexpected error during image capture: {e}")


# 定时任务，每20分钟执行一次
def schedule_capture(interval_minutes=20):
    while True:
        try:
            capture_image()
        except Exception as e:
            logger.error(f"Error during scheduled capture: {e}")

        # 等待下次执行
        time.sleep(interval_minutes * 60)


if __name__ == '__main__':
    schedule_capture()
