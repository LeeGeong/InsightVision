"""
相机服务模块

统一管理相机操作，包括：
- 相机连接管理
- 图像采集
- PTZ 控制
- 透视变换

开发者: JJH
"""
import json
import time
from pathlib import Path
from typing import Tuple, Optional, Dict, Any

import cv2
import numpy as np
from sqlmodel import Session, select

from app.api.deps import SessionDep
from app.log import logger
from app.models.device import Device
from app.core.config.settings_v2 import settings


class CameraError(Exception):
    """相机操作异常"""
    pass


class CameraConnectionError(CameraError):
    """相机连接异常"""
    pass


class CameraCaptureError(CameraError):
    """图像采集异常"""
    pass


class CameraService:
    """
    相机服务类
    
    统一管理相机操作，提供图像采集、PTZ 控制等功能
    
    使用方式:
        camera_service = CameraService(session)
        
        # 获取图像
        status, message, image = camera_service.capture_image(rtsp_url)
        
        # 获取相机实例（用于 PTZ 控制）
        camera = camera_service.get_camera_instance(ip)
    """
    
    def __init__(self, session: SessionDep):
        self.session = session
        self._camera_instances: Dict[str, Any] = {}
    
    def get_device_info(self, ip: str = None, device_name: str = None) -> Tuple[str, str, str]:
        """
        获取设备信息

        Args:
            ip: 设备 IP 地址
            device_name: 设备名称

        Returns:
            Tuple[str, str, str]: (account, password, ip)

        Raises:
            CameraError: 设备未找到
        """
        if ip:
            statement = select(Device).where(Device.ip == ip)
        elif device_name:
            statement = select(Device).where(Device.name == device_name)
        else:
            raise CameraError("必须提供 ip 或 device_name")
        
        result = self.session.exec(statement).all()
        
        if not result:
            raise CameraError(f"设备未找到: ip={ip}, device_name={device_name}")
        
        device = result[0]
        return device.account, device.password, device.ip
    
    def get_rtsp_url(self, ip: str, account: str = None, password: str = None, stream: int = 1) -> str:
        """
        生成 RTSP 流地址

        Args:
            ip: 设备 IP 地址
            account: 账号（可选，自动查询）
            password: 密码（可选，自动查询）
            stream: 流编号 (1=主码流, 2=子码流)

        Returns:
            str: RTSP 流地址
        """
        if account is None or password is None:
            account, password, ip = self.get_device_info(ip=ip)
        
        return f"rtsp://{account}:{password}@{ip}/Streaming/Channels/{stream}"
    
    def capture_image(
        self, 
        rtsp: str,
        timeout: int = None
    ) -> Tuple[bool, str, np.ndarray]:
        """
        从 RTSP 流获取一帧图像

        Args:
            rtsp: RTSP 流地址
            timeout: 超时时间（秒）

        Returns:
            Tuple[bool, str, np.ndarray]: (status, message, image)
                - status: 是否成功
                - message: 状态消息
                - image: 图像数据（失败时返回白色空白图）
        """
        if timeout is None:
            timeout = settings.camera.CONNECTION_TIMEOUT
        
        default_img = np.ones((100, 100, 3), dtype=np.uint8) * 255
        cap = None
        
        try:
            cap = cv2.VideoCapture(rtsp, cv2.CAP_FFMPEG)
            
            if not cap.isOpened():
                logger.error(f"无法打开相机: {rtsp}")
                return False, "无法打开相机", default_img
            
            ret, frame = cap.read()
            
            if ret and frame is not None:
                logger.info(f"成功获取图像: shape={frame.shape}")
                return True, "获取图片正常", frame
            else:
                logger.error("无法捕获图像")
                return False, "无法捕获图像", default_img
                
        except Exception as e:
            logger.error(f"相机采集异常: {str(e)}")
            return False, f"相机采集异常: {str(e)}", default_img
            
        finally:
            if cap is not None:
                cap.release()
    
    def capture_from_ip(self, ip: str, stream: int = 1) -> Tuple[bool, str, np.ndarray]:
        """
        根据 IP 地址获取图像（便捷方法）

        Args:
            ip: 设备 IP 地址
            stream: 流编号

        Returns:
            Tuple[bool, str, np.ndarray]: (status, message, image)
        """
        rtsp = self.get_rtsp_url(ip, stream=stream)
        return self.capture_image(rtsp)
    
    def get_camera_instance(self, ip: str):
        """
        获取相机实例（用于 PTZ 控制）

        Args:
            ip: 设备 IP 地址

        Returns:
            Camera_ln: 相机控制实例
        """
        if ip in self._camera_instances:
            return self._camera_instances[ip]
        
        try:
            from app.utils.camera_onvif_ln import Camera_ln
            
            account, password, ip = self.get_device_info(ip=ip)
            camera = Camera_ln(account, password, ip)
            self._camera_instances[ip] = camera
            
            return camera
            
        except Exception as e:
            logger.error(f"获取相机实例失败: {str(e)}")
            raise CameraConnectionError(f"获取相机实例失败: {str(e)}")
    
    def move_to_position(
        self, 
        ip: str, 
        pixel_x: int, 
        pixel_y: int, 
        height: float,
        zoom_level: float = 1.0
    ) -> bool:
        """
        移动相机到指定位置

        Args:
            ip: 设备 IP 地址
            pixel_x: 像素 X 坐标
            pixel_y: 像素 Y 坐标
            height: 高度
            zoom_level: 缩放级别

        Returns:
            bool: 是否成功
        """
        try:
            camera = self.get_camera_instance(ip)
            camera.move_to_xyz(
                pixel_x=pixel_x,
                pixel_y=pixel_y,
                height=height,
                zoom_level=zoom_level
            )
            return True
            
        except Exception as e:
            logger.error(f"相机移动失败: {str(e)}")
            return False
    
    def calculate_zoom_level(
        self,
        detection: Dict[str, Any],
        height: float
    ) -> float:
        """
        计算缩放级别

        Args:
            detection: 检测结果（包含 short_side, long_side 等）
            height: 高度

        Returns:
            float: 缩放级别
        """
        try:
            from app.utils.camera_onvif_ln import Camera_ln
            
            w = detection.get("short_side", 100)
            h = detection.get("long_side", 100)
            
            zoom_level = Camera_ln.calculate_zoom_level_JJH(detection, height)
            return zoom_level
            
        except Exception as e:
            logger.error(f"计算缩放级别失败: {str(e)}")
            return 1.0


