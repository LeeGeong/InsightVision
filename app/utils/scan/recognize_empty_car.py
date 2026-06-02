'''
空框架位置识别
'''
from scan.util.open_file_to_pcd import get_pcd_np_from_file
from scan.util.filter import filter_np2np
from scan.util.cut import cut_floor
from scan.util.exclude import examine_points_count
from scan.util.cluster import car_cluster
from scan.util.get_grab_point import get_center_point
import numpy as np
from scan.util.filter_plane import get_z_heights_from_x_interval

def get_data(is_success:bool, message:str, point: tuple = (0,0,0)) -> dict:
    return {
        "is_success": is_success,
        "message":message,
        "grab_point":point,
    }


def get_result(file_path: str, park_no: str, car_type:int) -> dict:
    '''
    空框架计算车位中心点
    :param file_path: 点云文件路径
    :param park_no: 车位号
    :param car_type:
    :return: 车位中心点
    '''
    try:
        is_success, pcd_np, message = get_pcd_np_from_file(file_path)
        if not is_success:
            return get_data(is_success, message)

        # 1 离群点去除
        pcd_filter_np = filter_np2np(pcd_np)
        # 2 切割地面
        pcd_not_floor = cut_floor(pcd_filter_np)
        # 3 判断现场有无车辆
        if not examine_points_count(pcd_not_floor):
            return get_data(False, "当前车位没有车")
        # 4 聚类
        pcd_car = car_cluster(pcd_not_floor)
        #todo 提取车上层点云

        # 5 点云包围盒计算中心点
        center_point_x, center_point_y, _ = get_center_point(pcd_car)
        pcd_car_np = np.asarray(pcd_car.points)
        # 根据框架类型计算z值
        if car_type == 2:
            # 2 - 凹框架
            x_to_z = get_z_heights_from_x_interval(pcd_car_np, interval=0.05)   # x每隔step，取z的平均值
            x_to_z_np = np.asarray(x_to_z)
            x_to_z_np = x_to_z_np[x_to_z_np[:, 0].argsort()]  # 按x值从小到大排序
            center_point_z = (x_to_z_np[0][1] + x_to_z_np[-1][1]) / 2
        else:
            # 3 - 平框架
            center_point_z = np.mean(pcd_car_np[:, 2])

        # 6 转换单位
        from scan.util.common import reserve_integer,unit_conversion
        center_x = reserve_integer(unit_conversion(center_point_x))
        center_y = reserve_integer(unit_conversion(center_point_y))
        center_z = reserve_integer(unit_conversion(center_point_z))
        center_point = (center_x, center_y, center_z)

        return get_data(True, "识别空框架中心点成功", center_point)
    except Exception as e:
        return get_data(False, "识别空框架中心点失败")



if __name__ == '__main__':
    # file_path = r"D:\项目点云文件\宝钢\扫描数据\扫描数据scan\2025\01\0104\1-4\1-4\638715873997225006.xyz"
    file_path = r"D:\项目点云文件\宝钢\扫描数据\扫描数据scan\2025\03\0312\192.168.2.198_653640069857286_TPC11_20250312_638773709373718807.xyz"
    res = get_result(file_path, park_no="", car_type=1)
    print(res)