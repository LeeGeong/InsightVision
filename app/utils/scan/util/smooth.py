# 平滑处理
import open3d as o3d
import numpy as np
from sklearn.neighbors import NearestNeighbors
import scan.config as config


def gaussian_filter(pcd_np: np.ndarray, sigma=0.1, k_neighbors=20) -> np.ndarray:
    """
    对点云进行高斯滤波
    :param pcd: 输入的点云
    :param sigma: 高斯滤波的标准差 (用于控制平滑的强度)
    :param k_neighbors: 近邻数量 (决定每个点的邻域大小)
    :return: 滤波后的点云
    """

    # 使用 KDTree 或 NearestNeighbors 查找邻域
    nbrs = NearestNeighbors(n_neighbors=k_neighbors, algorithm='auto').fit(pcd_np)
    distances, indices = nbrs.kneighbors(pcd_np)

    # 计算每个点的高斯权重
    filtered_points = np.copy(pcd_np)
    for i, point in enumerate(pcd_np):
        # 计算邻域点的距离
        neighborhood_distances = distances[i]

        # 计算高斯权重 (根据距离和标准差)
        weights = np.exp(-neighborhood_distances ** 2 / (2 * sigma ** 2))

        # 使用权重对邻域点进行加权平均
        weighted_sum = np.sum(weights[:, np.newaxis] * pcd_np[indices[i]], axis=0)
        filtered_points[i] = weighted_sum / np.sum(weights)

    if config.is_visual:
        print("高斯结束")
        from scan.util.common import visualization_pcd
        visualization_pcd(filtered_points, window_name="高斯")

    if (config.is_save):
        import os
        import time
        output_dir = os.path.join("../Data2", f"{str(time.time())}_smooth.xyz")
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(filtered_points)
        o3d.io.write_point_cloud(filename=output_dir, pointcloud=pcd)
        print(f"保存成功: {output_dir}")
    return filtered_points


if __name__ == '__main__':
    file_path = r"D:\项目\BaoGang_ScanAlgorithm\Data\TPC10_20250423_668553690836998_192.168.2.199.xyz"
    from scan.util.open_file_to_pcd import get_pcd_np_from_file
    isSuccess, pcd_np, message = get_pcd_np_from_file(file_path)
    # 对点云进行高斯滤波
    sigma = 0.1  # 高斯滤波标准差
    filtered_pcd = gaussian_filter(pcd_np, sigma=sigma)

    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(filtered_pcd)

    # 保存平滑后的点云
    o3d.io.write_point_cloud("D:\项目\BaoGang_ScanAlgorithm\Data\smoothed_point_cloud_gaosi.xyz", pcd)
