'''
识别钢板顶层高度
'''
import open3d as o3d
import numpy as np
from scan.util.open_file_to_pcd import get_pcd_np_from_file
from scan.util.filter import filter_np2np
from scan.util.cut import cut_floor
from scan.util.cluster import car_cluster
from scan.util.common import unit_conversion, visualization_pcd
from scipy.spatial import ConvexHull
from shapely.geometry import Polygon
import scan.config as config
from scan.util.exclude import examine_points_count
from scan.util.smooth import gaussian_filter
from scan.util.filter_plane import get_z_heights_from_y_interval, recognize_planes_y, filter_planes_y, \
    get_z_heights_from_x_interval, recognize_planes_x, filter_planes_x


def car_body_trans(pcd_np: np.ndarray) -> np.ndarray:
    """
    将车身向内平移 - 切掉两边的柱子和车身点云
    :param pcd_np:
    :return:
    """
    # 投影 - 去掉z，变成xy平面
    pcd_projection_np = pcd_np[:, :2]

    # 计算凸包
    pts = pcd_projection_np
    hull = ConvexHull(pts)

    # 获取凸包的顶点坐标
    hull_points = pcd_projection_np[hull.vertices, :2]

    # 创建 Shapely 多边形对象
    polygon = Polygon(hull_points)

    # 获取最小边界矩形
    min_rect = polygon.minimum_rotated_rectangle

    # 提取矩形的顶点坐标
    rect_coords = np.array(min_rect.exterior.coords.xy).T[:-1, :]

    # 找到两个长边对应的两组点
    maxY_idx = np.argmax(rect_coords[:, 1])  # y最上面的点, 找到与它一组的点
    lengths = np.linalg.norm(rect_coords - rect_coords[maxY_idx], ord=2, axis=1)
    lengths[np.argmax(lengths)] = -np.inf

    point_index = np.argmax(lengths)
    line1_points = np.asarray([rect_coords[maxY_idx], rect_coords[point_index]])  # 上面的线的两个点

    line2_points = np.delete(rect_coords, [maxY_idx, point_index], axis=0)  # 下面的线的两个点

    # 计算斜率
    k = (line1_points[0, 1] - line1_points[1, 1]) / (line1_points[0, 0] - line1_points[1, 0])
    # 计算截距
    b1 = line1_points[0, 1] - k * line1_points[0, 0]
    b2 = line2_points[0, 1] - k * line2_points[0, 0]
    # 向里面平移
    b1_trans = b1 - 0.25
    b2_trans = b2 + 0.25
    # 计算两条平行线之间的距离
    distance_threshold = abs(b1_trans - b2_trans) / np.sqrt(1 + k ** 2)

    # 找到两条平行线之间的点
    points_index = []
    for index, point in enumerate(pcd_np):
        x0, y0, _ = point

        # 计算点到两条线的距离
        distance1 = abs(k * x0 - y0 + b1_trans) / np.sqrt(k ** 2 + 1)
        distance2 = abs(k * x0 - y0 + b2_trans) / np.sqrt(k ** 2 + 1)

        # 判断是否在两条平行线之间
        if (distance1 < distance_threshold and distance2 < distance_threshold):
            points_index.append(index)

    pcd_translation_np = pcd_np[points_index]

    return pcd_translation_np


def get_z_height_car_all(pcd_car_body_np: np.ndarray) -> np.ndarray:
    '''卡车的z_height'''
    # 将车身向内平移 - 切掉两边的柱子和车身点云
    pcd_trans_np = car_body_trans(pcd_car_body_np)
    z_mean = np.mean(pcd_trans_np[:, 2])
    z_max = np.max(pcd_trans_np[:, 2])
    z_range = abs(z_max - z_mean)

    # 再过滤z平均值远的点
    mask = abs(pcd_trans_np[:, 2] - z_mean) <= z_range
    pcd_filter_np = pcd_trans_np[mask]
    z_mean_filter = np.mean(pcd_filter_np[:, 2])

    return z_mean_filter


def get_car_top(pcd: o3d.geometry.PointCloud, deep_height=0.2) -> o3d.geometry.PointCloud:
    # 顶层往下0.3米
    #TODO 顶层往下多少米，不能低于10cm，因为地面倾斜
    # 从0.3降低到0.2之后减少了起伏不平框架车提取平面的影响    所以起伏不平框架车最高点往上20cm以内的钢板，可能会识别错钢板
    pcd_np = np.asarray(pcd.points)

    # 设定 X 值的间隔 (从最小到最大每 0.1 米)
    x_min = pcd_np[:, 0].min()
    x_max = pcd_np[:, 0].max()
    x_intervals = np.arange(x_min, x_max, 0.1)

    # 存储筛选后的点
    filtered_points = []

    for x_start in x_intervals:
        # 选择 X 值在 [x_start, x_start+0.1) 范围内的点
        mask_x = (pcd_np[:, 0] >= x_start) & (pcd_np[:, 0] < x_start + 0.1)
        points_in_range = pcd_np[mask_x]

        if len(points_in_range) == 0:
            continue

        # 找到该 X 范围内 Z 的最大值
        max_z = points_in_range[:, 2].max()

        # 选择 Z 值大于等于 max_z - 0.3 的点
        mask_z = points_in_range[:, 2] >= max_z - deep_height
        filtered_points_in_range = points_in_range[mask_z]

        # 将符合条件的点添加到最终列表中
        filtered_points.append(filtered_points_in_range)

    # 将所有过滤后的点合并成一个数组
    filtered_points = np.vstack(filtered_points)

    pcd_filter = o3d.geometry.PointCloud()
    pcd_filter.points = o3d.utility.Vector3dVector(filtered_points)

    if (config.is_visual):
        print("上层点云提取结束")
        visualization_pcd(pcd_filter, window_name="上层点云")

    return pcd_filter