class PerspectiveService:
    """
    透视变换服务
    
    管理透视变换配置和操作
    """
    
    def __init__(self):
        self._config: Optional[Dict[str, Any]] = None
        self._load_config()
    
    def _load_config(self):
        """加载透视变换配置"""
        config_path = settings.paths.PERSPECTIVE_CONFIG_PATH
        
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
                logger.info(f"透视变换配置加载成功: {config_path}")
            except Exception as e:
                logger.error(f"透视变换配置加载失败: {str(e)}")
                self._config = {}
        else:
            logger.warning(f"透视变换配置文件不存在: {config_path}")
            self._config = {}
    
    def get_config(self, ip: str) -> Optional[Dict[str, Any]]:
        """
        获取指定 IP 的透视变换配置

        Args:
            ip: 设备 IP 地址

        Returns:
            Optional[Dict]: 透视变换配置
        """
        if not self._config:
            return None
        
        return self._config.get(ip)
    
    def get_perspective_data(self, ip: str) -> Dict[str, Any]:
        """
        获取透视变换数据（M 矩阵和尺寸）

        Args:
            ip: 设备 IP 地址

        Returns:
            Dict: 包含 M, width, height 的字典
        """
        config = self.get_config(ip)
        
        if not config:
            logger.warning(f"未找到 {ip} 的透视变换配置")
            return {"M": None, "width": 1920, "height": 1080}
        
        return {
            "M": np.array(config.get("M")),
            "width": config.get("width", 1920),
            "height": config.get("height", 1080)
        }
    
    def apply_perspective_warp(
        self,
        image: np.ndarray,
        ip: str
    ) -> Tuple[np.ndarray, int, int]:
        """
        应用透视变换

        Args:
            image: 输入图像
            ip: 设备 IP 地址

        Returns:
            Tuple[np.ndarray, int, int]: (变换后图像, 宽度, 高度)
        """
        perspective_data = self.get_perspective_data(ip)
        M = perspective_data.get("M")
        
        if M is None:
            logger.warning(f"未找到 {ip} 的变换矩阵，返回原图")
            return image, image.shape[1], image.shape[0]
        
        try:
            from app.utils.image_utils import perspective_warp
            return perspective_warp(image, M, ip)
        except Exception as e:
            logger.error(f"透视变换失败: {str(e)}")
            return image, image.shape[1], image.shape[0]


def get_camera_service(session: SessionDep) -> CameraService:
    """依赖注入：获取相机服务实例"""
    return CameraService(session)


def get_perspective_service() -> PerspectiveService:
    """依赖注入：获取透视变换服务实例"""
    return PerspectiveService()


if __name__ == "__main__":
    print("CameraService 和 PerspectiveService 模块")
    print("=" * 50)
    print("主要功能:")
    print("  - CameraService: 相机连接、图像采集、PTZ 控制")
    print("  - PerspectiveService: 透视变换配置管理")
    print()
    print("使用示例:")
    print("  camera_service = CameraService(session)")
    print("  status, msg, img = camera_service.capture_from_ip('192.168.3.65')")
