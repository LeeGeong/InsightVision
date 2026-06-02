import numpy as np
from scipy.spatial import ConvexHull
from shapely.geometry import MultiPoint
import matplotlib.pyplot as plt
import scan.config as config
import math
import open3d as o3d
from typing import Union


def calculate_rectangle_rotated_center(x0, y0, length, width, angle_degrees, rotate_direction: str):
    """
    计算矩形绕右上角旋转后的中心点坐标
    :param x0: 右上角x坐标
    :param y0: 右上角y坐标
    :param length: 矩形的长（水平方向）
    :param width: 矩形的宽（竖直方向）
    :param angle_degrees: 旋转角度（度），小于90度
    :param rotate_direction: 绕右上角逆/顺时针旋转，up - 顺，down - 逆
    :return: 旋转后的中心点坐标(x, y)
    """
    # 将角度转换为弧度
    theta = math.radians(angle_degrees)
    cos_theta = math.cos(theta)
    sin_theta = math.sin(theta)

    # 计算相对于原点的旋转后的坐标变化量
    if rotate_direction == "+":
        delta_x = - (length * cos_theta + width * sin_theta) / 2  # 顺
        delta_y = (length * sin_theta - width * cos_theta) / 2

    else:
        delta_x = (- length * cos_theta + width * sin_theta) / 2  # 逆
        delta_y = -(length * sin_theta + width * cos_theta) / 2

    # 转换回原坐标系
    center_x = x0 + delta_x
    center_y = y0 + delta_y

    return center_x, center_y


def calculate_rectangle_rotated_center_left_up(x0, y0, length, width, angle_degrees, rotate_direction: str):
    """
    计算矩形绕左上角旋转后的中心点坐标
    :param x0: 左上角x坐标
    :param y0: 左上角y坐标
    :param length: 矩形的长（水平方向）
    :param width: 矩形的宽（竖直方向）
    :param angle_degrees: 旋转角度（度），小于90度
    :param rotate_direction: 绕右上角逆/顺时针旋转，up - 顺，down - 逆（给的是右上角的）
    :return: 旋转后的中心点坐标(x, y)
    """
    # 将角度转换为弧度
    theta = math.radians(angle_degrees)
    cos_theta = math.cos(theta)
    sin_theta = math.sin(theta)

    # 计算相对于原点的旋转后的坐标变化量
    if rotate_direction == "+":
        delta_x = (length * cos_theta - width * sin_theta) / 2  # 顺
        delta_y = -(length * sin_theta + width * cos_theta) / 2

    else:
        delta_x = (length * cos_theta + width * sin_theta) / 2  # 逆
        delta_y = (length * sin_theta - width * cos_theta) / 2

    # 转换回原坐标系
    center_x = x0 + delta_x
    center_y = y0 + delta_y

    return center_x, center_y

def minimum_bounding_rectangle(pcd: np.ndarray) -> tuple:
    """
    计算点云的最小外接矩形及其四个角点。
    参数：
    points: ndarray，形状为 (n, 3)，表示 n 个点的三维坐标。
    返回：
    rect: (length, width, angle, corners)
    - width, length: 矩形的宽度和长度
    - angle: 矩形的旋转角度（角度）
    - corners: 四个角点的坐标列表 [(x1, y1), (x2, y2), (x3, y3), (x4, y4)]
    """
    # 转换
    pcd_np_two_dimension = np.asarray(pcd.points)[:, :2]

    # 1. 计算点云的凸包
    hull = ConvexHull(pcd_np_two_dimension)
    hull_points = pcd_np_two_dimension[hull.vertices]

    # 2. 创建凸包的shapely对象
    convex_hull = MultiPoint(hull_points)

    # 3. 计算最小外接矩形
    min_rect = convex_hull.minimum_rotated_rectangle

    # 4. 获取最小外接矩形的四个角点, min_rect.exterior.coords会得到5个点，最后一个点是第一个点
    corners = np.asarray(min_rect.exterior.coords)[:-1]

    # 5. 计算矩形的旋转角度
    # 取前两个角点，计算这两个点的方向向量
    # p1 = np.array(corners[0])
    # p2 = np.array(corners[1])
    # 取y值小的两个点，计算这两个点的方向向量
    sorted_indices = np.argsort(corners[:, 1])  # 按照 y 值排序
    min_y_two_points = corners[sorted_indices[:2]]  # 获取前两个最小的点
    p1 = min_y_two_points[0]
    p2 = min_y_two_points[1]

    # 计算向量 (p2 - p1)
    vec = p2 - p1

    # 计算向量与水平轴的夹角（弧度），然后转换为度数
    angle = np.degrees(np.arctan2(vec[1], vec[0]))  # 使用arctan2来避免除零问题
    angle = abs(angle)
    if (angle > 90):
        angle = 180 - angle

    # 6. 获取矩形的宽度和长度
    sorted_indices = np.argsort(corners[:, 0])  # 按照 x 值排序
    max_x_two_points = corners[sorted_indices[2:]]  # 获取后两个最大的点
    width = np.linalg.norm(max_x_two_points[0] - max_x_two_points[1])  # 两个x值最大的点
    length = np.linalg.norm(p1 - p2)  # 两个y值最小的点

    # 7. 获取矩形的中心
    # x, y = min_rect.centroid.x, min_rect.centroid.y
    # print(x,y)

    if config.is_visual:
        visualization(corners, pcd_np_two_dimension)

    return (length, width, angle, corners)


