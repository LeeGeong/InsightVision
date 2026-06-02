# =====================================================================
# 公司名称：锐创理工
# 项目名称：
# 模块名称：相机跟随
# 开发人员：JJH
# 开发日期：2022.8.12
# 功能简介：
# 当前版本：0.0.1
# 修改时间：
# 修改人员：
# =====================================================================

import math
from math import degrees, atan2, asin

import numpy as np
from onvif import ONVIFCamera

# from ..log import logger
from app.log import logger


def ptz_to_angles(ptz_pan, ptz_tilt):
    """将 PTZ 值映射到角度（度）"""
    pan_angle = (ptz_pan + 1.0) / 2.0 * 360.0
    pan_angle = pan_angle % 360.0
    tilt_angle = 90.0 - (ptz_tilt + 1.0) / 2.0 * (90.0 - (-15.0))
    return pan_angle, tilt_angle


def angles_to_ptz(pan_deg, tilt_deg):
    """将角度（度）映射到 PTZ 值"""
    ptz_pan = (pan_deg / 360.0) * 2.0 - 1.0
    ptz_tilt = -((tilt_deg + 15.0) / (90.0 + 15.0) * 2.0 - 1.0)
    return ptz_pan, ptz_tilt


def compute_ptz_from_3d_point(world_point, R, t, camera_location):
    """
    根据3D世界坐标点计算对应的PTZ参数

    参数:
        world_point: 3D世界坐标点，可以是列表或numpy数组，形状 (3,)
        R: 旋转矩阵，形状 (3,3) - 世界坐标系到相机坐标系
        t: 平移向量，形状 (3,) - 使得 x_cam = R*P + t
        camera_location: 相机位置，形状 (3,) - 世界坐标系中的位置

    返回:
        tuple: (ptz_pan, ptz_tilt) - 计算得到的PTZ参数

    异常:
        ValueError: 如果点与相机位置重合

    示例:
        # >>> # 已知相机外参
        # >>> R = [[0.9912, 0.1269, -0.0371], [0.1277, -0.9916, 0.0191], [-0.0344, -0.0237, -0.9991]]
        # >>> t = [-85946.53, 413404.50, 26554.11]
        # >>> camera_loc = [33307, 421483, 15425]
        # >>>
        # >>> # 计算3D点的PTZ
        # >>> world_pt = [42380, 426130, 600]
        # >>> ptz_pan, ptz_tilt = compute_ptz_from_3d_point(world_pt, R, t, camera_loc)
        # >>> print(f"PTZ: [{ptz_pan:.6f}, {ptz_tilt:.6f}]")
    """
    # 转换为numpy数组
    world_point = np.asarray(world_point, dtype=float)
    camera_location = np.asarray(camera_location, dtype=float)
    R = np.asarray(R, dtype=float)
    t = np.asarray(t, dtype=float)

    # 验证输入形状
    if world_point.shape != (3,):
        raise ValueError(f"world_point 必须是3维向量，当前形状: {world_point.shape}")
    if R.shape != (3, 3):
        raise ValueError(f"R 必须是3x3矩阵，当前形状: {R.shape}")
    if t.shape != (3,):
        raise ValueError(f"t 必须是3维向量，当前形状: {t.shape}")
    if camera_location.shape != (3,):
        raise ValueError(f"camera_location 必须是3维向量，当前形状: {camera_location.shape}")

    # 步骤1：计算从相机到点的方向向量（世界坐标系）
    vec_cam_to_point = world_point - camera_location
    norm = np.linalg.norm(vec_cam_to_point)
    if norm == 0:
        raise ValueError("点与相机位置重合，无法计算方向")

    # 单位化方向向量
    direction_world = vec_cam_to_point / norm

    # 步骤2：使用旋转矩阵将方向向量转换到相机坐标系
    direction_camera = R @ direction_world

    # 单位化（确保数值稳定性）
    direction_camera = direction_camera / np.linalg.norm(direction_camera)

    # 步骤3：根据相机坐标系中的方向向量计算pan和tilt角度
    dx, dy, dz = direction_camera

    # 计算pan角度（水平角度）
    pan_rad = atan2(dy, dx)
    pan_deg = degrees(pan_rad)

    # 确保pan角度在0-360°范围内
    if pan_deg < 0:
        pan_deg += 360.0

    # 计算tilt角度（垂直角度）
    dz_clipped = np.clip(dz, -1.0, 1.0)
    tilt_rad = asin(dz_clipped)
    tilt_deg = degrees(tilt_rad)

    # 步骤4：将角度转换为PTZ参数
    ptz_pan, ptz_tilt = angles_to_ptz(pan_deg, tilt_deg)

    return ptz_pan, ptz_tilt


