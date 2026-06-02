import open3d as o3d
import numpy as np
import scan.config as config
from scan.util.cut import cut_floor
import matplotlib.pyplot as plt
import math
from scan.util.logger import scan_logger
from typing import Union


def fit_line(pcd_np, up_or_down) -> tuple:
    '''拟合钢板上下边界直线
    :param pcd_np: ndarray，形状为 (n, 3)，表示 n 个点的三维坐标
    :param up_or_down: 需要得到上边界还是下边界
    :return: （是否得到直线，拟合直线的角度）
    '''
    # 设定 X 值的间隔 (从最小到最大每 0.1 米)
    x_min = pcd_np[:, 0].min()
    x_max = pcd_np[:, 0].max()
    x_intervals = np.arange(x_min, x_max, 0.1)
    # 存储筛选后的点
    filtered_points = []
    last_point = None
    for x_start in x_intervals:
        # 选择 X 值在 [x_start, x_start+0.1) 范围内的点
        mask_x = (pcd_np[:, 0] >= x_start) & (pcd_np[:, 0] < x_start + 0.1)
        points_in_range = pcd_np[mask_x]
        if len(points_in_range) == 0:
            continue
        # 找到y值最大或最小的点的索引
        if up_or_down == "up":
            index_of_y = np.argmax(points_in_range[:, 1])
        else:
            index_of_y = np.argmin(points_in_range[:, 1])
        # 获取y值最大的点
        max_y_point = points_in_range[index_of_y]

        # 判断点属于上边界
        if last_point is None:  # 第一次存点
            last_point = max_y_point
            continue
        if abs(last_point[1] - max_y_point[1]) >= 0.1:  # 通过y值变化较小，来判断是上面的边
            last_point = max_y_point
            continue

        # 将符合条件的点添加到最终列表中
        filtered_points.append(max_y_point)
    # 将所有过滤后的点合并成一个数组
    filtered_points = np.vstack(filtered_points)

    if (len(filtered_points) >= 2):
        # 将x和y值分离
        x = filtered_points[:, 0]
        y = filtered_points[:, 1]

        # 使用numpy的polyfit函数进行线性拟合 p为多项式的系数，这里我们拟合一条直线，所以多项式的阶数为1
        p = np.polyfit(x, y, 1)
        # 计算弧度
        theta_radian = math.atan(p[0])
        # 转换为度数
        theta_degree = math.degrees(theta_radian)

        if config.is_visual:
            visual_line(p, x, y, pcd_np)
        return True, theta_degree
    else:
        return False, 0


# 中心点识别，判断视觉切得是否正确
def exclude(pcd: o3d.geometry.PointCloud):
    # 1.通过地面点数判断是否切歪了
    pcd_np = np.asarray(pcd.points)
    pcd_np_counts = pcd_np.shape[0]

    pcd_floor_np = pcd_np[pcd_np[:, 2] < config.floor_height]
    pcd_floor_counts = pcd_floor_np.shape[0]

    proportion = pcd_floor_counts / pcd_np_counts

    if (proportion > (1 / 3)):
        scan_logger.info("排除：[地面点多]")
        return False, None
    else:
        # 切割地面
        pcd_not_floor = cut_floor(pcd_np)

    # 2.判断上下边斜率
    pcd_not_floor_np = np.asarray(pcd_not_floor.points)
    isSuccess_1, theta_degree_1 = fit_line(pcd_not_floor_np, "up")
    isSuccess_2, theta_degree_2 = fit_line(pcd_not_floor_np, "down")
    degree_difference = abs(theta_degree_2 - theta_degree_1)
    # 差值度数参数调整
    if isSuccess_1 and isSuccess_2 and degree_difference <= 2:
        print("排除完成")
        return True, pcd_not_floor
    else:
        scan_logger.info(f"排除：[上下边斜率差值大 - {degree_difference}]")
        return False, None


def examine_points_count(pcd: Union[np.ndarray, o3d.geometry.PointCloud]) -> bool:
    """
    判断当前点云是否为空
    :param pcd:  ndarray或者o3d.geometry.PointCloud，形状为 (n, 3)，表示 n 个点的三维坐标。
    :return: 空->false, 非空->true
    """
    if isinstance(pcd, o3d.geometry.PointCloud):
        pcd_np = np.asarray(pcd.points)
    else:
        pcd_np = pcd

    # 判断点数量
    points_count = pcd_np.shape[0]
    if points_count == 0:
        return False
    else:
        return True


def examine_points_count_lower_limit(pcd: Union[np.ndarray, o3d.geometry.PointCloud], lower_limit: int) -> tuple:
    """
    检查当前点云点数大于lower_limit
    :param pcd: ndarray或者o3d.geometry.PointCloud，形状为 (n, 3)，表示 n 个点的三维坐标。
    :param lower_limit: 检测最少得点数
    :return:是否低于点数
    """
    if isinstance(pcd, o3d.geometry.PointCloud):
        pcd_np = np.asarray(pcd.points)
    else:
        pcd_np = pcd

    # 判断点数量
    points_count = pcd_np.shape[0]
    if points_count > lower_limit:
        return (True, "点数正确")
    else:
        print(f"点数：{points_count}")
        return (False, "点数过少")


def examine_rectangle(rectangle_width, angle, width) -> tuple:
    """
    纠偏判断外接矩形，是否满足要求
    :param rectangle_width: 外接矩形的宽度
    :param angle: 外接矩形的旋转角度
    :param width: 调度传来的宽度
    :return:
    """
    # 判断外接矩形的宽度和调度传来的宽度
    if not (rectangle_width > (width - 0.2) and rectangle_width < (width + 0.2)):
        return (False, "宽度识别错误")

    if angle > 15:
        return (False, "识别矩形旋转角度过大")

    return (True, "识别正确")


def visual_line(p, x_points, y_points, pcd_np):
    # 创建多项式对象
    polynomial = np.poly1d(p)
    # 使用多项式对象生成一系列y值
    x_new = np.linspace(x_points.min(), x_points.max(), 300)
    y_new = polynomial(x_new)
    # 绘制原始数据点
    plt.scatter(x_points, y_points, color='red')
    plt.scatter(pcd_np[:, 0], pcd_np[:, 1], color='green')
    plt.scatter(x_points, y_points, color='blue')
    # 绘制拟合的直线
    plt.plot(x_new, y_new, color='blue')
    # 添加图例
    plt.legend()
    # 显示图表
    plt.show()


def examine_offset(offset_x_or_offset_y: float, threshold_x_or_y: float) -> tuple:
    """
    纠偏偏移异常检查
    :param offset_x_or_offset_y: 识别出的偏移，x或y
    :param threshold_x_or_y: 阈值 x或y
    :return:
    """
    if -threshold_x_or_y <= offset_x_or_offset_y <= threshold_x_or_y:
        return True, "偏移正常"
    else:
        return False, "偏移异常"


def examine_angle(angle: float, threshold_angle: float) -> tuple:
    '''
    纠偏角度异常检测
    :param angle: 识别出的角度
    :param threshold_angle: 阈值 角度
    :return:
    '''
    if -threshold_angle <= angle <= threshold_angle:
        return True, "角度正常"
    else:
        return False, "角度异常"
