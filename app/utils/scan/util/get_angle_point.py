import open3d as o3d
import numpy as np
import scan.config as config
from scan.util.common import reserve_decimal


def get_angle_point(pcd: o3d.geometry.PointCloud):
    # 得到点云包围盒
    # 计算包围盒
    bbox = pcd.get_axis_aligned_bounding_box()

    # 获取包围盒的最小边界和最大边界
    max_bound = bbox.max_bound

    # 计算包围盒的左下角点
    right_upper_point = [max_bound[0], max_bound[1], max_bound[2]]

    pcd_np = np.asarray(pcd.points)
    # 找到距离目标点最近的点
    distances = np.linalg.norm(pcd_np - right_upper_point, axis=1)  # 计算每个点到目标点的距离
    nearest_index = np.argmin(distances)  # 找到最小距离对应的索引

    nearest_point = pcd_np[nearest_index]

    # 保留三位小数
    angle_point = reserve_decimal(nearest_point)

    # 可视化点
    if (config.is_visual):
        # colors = plt.cm.tab10(np.linspace(0,1,2))[:, :3]
        points_color = []
        for point in pcd_np:
            if (point[0] == nearest_point[0]) and (point[1] == nearest_point[1]) and (point[2] == nearest_point[2]):
                points_color.append([1, 0, 0])
            else:
                points_color.append([0, 1, 0])

        pcd.colors = o3d.utility.Vector3dVector(np.asarray(points_color))

        bbox.color = [0, 0, 1]
        o3d.visualization.draw_geometries([pcd, bbox])

    return angle_point


def get_angle_point_right_up_from_corners(corners: np.ndarray) -> tuple:
    '''
    从矩形的四个角点，得到右上角点、顺逆旋转
    '''
    sorted_indices = np.argsort(corners[:, 1])  # 按照 y 值排序
    max_y_two_points = corners[sorted_indices[2:]]  # 获后前两个最大的点,y值最大点 - 上边的两个点
    sorted_indices = np.argsort(max_y_two_points[:, 0])  # 按照 x 值排序
    max_x_two_point = max_y_two_points[sorted_indices[1:]][0]  # 获取后一个最大的点，x值最大点 - 右上角点
    other_point = max_y_two_points[sorted_indices[:1]][0]  # 左上角点

    # 通过矩形上边两个点判断顺时针旋还是逆时针旋
    if (max_x_two_point[1] > other_point[1]):
        rotate = "-"  # 逆时针
    else:
        rotate = "+"  # 顺时针

    return (max_x_two_point, rotate)


def get_angle_point_left_up_from_corners(corners: np.ndarray) -> tuple:
    '''
    从矩形的四个角点，得到左上角点、顺逆旋转
    '''
    sorted_indices = np.argsort(corners[:, 1])  # 按照 y 值排序
    max_y_two_points = corners[sorted_indices[2:]]  # 获后前两个最大的点,y值最大点 - 上边的两个点
    sorted_indices = np.argsort(max_y_two_points[:, 0])  # 按照 x 值排序
    max_x_two_point = max_y_two_points[sorted_indices[1:]][0]  # 获取后一个最大的点，x值最大点 - 右上角点
    other_point = max_y_two_points[sorted_indices[:1]][0]  # 左上角点

    # 通过矩形上边两个点判断顺时针旋还是逆时针旋
    if (max_x_two_point[1] > other_point[1]):
        rotate = "-"  # 逆时针
    else:
        rotate = "+"  # 顺时针

    return (other_point, rotate)


if __name__ == "__main__":
    # file_dir = r"D:\工作\项目\JinZhongSteelRecognize\Data2\638548386408471103_cluster.xyz"
    file_dir = r"D:\工作\项目\JinZhongSteelRecognize\Data2\638548390042529218_cluster.xyz"

    pcd = o3d.io.read_point_cloud(file_dir)

    angle_point = get_angle_point(pcd)
