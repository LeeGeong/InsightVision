'''
对齐装置/垫木装置Z值
'''
import open3d as o3d
import numpy as np
from scan.util.open_file_to_pcd import get_pcd_np_from_file
from scan.util.filter import filter_np2np
from scan.util.cut import cut_floor
from scan.util.cluster import car_cluster
from scan.util.common import unit_conversion, reserve_integer
import scan.config as config
from scan.util.exclude import examine_points_count


def calculate_average_after_normal(pcd_np: np.ndarray) -> np.ndarray:
    # 在z值最大的附近,取一个10平方厘米的数据，使用正态分布，留下中间60%的数据，取一个平均值z，最后再加1cm
    square_length = 0.1
    # 取z最大值周围的数据
    max_z_points = pcd_np[np.argmax(pcd_np[:, 2])]
    # print(f"point:{max_z_points}")
    np_left_points = pcd_np[(pcd_np[:, 0] >= (max_z_points[0] - (square_length / 2))) &
                            (pcd_np[:, 0] <= (max_z_points[0] + (square_length / 2))) &
                            (pcd_np[:, 1] >= (max_z_points[1] - (square_length / 2))) &
                            (pcd_np[:, 1] <= (max_z_points[1] + (square_length / 2)))]

    # 正态分布后计算平均值
    # 步骤1: 排序数组，从小到大
    sorted_data = np.sort(np_left_points[:, 2])
    # print(np_left_points[np_left_points[:,2].argsort()])

    # 步骤2: 计算要去除的元素数量
    num_to_remove = int(len(sorted_data) * 0.2)  # 计算要去除的元素数量（20%）

    # 步骤3: 去除20%的最小值和最大值
    if num_to_remove == 0:
        remaining_data = sorted_data
    else:
        remaining_data = sorted_data[num_to_remove:-num_to_remove]

    # 步骤4: 计算剩余数据的平均值
    average_value = np.mean(remaining_data)

    if config.is_save_align_area:
        import time
        global file_dir
        output_dir = f"{file_dir}.{str(time.time())}" + "_filter.xyz"
        from scan.util.common import save_pcd
        save_pcd(remaining_data, output_dir)
        print(f"保存成功: {output_dir}")

    return average_value


def filter_points_by_y_range(pcd_np):
    """
    从三维点云中提取y坐标在最大值到yMax-20cm范围内的点

    参数:
    point_cloud: numpy数组，形状为(n, 3)，包含n个三维点(x, y, z)

    返回:
    filtered_points: numpy数组，过滤后的点云
    """
    # 确保输入是numpy数组
    pcd_np = np.array(pcd_np)

    # 获取y坐标的最大值
    y_max = np.max(pcd_np[:, 1])

    # 计算y的最小阈值（yMax - 20cm）
    y_min_threshold = y_max - 0.2  # 20cm = 0.2m

    # 找到y坐标在[yMax - 0.2, yMax]范围内的点
    mask = (pcd_np[:, 1] >= y_min_threshold) & (pcd_np[:, 1] <= y_max)

    # 提取符合条件的点
    filtered_points = pcd_np[mask]

    if config.is_save_align_area:
        import time
        global file_dir
        output_dir = f"{file_dir} + {str(time.time())}" + " _filter.xyz"
        from scan.util.common import save_pcd
        save_pcd(filtered_points, output_dir)
        print(f"保存成功: {output_dir}")

    return filtered_points


def filter_points_by_y_min_plus_20cm(pcd_np):
    """
    从三维点云中提取y坐标在最小值到yMin+20cm范围内的点

    参数:
    point_cloud: numpy数组，形状为(n, 3)，包含n个三维点(x, y, z)

    返回:
    filtered_points: numpy数组，过滤后的点云
    """
    # 确保输入是numpy数组
    pcd_np = np.array(pcd_np)

    # 获取y坐标的最小值
    y_min = np.min(pcd_np[:, 1])

    # 计算y的最大阈值（yMin + 20cm）
    y_max_threshold = y_min + 0.2  # 20cm = 0.2m

    # 找到y坐标在[y_min, y_min + 0.2]范围内的点
    mask = (pcd_np[:, 1] >= y_min) & (pcd_np[:, 1] <= y_max_threshold)

    # 提取符合条件的点
    filtered_points = pcd_np[mask]

    if config.is_save_align_area:
        import time
        global file_dir
        output_dir = f"{file_dir} + {str(time.time())}" + " _filter.xyz"
        from scan.util.common import save_pcd
        save_pcd(filtered_points, output_dir)
        print(f"保存成功: {output_dir}")

    return filtered_points