def get_height(pcd: o3d.geometry.PointCloud) -> np.ndarray:
    pcd_car_body_np = np.asarray(pcd.points)

    # 宝钢没有卡车
    # # 车的中间位置
    # x_max = np.max(pcd_np[:, 0])
    # x_min = np.min(pcd_np[:, 0])
    # x_mid = (x_max + x_min) / 2
    #
    # # 将车辆分成两段，判断那边z平均值大，大的为车头
    # pcd_x_small_np = pcd_np[pcd_np[:, 0] <= x_mid]
    # pcd_x_large_np = pcd_np[pcd_np[:, 0] > x_mid]
    #
    # z_mean_pcd1 = np.mean(pcd_x_small_np[:, 2])
    # z_mean_pcd2 = np.mean(pcd_x_large_np[:, 2])
    #
    # # 得到车身的x范围
    # if (z_mean_pcd1 < z_mean_pcd2):
    #     x_range = (x_min, x_mid)
    # else:
    #     x_range = (x_mid, x_max)
    #
    # flag = 0  # 0卡车，1框架车
    # # 根据两段距离差判断是框架车还是卡车
    # if (abs(z_mean_pcd2 - z_mean_pcd1) < 0.5):
    #     x_range = (x_min, x_max)
    #     flag = 1

    # # 根据范围得到点
    # pcd_car_body_np = pcd_np[(pcd_np[:, 0] >= x_range[0]) & (pcd_np[:, 0] <= x_range[1])]

    flag = 1
    if flag == 0:  # 卡车
        z_height_mean = get_z_height_car_all(pcd_car_body_np)
        # if config.is_visual:
        #     print(f"当前车为卡车，前半段与后半段的差距 {abs(z_mean_pcd2 - z_mean_pcd1)}")
    else:  # 框架车
        # 1.先根据钢板宽方向过滤(大车方向 - y)
        # 平滑处理
        pcd_smooth_np = gaussian_filter(pcd_car_body_np)
        y_to_z_height = get_z_heights_from_y_interval(pcd_smooth_np, interval=0.05)
        # 找到可能得平面
        planes_y = recognize_planes_y(y_to_z_height, slope_threshold=0.2)
        # 筛选平面
        # pcd_filter_width_np = filter_planes_y(planes_y, pcd_car_body_np)
        pcd_filter_width_np = filter_planes_y(planes_y, pcd_smooth_np)

        # 2.钢板长方向过滤
        # TODO 是否平滑处理, 现在已增加
        x_to_z_height = get_z_heights_from_x_interval(pcd_filter_width_np, interval=0.05)  # x每隔step，取z的平均值
        # 找到可能得平面
        planes = recognize_planes_x(x_to_z_height, slope_threshold=0.2)
        # 筛选平面, 得到高度
        z_height_mean = filter_planes_x(planes, x_to_z_height, pcd_filter_width_np)

    # 保留三位小数
    # z_height = reserve_decimal(z_height_mean)
    return z_height_mean


def get_data(isSuccess: bool, message: str, height=0.0) -> dict:
    return {
        "isSuccess": isSuccess,
        "height": height,
        "message": message
    }


def get_result(file_path: str, park_no: str) -> dict:
    '''
    钢板高度
    :param file_path: 点云文件路径
    :return: 钢板高度(float)
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
        # 提取车上层点云
        pcd_car_top = get_car_top(pcd_car)
        # 得到钢板高度
        car_height = get_height(pcd_car_top)
        # 转换单位
        height = int(unit_conversion(car_height))

        return get_data(True, "识别高度成功", height)
    except:
        return get_data(False, "识别高度失败")


if __name__ == "__main__":
    # file_dir = r"D:\项目\BaoGang_ScanAlgorithm\Data\TPC9_20250408_663313556742150_192.168.2.198.xyz"
    # file_dir = r"D:\项目\BaoGang_ScanAlgorithm\Data\TPC9_20250408_663314665164806_192.168.2.198.xyz"
    # file_dir = r"D:\项目\BaoGang_ScanAlgorithm\Data\TPC9_20250408_663316880474118_192.168.2.198.xyz"
    # file_dir = r"D:\项目\BaoGang_ScanAlgorithm\Data\TPC9_20250408_663321502400518_192.168.2.198.xyz"
    # file_dir = r"D:\项目\BaoGang_ScanAlgorithm\Data\TPC9_20250408_663322685542406_192.168.2.198.xyz"

    # file_dir = r"D:\项目点云文件\宝钢\扫描数据\扫描数据scan\2025\10\22\tpc2_10_22\TPC2_20251021_732668805242886_192.168.2.191.xyz"
    file_dir = r"D:\项目点云文件\宝钢\扫描数据\扫描数据scan\2025\10\22\tpc2_10_22\TPC2_20251021_732663619084294_192.168.2.191.xyz"

    res = get_result(file_dir, "TPC9")

    print(f"{res}")
