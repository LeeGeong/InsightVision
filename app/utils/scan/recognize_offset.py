'''吊具纠偏'''
from scan.util.open_file_to_pcd import get_pcd_np_from_file, get_pcd_craneZ_np_from_file
from scan.util.cut import cut_xyz, cut_x
import scan.config as config
from scan.util.filter import filter, filter_electromagnet_lifting
from scan.util.cluster import cluster_steel_plate, cluster_magnet
from scan.util.exclude import examine_points_count_lower_limit, examine_angle, examine_offset
from scan.util.common import unit_conversion, unit_conversion_millimeter_to_meter, reserve_integer
from scan.util.calculate_bounding_rectangle import minimum_bounding_rectangle, calculate_rectangle_rotated_center, \
    minimum_bounding_rectangle_to_corners, calculate_rectangle_rotated_center_left_up
from scan.util.get_angle_point import get_angle_point_right_up_from_corners, get_angle_point_left_up_from_corners
from scan.util.logger import scan_logger
import numpy as np
from enum import Enum
from scan.util.offset_util import z_translation


class ResultCodeEnum(Enum):
    Both_Exceeded = (0, "角度、X、Y均超出阈值")  # 目前其他异常也走code 0
    Success = (1, "成功")
    Angle_Exceeded = (2, "角度超出阈值")
    OffsetX_Exceeded = (3, "x方向偏移超出阈值")
    OffsetY_Exceeded = (4, "y方向偏移超出阈值")
    Angle_OffsetX_Exceeded = (5, "角度、X方向偏移超出阈值")
    Angle_OffsetY_Exceeded = (6, "角度、Y方向偏移超出阈值")
    OffsetX_OffsetY_Exceeded = (7, "X、Y方向偏移超出阈值")

    def __init__(self, code: int, message: str):
        # 为每个枚举成员附加额外的属性（如code和message），而不仅仅是默认的name和value
        self.code = code
        self.message = message

    @classmethod
    def get_code_and_msg(cls, isSuccess_angle: bool, isSuccess_x: bool, isSuccess_y: bool) -> "ResultCodeEnum":
        key = (isSuccess_angle, isSuccess_x, isSuccess_y)
        mapping = {
            (False, False, False): cls.Both_Exceeded,
            (True, True, True): cls.Success,
            (False, True, True): cls.Angle_Exceeded,
            (True, False, True): cls.OffsetX_Exceeded,
            (True, True, False): cls.OffsetY_Exceeded,
            (False, False, True): cls.Angle_OffsetX_Exceeded,
            (False, True, False): cls.Angle_OffsetY_Exceeded,
            (True, False, False): cls.OffsetX_OffsetY_Exceeded,
        }
        return mapping[key]


def get_cut_steel_area(equipmentNo: str, lifiting_height: int):
    x_min = config.EqNo2CutParam[equipmentNo]["x_small"]
    x_max = config.EqNo2CutParam[equipmentNo]["x_large"]
    y_min = config.EqNo2CutParam[equipmentNo]["y_small"]
    y_max = config.EqNo2CutParam[equipmentNo]["y_large"]
    if (lifiting_height == 1):
        z_min = config.EqNo2CutParam[equipmentNo]["z_small_1"]
        z_max = config.EqNo2CutParam[equipmentNo]["z_large_1"]
    else:
        z_min = config.EqNo2CutParam[equipmentNo]["z_small_2"]
        z_max = config.EqNo2CutParam[equipmentNo]["z_large_2"]
    return x_min, x_max, y_min, y_max, z_min, z_max


def rectangle_extension(corners_area: np.ndarray) -> list:
    """向外扩展"""
    sorted_indices = np.argsort(corners_area[:, 1])  # 按照 y 值排序
    max_y_two_points = corners_area[sorted_indices[2:]]  # 获后两个最大的点,y值最大点 - 上边的两个点
    min_y_two_points = corners_area[sorted_indices[:2]]  # 获后两个最小的点,y值最小点 - 下边的两个点
    sorted_indices = np.argsort(max_y_two_points[:, 0])  # 按照 x 值排序
    left_up = max_y_two_points[sorted_indices[:1]][0]  # 左上角点
    right_up = max_y_two_points[sorted_indices[1:]][0]  # 获取后一个最大的点，x值最大点 - 右上角点

    sorted_indices = np.argsort(min_y_two_points[:, 0])  # 按照 x 值排序
    left_down = min_y_two_points[sorted_indices[:1]][0]  # 左下角点
    right_down = min_y_two_points[sorted_indices[1:]][0]  # 获取后一个最大的点，x值最大点 - 右下角点

    extend_distance = 0.05
    left_up = [left_up[0] - extend_distance, left_up[1] + extend_distance]
    right_up = [right_up[0] + extend_distance, right_up[1] + extend_distance]
    left_down = [left_down[0] - extend_distance, left_down[1] - extend_distance]
    right_down = [right_down[0] + extend_distance, right_down[1] - extend_distance]
    return [left_up, right_up, right_down, left_down]  # 顺时针