def align_and_crosser_z(pcd_car: o3d.geometry.PointCloud, park_no: str, frame_type: int ,empty_statu: int ) -> tuple:
    if park_no == "TPC5" or park_no == "TPC6" or park_no == "TPC7" or park_no == "TPC8":
        return False, None, f"车位{park_no}不使用对齐装置与垫木装置"
    else:
        try:
            # 对齐和垫木z值
            pcd_np_car = np.asarray(pcd_car.points)
            x_small = config.align_device[park_no]["x_small"]
            x_large = config.align_device[park_no]["x_large"]

            # x值小的对齐装置的z值(北侧对齐装置)
            np_align_small_area = pcd_np_car[(pcd_np_car[:, 0] >= x_small[0]) & (pcd_np_car[:, 0] <= x_small[1]) &
                                             (pcd_np_car[:, 1] >= x_small[2]) & (pcd_np_car[:, 1] <= x_small[3])]

            # 空的凹框架新的切割方法，其他的还用以前的方法
            if frame_type == 2 and empty_statu == 1:
                #根据车位位置切割边缘, 切割20cm
                if park_no == "TPC11" or park_no == "TPC12" or park_no == "TPC3" or park_no == "TPC4":
                    # 对齐是在y值大的地方
                    edge_points = filter_points_by_y_range(np_align_small_area)
                    np_align_small = np.max(edge_points[:, 2])
                else:
                    # 对齐是在y值小的地方
                    edge_points = filter_points_by_y_min_plus_20cm(np_align_small_area)
                    np_align_small = np.max(edge_points[:, 2])
                np_align_small_uniform_addition = np_align_small
            else:
                np_align_small = calculate_average_after_normal(np_align_small_area)
                np_align_small_uniform_addition = np_align_small + config.align_device[park_no]["uniform_addition"][0]

            # np_align_small = calculate_average_after_normal(np_align_small_area)
            # np_align_small_uniform_addition = np_align_small + config.align_device[park_no]["uniform_addition"][0]
            align_z1 = max(np_align_small_uniform_addition, x_small[4])  # 低于对齐装置下限高度值，就给下限位高度值。
            # print(f"align_small-------{np_align_small},{np_align_small_uniform_addition}")

            # x值大的对齐装置的z值(南侧对齐装置)
            np_align_large_area = pcd_np_car[(pcd_np_car[:, 0] >= x_large[0]) & (pcd_np_car[:, 0] <= x_large[1]) &
                                             (pcd_np_car[:, 1] >= x_large[2]) & (pcd_np_car[:, 1] <= x_large[3])]
            # 空的凹框架新的切割方法，其他的还用以前的方法
            if frame_type == 2 and empty_statu == 1:
                #根据车位位置切割边缘, 切割20cm
                if park_no == "TPC11" or park_no == "TPC12" or park_no == "TPC3" or park_no == "TPC4":
                    # 对齐是在y值大的地方
                    edge_points = filter_points_by_y_range(np_align_large_area)
                    np_align_large = np.max(edge_points[:, 2])
                else:
                    # 对齐是在y值小的地方
                    edge_points = filter_points_by_y_min_plus_20cm(np_align_large_area)
                    np_align_large = np.max(edge_points[:, 2])
                np_align_large_uniform_addition = np_align_large
            else:
                np_align_large = calculate_average_after_normal(np_align_large_area)
                np_align_large_uniform_addition = np_align_large + config.align_device[park_no]["uniform_addition"][1]

            # np_align_large = calculate_average_after_normal(np_align_large_area)
            # np_align_large_uniform_addition = np_align_large + config.align_device[park_no]["uniform_addition"][1]
            align_z2 = max(np_align_large_uniform_addition, x_large[4])
            # print(f"align_large-------{np_align_large},{np_align_large_uniform_addition}")

            # x值小的垫木装置的z值(北侧垫木装置)
            np_crosser_small_area = pcd_np_car[(pcd_np_car[:, 0] >= x_small[0]) & (pcd_np_car[:, 0] <= x_small[1])]
            crosser_z1 = np.max(np_crosser_small_area[:, 2])

            # x值大的垫木装置的z值(南侧垫木装置)
            np_crosser_large_area = pcd_np_car[(pcd_np_car[:, 0] >= x_large[0]) & (pcd_np_car[:, 0] <= x_large[1])]
            crosser_z2 = np.max(np_crosser_large_area[:, 2])

            # 转换单位
            align_z1 = reserve_integer(unit_conversion(align_z1))
            align_z2 = reserve_integer(unit_conversion(align_z2))
            crosser_z1 = reserve_integer(unit_conversion(crosser_z1))
            crosser_z2 = reserve_integer(unit_conversion(crosser_z2))

            return True, ((align_z1, align_z2), (crosser_z1, crosser_z2)), "识别成功"
        except:
            return False, None, "对齐和垫木识别失败"


def get_data(isSuccess: bool, message: str, align_z=(0, 0), crosser_z=(0, 0)) -> dict:
    return {
        "isSuccess": isSuccess,
        "align_z": {
            "AlignZ1": align_z[0],
            "AlignZ2": align_z[1]
        },
        "crosser_z": {
            "CrosserZ1": crosser_z[0],
            "CrosserZ2": crosser_z[1]
        },
        "message": message
    }


def get_result(file_path: str, park_no: str, frame_type: int, empty_statu: int) -> dict:
    '''
    识别对齐装置/垫木装置Z值
    :param file_path: 点云文件
    :param park_no:车位号
    :param frame_type: 框架车类型。1平框架，2凹框架
    :param empty_statu: 是否是空框架。1空框架，2有钢板
    :return:
    '''
    try:
        isSuccess, pcd_np, message = get_pcd_np_from_file(file_path)
        if not isSuccess:
            return get_data(isSuccess, message)

        # 离群点去除
        pcd_filter = filter_np2np(pcd_np)
        # 切割地面
        pcd_not_floor = cut_floor(pcd_filter)
        # 判断现场有无车辆
        if not examine_points_count(pcd_not_floor):
            return get_data(False, "当前车位没有车")
        # 聚类
        pcd_car = car_cluster(pcd_not_floor)
        # 对齐装置z值,垫木装置z值
        isSuccess, res, message = align_and_crosser_z(pcd_car, park_no, frame_type, empty_statu)  # z1对应x小的对齐装置， z2对应x大的对齐装置
        if not isSuccess:
            return get_data(isSuccess, message)

        return get_data(True, "识别成功", res[0], res[1])
    except:
        return get_data(False, "识别高度失败")


if __name__ == "__main__":
    # frame_type: 框架车类型。1平框架，2凹框架
    # empty_statu: 是否是空框架。1空框架，2有钢板
    file_dir = r"D:\工作\项目文档\点云\2026\01\08\TPC3_20260108_760592890994694_192.168.2.190.xyz"
    res = get_result(file_dir, "TPC3", 2, 1)

    print(f"{res}")
