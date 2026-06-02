import cv2
import numpy as np
from fastapi import HTTPException
from sqlmodel import select

from app.api.deps import SessionDep
from app.log import logger
from app.models.device import Device
from app.utils.image_save import save_image


def camera_check(rtsp):
    """
    检查相机连接状态并获取一帧图像
    
    Args:
        rtsp (str): RTSP流地址
        
    Returns:
        tuple: (status, message, image)
            - status (bool): 是否成功获取图像
            - message (str): 状态消息
            - image (numpy.ndarray): 获取的图像，失败时返回白色空白图
    """
    img = np.ones((100, 100, 3), dtype=np.uint8) * 255
    cap = None
    try:
        cap = cv2.VideoCapture(rtsp, cv2.CAP_FFMPEG)
        if not cap.isOpened():
            logger.info("无法打开相机。")
            msg = "无法打开相机。"
            return False, msg, img
        ret, frame = cap.read()
        if ret:
            img_list = [frame[:, :, ::-1]]
            save_image("static/steel_plate_native.jpg", frame)
            msg = "获取图片正常"
            return True, msg, frame
        else:
            logger.info("无法捕获图像。")
            msg = "无法捕获图像。"
            return False, msg, img
    finally:
        if cap is not None:
            cap.release()


def get_device_info(session: SessionDep, ip=None, device_name=None):
    """
    获取设备信息

    Args:
        session: 数据库会话
        ip: 设备IP地址
        device_name: 设备名称

    Returns:
        tuple: (account, password, ip)
            - account (str): 设备账号
            - password (str): 设备密码
            - ip (str): 设备IP地址
    """
    if ip:
        statement = select(Device).where(Device.ip == ip)
    if device_name:
        statement = select(Device).where(Device.name == device_name)
    result = session.exec(statement).all()
    if not result:
        raise HTTPException(status_code=404, detail="device not found")
    account = result[0].account
    password = result[0].password
    ip = result[0].ip
    return account, password, ip
