import open3d as o3d
import numpy as np
import scan.config as config
from shapely.geometry import Point, Polygon
from scan.util.common import visualization_pcd
from scipy.spatial import ConvexHull


# 切割地面
def cut_floor(pcd_np: np.ndarray) -> o3d.geometry.PointCloud:
    # 切割地面和上方
    # points_not_floor = pcd_np[pcd_np[:, 2] >= config.floor_height]

    # 宝钢地面不平，拿到1m以下的点云，每隔10cm删除最低点往上40cm当做删除地面
    points_cut_up = pcd_np[pcd_np[:, 2] >= 1]
    points_cut_bottom = pcd_np[pcd_np[:, 2] < 1]

    if points_cut_bottom.shape[0] == 0:
        # 认为没有地面点
        pcd_cut = o3d.geometry.PointCloud()
        pcd_cut.points = o3d.utility.Vector3dVector(points_cut_up)

        if config.is_visual:
            print("切割地面完成")
            visualization_pcd(pcd_cut, window_name="切割地面")
        return pcd_cut

    # 设定 X 值的间隔 (从最小到最大每 0.1 米)
    x_min = points_cut_bottom[:, 0].min()
    x_max = points_cut_bottom[:, 0].max()
    x_intervals = np.arange(x_min, x_max, 0.1)

    # 存储筛选后的点
    filtered_points = []

    for x_start in x_intervals:
        # 选择 X 值在 [x_start, x_start+0.1) 范围内的点
        mask_x = (points_cut_bottom[:, 0] >= x_start) & (points_cut_bottom[:, 0] < x_start + 0.1)
        points_in_range = points_cut_bottom[mask_x]

        if len(points_in_range) == 0:
            continue

        # 找到该 X 范围内 Z 的最小值
        min_z = points_in_range[:, 2].min()

        # 选择 Z 值大于等于 min_z + 0.4 的点
        mask_z = points_in_range[:, 2] >= min_z + 0.4
        filtered_points_in_range = points_in_range[mask_z]

        # 将符合条件的点添加到最终列表中
        filtered_points.append(filtered_points_in_range)

    # 将所有过滤后的点合并成一个数组
    filtered_points = np.vstack(filtered_points)
    point_not_floor_np = np.vstack((filtered_points, points_cut_up))

    pcd_cut = o3d.geometry.PointCloud()
    pcd_cut.points = o3d.utility.Vector3dVector(point_not_floor_np)

    if config.is_visual:
        print("切割地面完成")
        visualization_pcd(pcd_cut, window_name="切割地面")

    return pcd_cut


# 从xy对点云进行切割
def cut_xy(pcd_np: np.ndarray, x_min, x_max, y_min, y_max) -> np.ndarray:
    """
    根据xy范围切割点云
    :param pcd_np: ndarray，形状为 (n, 3)，表示 n 个点的三维坐标。
    :param x_min: x范围最小值
    :param x_max: x范围最大值
    :param y_min: y范围最小值
    :param y_max: y范围最大值
    :return: 切割后结果，ndarray，形状为 (n, 3)，表示 n 个点的三维坐标。
    """
    # 切割x
    point_cut_x = pcd_np[(pcd_np[:, 0] >= x_min) & (pcd_np[:, 0] <= x_max)]

    # 切割y
    points_cut_y = point_cut_x[(point_cut_x[:, 1] >= y_min) & (point_cut_x[:, 1] <= y_max)]

    # 可视化
    if config.is_visual:
        print("切割完成")
        visualization_pcd(points_cut_y, window_name="切割完成")

    # 保存
    # if(config.is_save):
    #     pcd_cut = o3d.geometry.PointCloud()
    #     pcd_cut.points = o3d.utility.Vector3dVector(points_cut_y)
    #     output_dir = os.path.join("../Data", re.findall("\d+", file_dir)[0] + "_cut.xyz")
    #     o3d.io.write_point_cloud(output_dir, pcd_cut)
    #     print("保存成功")

    return points_cut_y


