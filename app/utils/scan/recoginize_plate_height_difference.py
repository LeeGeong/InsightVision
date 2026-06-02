'''钢板高低差'''
import numpy as np
from scan.util.open_file_to_pcd import get_pcd_np_from_file
from scan.util.filter import filter_np2np
from scan.util.cut import cut_from_points
from scan.util.common import unit_conversion, reserve_integer
from scan.util.smooth import gaussian_filter
from scan.util.down_sampling import down_sampling_to_np
import scan.config as config


def check_points_position(angle_points: list) -> list:
    # left_top_point = None
    # left_bottom_point = None
    # right_top_point = None
    # right_bottom_point = None

    # 根据 x 值对点进行排序，按 x 值升序排列
    sorted_points = sorted(angle_points, key=lambda p: p[0])

    # 选取 x 值最大的两个点
    largest_two_points = sorted_points[-2:]
    if largest_two_points[0][1] > largest_two_points[1][1]:
        right_top_point = largest_two_points[0]
        right_bottom_point = largest_two_points[1]
    else:
        right_top_point = largest_two_points[1]
        right_bottom_point = largest_two_points[0]

    # 选取 x 值最小的两个点
    smallest_two_points = sorted_points[:2]
    if smallest_two_points[0][1] > smallest_two_points[1][1]:
        left_top_point = smallest_two_points[0]
        left_bottom_point = smallest_two_points[1]
    else:
        left_top_point = smallest_two_points[1]
        left_bottom_point = smallest_two_points[0]

    rect_points = [left_top_point, left_bottom_point, right_top_point, right_bottom_point]
    # 单位装换 毫米->米
    rect_points = np.asarray(rect_points, dtype=float) / float(1000)

    return rect_points


def get_data(isSuccess: bool, message: str, plate_high_z: float = 0, plate_low_z: float = 0) -> dict:
    return {
        "isSuccess": isSuccess,
        "plate_high_z": plate_high_z,
        "plate_low_z": plate_low_z,
        "message": message
    }


def get_result(file_path: str, angle_points: list) -> dict:
    """
    识别钢板高低差
    :param file_path: 点云文件地址
    :param angle_points: 四个角点 [[1,2],[1,2],[1,2],[1,2]]
    :return:识别结果
    """
    try:
        isSuccess, pcd_np, message = get_pcd_np_from_file(file_path)
        if not isSuccess:
            return get_data(isSuccess, message)

        # 离群点去除
        pcd_filter = filter_np2np(pcd_np)

        # 四个点判断位置
        points_position = check_points_position(angle_points)

        # 切割点云
        pcd_cut_np = cut_from_points(pcd_filter, points_position)

        # 降采样
        pcd_filter_np = down_sampling_to_np(pcd_cut_np)

        # 高斯平滑
        pcd_cut_np = gaussian_filter(pcd_filter_np)

        # 计算最高值和最低值
        plate_high_z = np.max(pcd_cut_np[:, 2])
        plate_low_z = np.min(pcd_cut_np[:, 2])

        # 误差
        plate_high_z = plate_high_z - config.error / 2
        plate_low_z = plate_low_z + config.error / 2

        # 转换单位
        plate_high_z = reserve_integer(unit_conversion(plate_high_z))
        plate_low_z = reserve_integer(unit_conversion(plate_low_z))

        return get_data(True, "识别成功", plate_high_z, plate_low_z)
    except:
        return get_data(False, "识别钢板高低差失败")


if __name__ == '__main__':
    file_path = r"D:\项目\BaoGang_ScanAlgorithm\Data\TPC10_20250423_668553690836998_192.168.2.199.xyz"
    res = get_result(file_path, [[29573, 416296], [28957, 418269], [36490, 418240], [37145, 416207]])

    print(f"{res}")
    print(f"高低差：{res['plate_high_z'] - res['plate_low_z']}")