def get_data(result_code: int, message: str, offsetX=0.0, offsetY=0.0, plate_deflection_angle=0.0) -> dict:
    # 0 偏移、角度均超出阈值；1成功；2 偏移超出阈值；3 角度超出阈值
    result = {
        "isSuccess": result_code,
        "offset": {
            "OffSetX": offsetX,
            "OffSetY": offsetY
        },
        "plate_deflection_angle": plate_deflection_angle,
        "message": message
    }
    return result


def recognize_center(file_path: str, equipmentNo: str, length: int, width: int, lifiting_height: int,
                     magnet_offset: int) -> dict:
    '''
    识别吊具纠偏
    :param file_path: 点云文件路径
    :param equipmentNo: 起重机编号
    :param length: 钢板长度
    :param width: 钢板宽度
    :param lifiting_height: 吊具悬停高度 1=5400;2:4000
    :param magnet_offset: 电磁铁是否偏移 - 0表示不偏移、正值表示往大方向偏1100、负值表示往小方向偏1100
    :return: 识别结果
    '''
    try:
        scan_logger.info(
            f"文件：{file_path}, 钢板长：{length}, 钢板宽：{width}, 吊具高度：{str(5400) if lifiting_height == 1 else str(4000)}")
        # 1.单位转换
        length = unit_conversion_millimeter_to_meter(length)
        width = unit_conversion_millimeter_to_meter(width)

        # 2.加载点云文件
        isSuccess, pcd_np, message = get_pcd_craneZ_np_from_file(file_path)
        if not isSuccess:
            return get_data(ResultCodeEnum.Both_Exceeded.code, message)

        # 3.根据craneZ组合运动中数据 - 高度平移
        pcd_translation_np, min_crane_z = z_translation(pcd_np)

        # 4.计算Z切割值-吊具和钢板的中间点  kx+b
        z_1 = round(config.EqNo2CutParam[equipmentNo]["k"] * min_crane_z + config.EqNo2CutParam[equipmentNo]["b"],
                    3)

        # 5.根据扫描仪的位置切割 - 钢板
        cut_steel_area = get_cut_steel_area(equipmentNo, lifiting_height)
        z_2 = z_1 - 0.4  # z切割低点
        pcd_np_cut_steel = cut_xyz(pcd_translation_np,
                                   cut_steel_area[0], cut_steel_area[1],
                                   cut_steel_area[2], cut_steel_area[3],
                                   z_2, z_1)

        # 6.点数判断 -- 暂定8000
        isSuccess, message = examine_points_count_lower_limit(pcd_np_cut_steel, 4000)
        if not isSuccess:
            return get_data(ResultCodeEnum.Both_Exceeded.code, message)

        # 7.根据扫描仪的位置切割 - 电磁铁吊具
        cut_magnet_area = config.EqNo2CutParam[equipmentNo]["electromagnet_lifting_cut"][0]
        z_3 = z_1 + 0.35  # z切割高点
        pcd_np_cut_magnet = cut_xyz(pcd_translation_np,
                                    cut_magnet_area[0], cut_magnet_area[1],
                                    cut_magnet_area[2], cut_magnet_area[3],
                                    z_1, z_3)

        # 8.离群点去除
        pcd_filter_steel = filter(pcd_np_cut_steel)
        pcd_filter_magnet = filter(pcd_np_cut_magnet)

        # 9.钢板聚类
        pcd_cluster_steel = cluster_steel_plate(pcd_filter_steel, exclusion_width=0.3)

        # 10.处理电磁铁吊具，得到每块电磁铁的边界
        rectangles = []
        for area in config.EqNo2CutParam[equipmentNo]["electromagnet_lifting_cut"][1]:
            pcd_np_cut_magnet_section = cut_x(np.asarray(pcd_filter_magnet.points), area[0], area[1])  # 切割每块电磁铁
            if pcd_np_cut_magnet_section.shape[0] == 0:   #切除没有电磁铁的点
                continue
            pcd_cluster_magnet_section = cluster_magnet(pcd_np_cut_magnet_section)  # 每块电磁铁聚类
            if len(pcd_cluster_magnet_section.points):  # 离扫描仪远的的磁铁可能聚类后没有点 -> 排除
                pcd_filter_magnet_section = filter(np.asarray(pcd_cluster_magnet_section.points))  # 每块电磁铁离群点去除
                corners_area = minimum_bounding_rectangle_to_corners(pcd_filter_magnet_section)  # 每块电磁铁边界
                corners_area = rectangle_extension(corners_area)  # 每块电磁铁向外扩展
                rectangles.append(corners_area)  # 顺时针

        # 11.钢板去除电磁铁吊具
        pcd_np_steel_eliminate_magent_2d = filter_electromagnet_lifting(np.asarray(pcd_cluster_steel.points)[:, :2],
                                                                        rectangles)

        # 12 离群点去除
        z_zeros = np.zeros((pcd_np_steel_eliminate_magent_2d.shape[0], 1))  # 二维转三维
        pcd_np_steel_eliminate_magent_3d = np.hstack((pcd_np_steel_eliminate_magent_2d, z_zeros))  # 水平拼接二维点和z列
        pcd_np_steel_filter = filter(pcd_np_steel_eliminate_magent_3d)

        # 13.最小外接矩形，并判断排除
        rectangle_length, rectangle_width, angle, corners = minimum_bounding_rectangle(pcd_np_steel_filter)

        if equipmentNo == "C12":
            # 14.得到右上角点, 判断从右上角点是顺时针旋还是逆时针旋
            angle_point, rotate_direction = get_angle_point_right_up_from_corners(corners)
            # 15.得到钢板中心点
            center_point = calculate_rectangle_rotated_center(angle_point[0], angle_point[1], length,
                                                              width, angle,
                                                              rotate_direction)
        else:
            # 14.得到左上角点, 判断从右上角点是顺时针旋还是逆时针旋
            angle_point, rotate_direction = get_angle_point_left_up_from_corners(corners)
            # 15.得到钢板中心点
            center_point = calculate_rectangle_rotated_center_left_up(angle_point[0], angle_point[1], length,
                                                                      width, angle,
                                                                      rotate_direction)

        # 16.计算偏移 - 吊具中心点减钢板中心点
        lifting_center_x = config.EqNo2CutParam[equipmentNo]["crane_spreader_center_point"][
                               0] - magnet_offset / 1000  # 吊具相对中心点
        offsetX = lifting_center_x - center_point[0]
        offsetY = config.EqNo2CutParam[equipmentNo]["crane_spreader_center_point"][1] - center_point[1]
        scan_logger.info(
            f"文件：{file_path}, 钢板中心点：{[round(point, 4) for point in center_point]}, 角点：{[round(point, 4) for point in angle_point]},"
            f"角度：{round(angle, 4)}, 角点：{np.round(corners, 4).tolist()}")

        # 17.异常判断
        isSuccess_x, message_x = examine_offset(offsetX, config.offset_x_threshold)  # 判断x
        isSuccess_y, message_y = examine_offset(offsetY, config.offset_y_threshold)  # 判断y
        isSuccess_angle, message_angle = examine_angle(angle, config.offset_angle_threshold)  # 角度判断

        # 18.转换单位
        offsetX = reserve_integer(unit_conversion(offsetX))
        offsetY = reserve_integer(unit_conversion(offsetY))
        plate_deflection_angle = round(angle, 2) if rotate_direction == "+" else -round(angle, 2)  # 得到钢板偏角

        # 19.输出结果判断
        msg = f" offsetX：{offsetX}, offsetY：{offsetY}, angle: {plate_deflection_angle}"
        result_enum = ResultCodeEnum.get_code_and_msg(isSuccess_angle, isSuccess_x, isSuccess_y)
        result_code = result_enum.code
        message = result_enum.message
        if result_enum.code != ResultCodeEnum.Success.code:
            message = message + msg

        res = get_data(result_code, message, offsetX, offsetY, plate_deflection_angle)
        scan_logger.info(f"文件：{file_path}, 识别结果：{res.values()}")
        return res

    except:
        res = get_data(ResultCodeEnum.Both_Exceeded.code, "排查识别失败原因")
        scan_logger.info(f"文件：{file_path}, 识别结果：{res.values()}")
        return res


