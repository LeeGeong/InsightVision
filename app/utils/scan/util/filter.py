'''
2.点云数据离群点去除
'''
import open3d as o3d
import re
import os
import numpy as np
import scan.config as config


def filter_np2np(pcd_np: np.ndarray) -> np.ndarray:
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(pcd_np)

    # 离群点滤波
    pcd_filter, _ = pcd.remove_statistical_outlier(nb_neighbors=10, std_ratio=2)

    pcd_filter_np = np.asarray(pcd_filter.points)

    # 可视化
    if (config.is_visual):
        print("离群点过滤结束")
        from scan.util.common import visualization_pcd
        visualization_pcd(pcd_filter, window_name="离群点过滤")
    return pcd_filter_np


def filter(pcd_np: np.ndarray) -> o3d.geometry.PointCloud:
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(pcd_np)

    # 离群点滤波
    pcd_filter, _ = pcd.remove_statistical_outlier(nb_neighbors=10, std_ratio=2)

    # print("离群点过滤结束")

    # 可视化
    if (config.is_visual):
        from scan.util.common import visualization_pcd
        visualization_pcd(pcd_filter, window_name="离群点过滤")

    if config.is_save_filter:
        import time
        output_dir = os.path.join("../Data2", f"{str(time.time())}_filter.xyz")
        o3d.io.write_point_cloud(filename=output_dir, pointcloud=pcd_filter)
        print(f"保存成功: {output_dir}")

    return pcd_filter


def point_in_rectangle(p, rect):
    """
    判断点 p 是否在矩形 rect 内部（包括边界）。
    :param p: 点坐标 (x, y)
    :param rect: 矩形的四个点列表，顺序为 [p1, p2, p3, p4]（顺时针或逆时针）
    :return: True 如果点在矩形内部或边界上，否则 False
    """
    n = len(rect)
    cps = []  # 存储每条边的叉积
    for i in range(n):
        a = rect[i]  # 边起点
        b = rect[(i + 1) % n]  # 边终点（循环处理）
        # 计算向量 AB 和 AP
        ab = (b[0] - a[0], b[1] - a[1])
        ap = (p[0] - a[0], p[1] - a[1])
        # 计算叉积: AB.x * AP.y - AB.y * AP.x
        cp = ab[0] * ap[1] - ab[1] * ap[0]
        cps.append(cp)

    # 检查所有叉积同号（所有 <=0 或所有 >=0），表示点在所有边的同一侧或边上
    if all(cp <= 0 for cp in cps) or all(cp >= 0 for cp in cps):
        return True
    else:
        return False


def filter_electromagnet_lifting(pcd_np: np.ndarray, rectangles: list) -> np.ndarray:
    """
    从点集中剔除所有在任意矩形内部的点（包括边界）
    :param pcd_np:点集列表，每个点为 (x, y)
    :param rectangles:矩形列表，每个矩形为四个点的列表 [ [p1, p2, p3, p4], ... ],点的顺序必须连续（顺时针或逆时针）
    :return:过滤后的点集列表 [[x,y], ...]
    """
    filtered_points = []
    for p in pcd_np:
        in_any_rect = False
        for rect in rectangles:
            if point_in_rectangle(p, rect):
                in_any_rect = True
                break  # 点在一个矩形内，无需检查其他矩形
        if not in_any_rect:
            filtered_points.append(p)

    filtered_points = np.asarray(filtered_points)

    if config.is_visual:
        # print(f"原始点数: {len(pcd_np)}")
        # print(f"过滤后点数: {len(filtered_points)}")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots()
        # 绘制点云
        ax.scatter(filtered_points[:, 0], filtered_points[:, 1], color='blue', label='Points')
        # 显示图例
        ax.legend()
        # 设置图形比例相等，确保矩形显示正确
        ax.set_aspect('equal', 'box')
        # 展示图形
        plt.show()

    return filtered_points


if __name__ == "__main__":
    file_dir = r"D:\工作\项目\JinZhongSteelRecognize\Data2\638548386408471103 - Cloud.section.xyz"
    pcd = o3d.io.read_point_cloud(file_dir)

    pcd_filter = filter(pcd)

    # 点云上色
    pcd_filter.paint_uniform_color([1, 0, 0])
    # 保存点云
    output_dir = os.path.join("../Data2", re.findall('\d+', file_dir)[1] + "_filter.xyz")
    # o3d.visualization.draw_geometries([pcd_filter])
    o3d.io.write_point_cloud(output_dir, pcd_filter)