# 垂直的角度，25-56左右
class Camera_ln(object):
    def __init__(self, ip, user, password, topic, local_x=0, local_z=0, camera_type='default'):
        # 垂直视场角 56°
        # self.FOV_vertical = 48
        # self.FOV_horizontal = 90

        # 初始视场角（zoom=0时的视场角）
        self.max_FOV_vertical = 35.3  # 最大垂直视场角（最小zoom时）
        self.max_FOV_horizontal = 60.9  # 最大水平视场角（最小zoom时）
        self.min_FOV_vertical = 1.2  # 最小垂直视场角（最大zoom时）
        self.min_FOV_horizontal = 2  # 最小水平视场角（最大zoom时）

        self.current_FOV_vertical = self.max_FOV_vertical
        self.current_FOV_horizontal = self.max_FOV_horizontal
        self.ip = ip
        self.user = user
        self.password = password
        self.local_x = local_x
        self.local_z = local_z
        self.topic = topic

        self.image_width = 3840  # 图像宽度
        self.image_height = 2160  # 图像高度
        self.pantilt_x = 0  # 当前水平角度（ONVIF坐标）
        self.pantilt_y = 0  # 当前垂直角度（ONVIF坐标）
        self.ptz_speed = 0.5

    def connect_ONVIF(self):
        mycam = ONVIFCamera(self.ip, 80, self.user, self.password, wsdl_dir='./wsdl')
        self.media = mycam.create_media_service()
        self.ptz = mycam.create_ptz_service()
        self.device = mycam.create_devicemgmt_service()
        return

    # 初始化相机位置 归零（视野上边缘水平为归零）
    def init_camera_location(self):
        self.get_camera_location()  # 获取当前相机位置，得到x位置
        init_angle = self.FOV_vertical / 2
        init_location = 1 - round(init_angle / 90 * 2, 2)
        self.ptz_absolute_move(init_location)
        return

    # 获取当前相机信息
    def get_device_info(self):
        device_info = self.device.GetDeviceInformation()
        return device_info

    def get_picture(self):
        media_service = self.media
        # 获取相机的视频流配置
        profiles = media_service.GetProfiles()
        profile = profiles[0]  # 默认选择第一个profile

        # 获取抓拍图像
        request = media_service.create_type('GetSnapshotUri')
        request.ProfileToken = profile.token
        snapshot_uri = media_service.GetSnapshotUri(request)
        image_url = snapshot_uri.Uri

        # 获取图像数据
        from urllib import request as urllib_request
        response = urllib_request.urlopen(image_url)
        image_data = response.read()
        return image_data

    # 活动相机当前位姿
    def get_camera_location(self):
        media_profile = self.media.GetProfiles()[0]
        ProfileToken = media_profile.token
        status = self.ptz.GetStatus({'ProfileToken': ProfileToken})

        # 相机位姿 Y 1~ -1 对应 0 ~ 90
        self.pantilt_x = status.Position.PanTilt.x
        pantilt_y = status.Position.PanTilt.y
        logger.info(f"当前相机位置X：{self.pantilt_x}")
        logger.info(f"当前坐标：{status.Position}")
        return

    def get_camera_location1(self):
        try:
            media_profile = self.media.GetProfiles()[0]
            ProfileToken = media_profile.token
            status = self.ptz.GetStatus({'ProfileToken': ProfileToken})

            pantilt_x = status.Position.PanTilt.x
            pantilt_y = status.Position.PanTilt.y
            zoom_z = status.Position.Zoom.x

            logger.info(f"当前坐标：{status.Position}")

            return {
                "x": pantilt_x,
                "y": pantilt_y,
                "z": zoom_z
            }
        except Exception as e:
            logger.error(f"[get_camera_location] 获取相机位置失败：{e}")
            return None

    # 根据zoom level更新FOV
    def _update_fov_based_on_zoom(self):
        self.current_FOV_vertical = self.max_FOV_vertical - (
                    self.max_FOV_vertical - self.min_FOV_vertical) * self.current_zoom
        self.current_FOV_horizontal = self.max_FOV_horizontal - (
                    self.max_FOV_horizontal - self.min_FOV_horizontal) * self.current_zoom

    # 弧度转角度
    def angle_to_rad(self, angle):
        return math.radians(angle)

    # 当前吊具对应相机角度
    def y_to_camera_angle(self, target_x, target_y):
        rad = math.atan(abs(self.local_z - target_y) / abs(target_x - self.local_x))
        angle = math.degrees(rad)
        pantilt_y = 1 - angle / 90 * 2
        return pantilt_y

    # 计算相机当前位置视野上下限 1~-1 对应 0~-90°
    def calc_range(self, target_x):
        now_angle = round(self.pantilt_y - 1, 2) * 90 / 2 * - 1
        # 角度转弧度
        upper_limit_angle = now_angle - self.FOV_vertical / 2
        lower_limit_angle = now_angle + self.FOV_vertical / 2
        if upper_limit_angle <= 0:
            upper_limit_angle = 0.00001
        elif lower_limit_angle >= 90:
            lower_limit_angle = 90 - 0.00001
        tan_lower_value = math.tan(math.radians(lower_limit_angle))
        lower_limit_y = self.local_z - (target_x * tan_lower_value)
        tan_upper_value = math.tan(math.radians(upper_limit_angle))
        upper_limit_y = self.local_z - (target_x * tan_upper_value)

        if upper_limit_y > self.local_z:
            upper_limit_y = self.local_z
        elif lower_limit_y < 0:
            lower_limit_y = 0
        y_min = lower_limit_y
        y_max = upper_limit_y
        return (y_min, y_max)

    # 相机ptz 绝对位置移动
    def ptz_absolute_move(self, location_x, location_y, zoom_level):
        media_profile = self.media.GetProfiles()[0]
        request = self.ptz.create_type('AbsoluteMove')
        request.ProfileToken = media_profile.token
        self.ptz.Stop({'ProfileToken': media_profile.token})

        if request.Position is None:
            request.Position = self.ptz.GetStatus({'ProfileToken': media_profile.token}).Position
        if request.Speed is None:
            request.Speed = self.ptz.GetStatus({'ProfileToken': media_profile.token}).Position

        request.Position.PanTilt.y = location_y
        request.Speed.PanTilt.y = 1
        request.Position.PanTilt.x = location_x
        request.Speed.PanTilt.x = 1
        request.Position.Zoom.x = zoom_level
        request.Speed.Zoom.x = 0.5

        self.ptz.AbsoluteMove(request)
        return

    def move_to_pixel(self, current_pan, current_tilt, pixel_x, pixel_y, zoom_level=None, speed=None):
        media_profile = self.media.GetProfiles()[0]

        # 1. 获取当前状态
        status = self.ptz.GetStatus({'ProfileToken': media_profile.token})
        # current_pan = status.Position.PanTilt.x
        # current_tilt = status.Position.PanTilt.y

        # 如果未指定zoom_level，使用当前zoom level
        if zoom_level is None:
            zoom_level = status.Position.Zoom.x
        else:
            self.current_zoom = zoom_level

        # 2. 计算像素偏移
        offset_x = self.image_width / 2 - pixel_x
        offset_y = self.image_height / 2 - pixel_y

        # 4. 转换为ONVIF坐标
        if self.ip == '192.168.3.55':
            new_pan = current_pan - offset_x * 0.00013
            new_tilt = current_tilt - offset_y * (-0.0003)
        else:
            new_pan = current_pan - offset_x * 0.00012976445
            new_tilt = current_tilt - offset_y * (-0.0003)

        if new_pan < -1 or new_pan > 1:
            new_pan = ((new_pan + 1) % 2) - 1
        new_tilt = max(-1, min(1, new_tilt))
        logger.info(f"new_pan: {new_pan}, new_tilt: {new_tilt}")

        # 6. 执行移动
        request = {
            'ProfileToken': media_profile.token,
            'Position': {
                'PanTilt': {'x': new_pan, 'y': new_tilt},
                'Zoom': {'x': zoom_level} if zoom_level else status.Position.Zoom
            },
            'Speed': {
                'PanTilt': {'x': speed or self.ptz_speed, 'y': speed or self.ptz_speed}
            }
        }

        self.ptz.AbsoluteMove(request)

    def move_to_xyz(self,pixel_x, pixel_y, height, zoom_level=None, speed=None):
        media_profile = self.media.GetProfiles()[0]
        logger.info(f"pixel_x: {pixel_x}, pixel_y: {pixel_y}")
        # 1. 获取当前状态
        status = self.ptz.GetStatus({'ProfileToken': media_profile.token})
        if self.ip == '192.168.3.9':
            camera_location = [33307, 421483, 15425]  #192.168.3.9
            R = [
                [0.9912156124610972, 0.12694343297770966, -0.037107606190729926],
                [0.12771293390534472, -0.9916262830920372, 0.01914996591017272],
                [-0.03436591518731342, -0.02372086644508295, -0.9991277717931942]
            ]
            t = [-85946.53254049376, 413404.4977627314, 26554.113368926766]
            C = [10 * pixel_x, 10 * pixel_y, height]
            C_PTZ = compute_ptz_from_3d_point(C, R, t, camera_location)
            new_pan = C_PTZ[0]
            new_tilt = C_PTZ[1]

        elif self.ip == '192.168.3.59':
            camera_location = [24075, 420267, 15420]   # 192.168.3.59
            # 地面
            R = [
                [-0.96116906 ,- 0.27232611,  0.04463777],
                [-0.27591925 , 0.95115743 ,- 0.13844896],
            [-0.00475428 ,- 0.14538928 ,- 0.98936311]
            ]
            t = [ 137264.72584454, -392282.01151769 ,  76678.85383505]
            # 框架车
            # R = [[-0.96072619 , 0.27728778 , 0.01080147],
            #      [ 0.27717075 , 0.96075577 , -0.0111683],
            #      [-0.0134744 , -0.00773583, -0.99987929]]
            # t=[ -93571.97957062, -410274.61449977 ,  18993.64763032]
            C = [10 * pixel_x, 10 * pixel_y, height]
            C_PTZ = compute_ptz_from_3d_point(C, R, t, camera_location)

            new_pan = C_PTZ[0]
            new_tilt = C_PTZ[1] + 0.047918
            # 融合矩阵
            # R =[
            #     [-0.96176604,  0.27382446,  0.00512447],
            #     [ 0.27133042,  0.95521588, -0.11807806],
            #     [-0.03722764, -0.11217304 ,-0.99299109]]
            # t =[ -92396.34801752, -407474.85787516,   63510.49692489]

        elif self.ip == '192.168.3.50':
            camera_location = [23151, 98415, 15474]  # 192.168.3.50
            R = [
                [-0.65731349, - 0.75114873,  0.06094714],
                [-0.75151734,  0.65936794,  0.0213449],
                [-0.05621979, - 0.03177254, - 0.99791274]
            ]
            t = [88198.67119441, -47823.60943309,  19870.14047087]
            C = [10 * pixel_x, 10 * pixel_y, height]
            C_PTZ = compute_ptz_from_3d_point(C, R, t, camera_location)

            new_pan = C_PTZ[0]
            new_tilt = C_PTZ[1] + 0.045092
        elif self.ip == '192.168.3.55':
            camera_location = [23383, 311336, 15504]  # 192.168.3.50
            R = [
                [0.15972803,  0.98481053, - 0.06808214],
                [0.98714186, - 0.15891442,  0.01723848],
                [0.00615741, - 0.0699602, - 0.99753078]
            ]
            t = [-309286.34583181,   26126.17591786,   37102.86801467]
            C = [10 * pixel_x, 10 * pixel_y, height]
            C_PTZ = compute_ptz_from_3d_point(C, R, t, camera_location)

            new_pan = C_PTZ[0]
            new_tilt = C_PTZ[1] + 0.036891

        logger.info(f"new_pan: {new_pan}, new_tilt: {new_tilt}")


        # 6. 执行移动
        request = {
            'ProfileToken': media_profile.token,
            'Position': {
                'PanTilt': {'x': new_pan, 'y': new_tilt},
                'Zoom': {'x': zoom_level} if zoom_level else status.Position.Zoom
            },
            'Speed': {
                'PanTilt': {'x': speed or self.ptz_speed, 'y': speed or self.ptz_speed}
            }
        }
        self.ptz.AbsoluteMove(request)


    def calculate_zoom_level(self, box_width, box_height, max_zoom=0.9, min_zoom=0.1):
        """
        根据检测框大小动态计算zoom_level
        :param box_width: 检测框宽度（像素）
        :param box_height: 检测框高度（像素）
        :param max_zoom: 最大变焦级别（避免过度放大导致目标超出视野）
        :param min_zoom: 最小变焦级别（避免过度缩小导致目标过小）
        :return: zoom_level (0~1)
        """
        # 计算检测框面积占比
        box_area = box_width * box_height
        image_area = self.image_width * self.image_height
        area_ratio = box_area / image_area
        logger.info(f"比例：{area_ratio}")

        if area_ratio > 0.01:  # 大面积→小变焦
            zoom_level = 0.08
        elif area_ratio > 0.0001:
            zoom_level = 0.1
        else:  # 小面积→中等变焦
            zoom_level = 0.09
        zoom_level = max(min_zoom, min(max_zoom, zoom_level))  # 限制范围

        return zoom_level

    def calculate_zoom_level1(self, box_width, box_height, max_zoom=0.9, min_zoom=0.0454545468):
        """
            根据实际检测框长宽计算zoom_level
        """
        F0 = 0.0454545468
        W0 = 16300.0
        H0 = 4100.0

        box_width = box_width * 10
        box_height = box_height * 10
        F_width = F0 * (W0 / box_width) * 0.9
        F_height = F0 * (H0 / box_height) * 0.9
        zoom_level = min(F_width, F_height)

        logger.info(f"当前焦距:{zoom_level}")

        return zoom_level

    def calculate_zoom_level_JJH(self, detection, height):
        """
            根据实际检测框长宽计算zoom_level
        """
        # actual_area = 8,294,400
        # 8,294,400
        # 6.1 - 240 mm
        # target_area = 103680

        if self.ip == '192.168.3.59':
            camera_location = [24075, 420267, 15420]
        elif self.ip == '192.168.3.50':
            camera_location = [23151, 98415, 15474]  # 192.168.3.50
        elif self.ip == '192.168.3.55':
            camera_location = [23383, 311336, 15504]  # 192.168.3.50

        pixel_x = detection["center"][0] * 10
        pixel_y = detection["center"][1] * 10
        distance = math.sqrt((camera_location[0] - pixel_x) ** 2 + (camera_location[1] - pixel_y) ** 2 + (camera_location[2] - height) ** 2)
        if distance <= 18888:
            target_line = 1200
        else:
            target_line = 1700

        box_width = detection["short_side"] * 10
        box_height = detection["long_side"] * 10
        box_area = box_width * box_height

        zoom_level = ((0.001875 * distance * target_line / box_height) - 6)/ 234

        # zoom_level = math.sqrt(target_area * distance / box_area) / 240
        # zoom_level = 960 * distance / box_width / 240
        # print(f"当前焦距:{zoom_level}")

        return zoom_level
    def calculate_zoom_level2(self, box_width, box_height, max_zoom=0.9, min_zoom=0.0454545468):
        """
            根据实际检测框长宽计算zoom_level
        """
        F0 = 0.0454545468
        W0 = 2624
        H0 = 653

        F_width = F0 * (W0 / box_width)
        F_height = F0 * (H0 / box_height)
        zoom_level = min(F_width, F_height)

        logger.info(f"当前焦距:{zoom_level}")

        return zoom_level