def minimum_bounding_rectangle_to_corners(pcd: Union[o3d.geometry.PointCloud, np.ndarray]) -> np.ndarray:
    """
    计算点云的最小外接矩形得到四个角点。
    参数：
    points: ndarray或者o3d.geometry.PointCloud，形状为 (n, 3)，表示 n 个点的三维坐标。
    返回：
    corners: 四个角点的坐标列表 [(x1, y1), (x2, y2), (x3, y3), (x4, y4)]
    """
    if(isinstance(pcd, o3d.geometry.PointCloud)):
        pcd = np.asarray(pcd.points)

    # 转换
    pcd_np_two_dimension = pcd[:, :2]

    # 1. 计算点云的凸包
    hull = ConvexHull(pcd_np_two_dimension)
    hull_points = pcd_np_two_dimension[hull.vertices]

    # 2. 创建凸包的shapely对象
    convex_hull = MultiPoint(hull_points)

    # 3. 计算最小外接矩形
    min_rect = convex_hull.minimum_rotated_rectangle

    # 4. 获取最小外接矩形的四个角点, min_rect.exterior.coords会得到5个点，最后一个点是第一个点
    corners = np.asarray(min_rect.exterior.coords)[:-1]

    if config.is_visual:
        visualization(corners, pcd_np_two_dimension)

    return corners


def visualization(corners, points):
    # 可视化
    fig, ax = plt.subplots()

    # 绘制点云
    ax.scatter(points[:, 0], points[:, 1], color='blue', label='Points')

    # 绘制最小外接矩形
    corners = np.vstack([corners, corners[0]])  # 连接最后一个点到第一个点

    # 绘制矩形边
    ax.plot(corners[:, 0], corners[:, 1], color='red', label='Minimum Bounding Rectangle')

    # 显示图例
    ax.legend(loc='upper right',bbox_to_anchor=(1.05, 1), borderaxespad=0.)
    plt.tight_layout()  # 自动调整布局
    # plt.subplots_adjust(right=10)  #增加右侧边距，为图例腾出空间。
    # 设置图形比例相等，确保矩形显示正确
    ax.set_aspect('equal', 'box')

    # 展示图形
    plt.show()


if __name__ == '__main__':
    file_path = r"D:\项目\BaoGang_ScanAlgorithm\Data2\192.168.2.199_651260604809222_TPC10_20250305_638767900134804776 - Cloud.segmented.remaining.txt"
    from scan.util.open_file_to_pcd import get_pcd_np_from_file

    _, pcd_np, _ = get_pcd_np_from_file(file_path)
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(pcd_np)
    rect = minimum_bounding_rectangle(pcd)
    # print(f"中心点: ({rect[0]}, {rect[1]})")
    print(f"宽度: {rect[0]}, 高度: {rect[1]}")
    print(f"旋转角度: {rect[2]} 度")
    print("四个角点:", rect[3])
    visualization(rect, pcd_two_dimension)

# # 示例使用
# x0, y0 = 10, 5  # 右上角坐标
# length = 4
# width = 2
# angle = 30  # 顺时针旋转30度
#
# center = calculate_rotated_center_clockwise(x0, y0, length, width, angle)
# print(f"旋转后的中心点坐标：{center}")
