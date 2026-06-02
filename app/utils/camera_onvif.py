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

from onvif import ONVIFCamera
import math



# 垂直的角度，25-56左右
class Camera(object):
    def __init__(self, ip, user, password, topic, local_x=0, local_z=0):
        # 垂直视场角 56°
        self.FOV_vertical = 56
        self.ip = ip
        self.user = user
        self.password = password
        self.local_x = local_x
        self.local_z = local_z
        self.topic = topic

    def connect_ONVIF(self):
        mycam = ONVIFCamera(self.ip, 80, self.user, self.password, wsdl_dir='./wsdl')
        self.media = mycam.create_media_service()
        self.ptz = mycam.create_ptz_service()
        self.device = mycam.create_devicemgmt_service()
        return

    # 初始化相机位置 归零（视野上边缘水平为归零）
    def init_camera_location(self):
        self.get_camera_location() # 获取当前相机位置，得到x位置
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
        print("当前相机位置X：", self.pantilt_x)
        print("当前坐标：", status.Position)
        return

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
    camera = Camera(ip, user, password, 0, 25000)
    camera.ptz_absolute_move(-0.503944397, -0.239238128, 0.03136363)

    # 初始化相机位置
    # camera.init_camera_location()
    # 获取相机当前位置
    camera.connect_ONVIF()
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