if __name__ == "__main__":
    # file_dir = r"D:\项目点云文件\宝钢\扫描数据\扫描数据C\10\29\c11_2025_10_29\C11_20251029_735423734829062_192.168.0.13.xyz"
    # res = recognize_center(file_dir, "C11", 6244, 4013, 1, 1100)

    # file_dir = r"D:\项目点云文件\宝钢\扫描数据\扫描数据C\10\29\c11_2025_10_29\C11_20251029_735407848181766_192.168.0.13.xyz"
    # res = recognize_center(file_dir, "C11", 7847, 2232, 1, 0)

    file_dir = r"D:\项目点云文件\宝钢\扫描数据\扫描数据C\12\26\C12_20251225_755703756955654_192.168.0.13.xyz"
    res = recognize_center(file_dir, "C12", 9485, 3053, 1, 0)

    print(res)

    # file_dir = r"D:\项目点云文件\宝钢\扫描数据\扫描数据C\10\29\c11_2025_10_29\C11_20251029_735389824573446_192.168.0.13.xyz"
    # res = recognize_center(file_dir, "C11", 6263, 2158, 1, 1100)

    # file_dir = r"D:\项目点云文件\宝钢\扫描数据\扫描数据C\10\29\c11_2025_10_29\C11_20251029_735400563945478_192.168.0.13.xyz"
    # res = recognize_center(file_dir, "C11", 7431, 3032, 1, 1100)

    # file_dir = r"D:\项目点云文件\宝钢\扫描数据\扫描数据C\10\29\c11_2025_10_29\C11_20251029_735405294972934_192.168.0.13.xyz"
    # res = recognize_center(file_dir, "C11", 7889, 2759, 1, 0)