# 从xyz对点云进行切割
def cut_xyz(pcd_np: np.ndarray, x_min, x_max, y_min, y_max, z_min, z_max) -> np.ndarray:
    """
    根据xyz范围切割点云
    :param pcd_np: ndarray，形状为 (n, 3)，表示 n 个点的三维坐标。
    :param x_min: x范围最小值
    :param x_max: x范围最大值
    :param y_min: y范围最小值
    :param y_max: y范围最大值
    :param z_min: z范围最小值
    :param z_max: z范围最大值
    :return: 切割后结果，ndarray，形状为 (n, 3)，表示 n 个点的三维坐标。
    """
    # 切割x
    point_cut_x = pcd_np[(pcd_np[:, 0] >= x_min) & (pcd_np[:, 0] <= x_max)]

    # 切割y
    points_cut_y = point_cut_x[(point_cut_x[:, 1] >= y_min) & (point_cut_x[:, 1] <= y_max)]

    # 切割z
    points_cut_z = points_cut_y[(points_cut_y[:, 2] >= z_min) & (points_cut_y[:, 2] <= z_max)]

    # 可视化
    if (config.is_visual):
        visualization_pcd(points_cut_z, "切割完成")

    # 保存
    if (config.is_save):
        import os
        import time
        output_dir = os.path.join("../Data2", f"{str(time.time())}_cut.xyz")
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(points_cut_z)
        o3d.io.write_point_cloud(filename=output_dir, pointcloud=pcd)
        print(f"保存成功: {output_dir}")

    return points_cut_z


def cut_x(pcd_np: np.ndarray, x_min, x_max) -> np.ndarray:
    """
    根据x范围切割点云
    :param pcd_np: ndarray，形状为 (n, 3)，表示 n 个点的三维坐标。
    :param x_min: x范围最小值
    :param x_max: x范围最大值
    :return: 切割后结果，ndarray，形状为 (n, 3)，表示 n 个点的三维坐标。
    """
    # 切割x
    point_cut_x = pcd_np[(pcd_np[:, 0] >= x_min) & (pcd_np[:, 0] <= x_max)]

    # 可视化
    # if (config.is_visual):
    #     visualization_pcd(point_cut_x, "切割完成")

    # 保存
    if (config.is_save):
        import os
        import time
        output_dir = os.path.join("../Data2", f"{str(time.time())}_cut.xyz")
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(point_cut_x)
        o3d.io.write_point_cloud(filename=output_dir, pointcloud=pcd)
        print(f"保存成功: {output_dir}")

    return point_cut_x


# 根据视觉的点进行切割
def cut_from_rect_point(pcd_np: np.ndarray, rect_points: list):
    '''
    根据四个点切割点云
    :param pcd: ndarray，形状为 (n, 3)，表示 n 个点的三维坐标。
    :param rect_points: 四边形的四个点
    :return:传来的点数是否正确、切割后的pcd、异常原因
    '''
    if (len(rect_points) != 4):
        return False, None

    # 下采样
    # pcd = pcd.voxel_down_sample(voxel_size=0.03)

    # 单位装换 毫米->米
    rect_points = np.asarray(rect_points, dtype=float) / float(1000)

    # 根据四个点进行切割，留下矩形框内的点 - 减少下一步过滤点for循环的点数
    x_max = np.max(rect_points[:, 0])
    x_min = np.min(rect_points[:, 0])
    y_max = np.max(rect_points[:, 1])
    y_min = np.min(rect_points[:, 1])
    pcd_cut_np = cut_xy(pcd_np, x_min, x_max, y_min, y_max)

    # 创建四边形
    rect = Polygon(rect_points)

    # 过滤点
    points_filter = []
    for point in pcd_cut_np:
        # 创建一个点
        p = Point(point[0], point[1])

        # 使用contains方法判断点是否在多边形内部
        if rect.contains(p):
            points_filter.append(point)

    pcd_filter_np = np.asarray(points_filter)
    pcd_filter = o3d.geometry.PointCloud()
    pcd_filter.points = o3d.utility.Vector3dVector(pcd_filter_np)

    if config.is_visual:
        print("根据视觉切割完成")
        visualization_pcd(pcd_filter, window_name="根据视觉切割完成")

    return True, pcd_filter


def cut_from_points(pcd_np: np, angel_points: list) -> np.ndarray:
    """
    根据钢板角点切割
    :param pcd_np: 要切割的点云
    :param angel_points: 钢板的四个角点 [左上角点，左下角点，右上角点，右下角点]
    :return:切割后的点云
    """
    # 根据四个点进行切割，留下矩形框内的点（框是内接矩形）
    x_max = np.min((angel_points[2][0], angel_points[3][0]))
    x_min = np.max((angel_points[0][0], angel_points[1][0]))
    y_max = np.min((angel_points[0][1], angel_points[2][1]))
    y_min = np.max((angel_points[1][1], angel_points[3][1]))

    pcd_cut_np = cut_xy(pcd_np, x_min, x_max, y_min, y_max)

    return pcd_cut_np