if __name__ == '__main__':
    """
    {
    'PanTilt': {
        'x': 0.392722249,
        'y': -0.416571409
    },
    'Zoom': {
        'x': 0.0772727281
    }
}
    """
    # 单位：毫米
    ip = '192.168.3.68'
    user = 'admin'
    password = 'Bgitv45654'
    camera = Camera_ln(ip, user, password, 0, 25000)
    # 初始化相机位置
    # camera.init_camera_location()
    # 获取相机当前位置
    camera.connect_ONVIF()
    # camera.ptz_absolute_move(-0.503944397, -0.239238128,0.03136363)
    # camera.ptz_absolute_move(-0.966666639, -0.414476156, 0.0454545468)
    # camera.ptz_absolute_move(0.000555555569, -0.567047536, 0.0454545468)
    # camera.move_to_pixel(0.103888892, -0.0622857213,2808,688, 0.0454545468)
    # camera.move_to_xyz( 3839, 41623, 2620,0.1804944)
    # camera.move_to_xyz(6656, 415447, 2450,0.1804944)
    location = camera.get_camera_location()

    # image_data = camera.get_picture()
    # with open('test.jpg', 'wb') as img_file:
    #     img_file.write(image_data)
    # 根据相机位姿计算视野范围

    # camera.ptz_absolute_move(0.392722249, -0.416571409, 0.0772727281)
    # y_range = camera.calc_range(input_x)
    # if input_y < y_range[0] or input_y > y_range[1]:
    #     pantilt_y = camera.y_to_camera_angle(input_x, input_y)
    #     camera.ptz_absolute_move(pantilt_y)
    # else:
    #     pass
