'''
聚类
'''
import open3d as o3d
import numpy as np
import scan.config as config
import matplotlib.pyplot as plt
import copy


def car_cluster(pcd: o3d.geometry.PointCloud) -> o3d.geometry.PointCloud:
    """
    车聚类
    :param pcd: o3d.geometry.PointCloud，形状为 (n, 3)，表示 n 个点的三维坐标。
    :return: 聚类后的点云， ndarray或者o3d.geometry.PointCloud，形状为 (n, 3)，表示 n 个点的三维坐标。
    """
    # 降采样
    pcd = pcd.voxel_down_sample(0.03)

    pcd_np = np.asarray(pcd.points)

    labels = np.array(pcd.cluster_dbscan(eps=0.3, min_points=10, print_progress=False))

    # 统计每个簇的点的数量
    unique_labels, label_counts = np.unique(labels, return_counts=True)

    # 删除点数小于5000点的簇
    labels_filter = unique_labels[label_counts > 5000]
    mask_filter = []
    for label in labels:
        if label in labels_filter:
            mask_filter.append(True)
        else:
            mask_filter.append(False)
    pcd_filter_np = pcd_np[mask_filter]

    pcd_filter = o3d.geometry.PointCloud()
    pcd_filter.points = o3d.utility.Vector3dVector(pcd_filter_np)

    # 可视化
    if (config.is_visual):
        print("聚类完成")
        from scan.util.common import visualization_pcd
        visualization_pcd(pcd_filter, window_name="聚类")

    return pcd_filter


def cluster_steel_plate(pcd: o3d.geometry.PointCloud, exclusion_width: float) -> o3d.geometry.PointCloud:
    '''
    钢板进行聚类
    :param pcd: 点云，o3d.geometry.PointCloud，形状为 (n, 3)，表示 n 个点的三维坐标。
    :param exclusion_width: 聚类后排除簇的宽度
    '''
    # 降采样
    pcd = pcd.voxel_down_sample(0.03)
    # 进行聚类
    pcd_np = np.asarray(pcd.points)
    labels = np.asarray(pcd.cluster_dbscan(eps=0.3, min_points=5, print_progress=False))    # labels = -1 表示该点在密度聚类中被认为是噪声点，无法归入任何一个有效簇

    # 聚类得到的簇数
    num_clusters = labels.max() + 1
    # print(f"point cloud has {num_clusters} clusters")

    # 排除x范围小的簇
    pcd_filter_np = []
    labels_filter = []
    for cluster_label in np.unique(labels):
        # 获得当前label的簇
        cluster_np = pcd_np[labels == cluster_label]
        # 计算当前簇的 X 范围
        x_range = np.max(cluster_np[:, 0]) - np.min(cluster_np[:, 0])
        #print(cluster_label,cluster_np.shape, x_range)

        if x_range > exclusion_width and cluster_label != -1:   # labels = -1 表示该点在密度聚类中被认为是噪声点，无法归入任何一个有效簇
            pcd_filter_np.append(cluster_np)
            labels_filter.append(cluster_label)

    pcd_filter = o3d.geometry.PointCloud()
    pcd_filter.points = o3d.utility.Vector3dVector(np.vstack(pcd_filter_np))

    # 可视化
    if (config.is_visual):
        colors = plt.cm.tab10(np.linspace(0, 1, num_clusters))[:, :3]
        color_points = [colors[label] if label != -1 else [0, 0, 0] for label in labels]     # 设置噪声点labels=-1的点为黑色
        pcd.colors = o3d.utility.Vector3dVector(color_points)
        # 通过平移调整第二个点云的位置
        pcd_filter_copy = copy.deepcopy(pcd_filter).translate((25, 0, 0))  # 将第二个点云向右平移1.5单位
        o3d.visualization.draw_geometries([pcd, pcd_filter_copy], window_name="左-聚类，右-聚类排除", width=1200,
                                          height=600)

    # 保存
    if (config.is_save):
        import os
        import time
        output_dir = os.path.join("../Data2", f"{str(time.time())}" + " _cluster.xyz")
        from scan.util.common import save_pcd
        save_pcd(pcd_filter, output_dir)
        print(f"保存成功: {output_dir}")

    return pcd_filter


def cluster_magnet(pcd_np: np.ndarray, exclusion_width: float = 0) -> o3d.geometry.PointCloud:
    '''
    电磁铁进行聚类
    :param pcd: 点云，o3d.geometry.PointCloud，形状为 (n, 3)，表示 n 个点的三维坐标。
    :param exclusion_width: 聚类后排除簇的宽度
    '''
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(pcd_np)

    # 降采样
    pcd = pcd.voxel_down_sample(0.03)
    # 进行聚类
    pcd_np = np.asarray(pcd.points)
    labels = np.asarray(pcd.cluster_dbscan(eps=0.1, min_points=5, print_progress=False))    # labels = -1 表示该点在密度聚类中被认为是噪声点，无法归入任何一个有效簇

    # 聚类得到的簇数
    num_clusters = labels.max() + 1
    # print(f"point cloud has {num_clusters} clusters")

    # 排除x范围小的簇
    pcd_filter_np = []
    labels_filter = []
    for cluster_label in np.unique(labels):
        # 获得当前label的簇
        cluster_np = pcd_np[labels == cluster_label]
        # 计算当前簇的 X 范围
        x_range = np.max(cluster_np[:, 0]) - np.min(cluster_np[:, 0])
        #print(cluster_label,cluster_np.shape, x_range)

        if cluster_label != -1:   # labels = -1 表示该点在密度聚类中被认为是噪声点，无法归入任何一个有效簇
            pcd_filter_np.append(cluster_np)
            labels_filter.append(cluster_label)

    pcd_filter = o3d.geometry.PointCloud()
    if len(pcd_filter_np) != 0:  # 聚类后没有聚在一起的簇，全是labels = -1
        pcd_filter.points = o3d.utility.Vector3dVector(np.vstack(pcd_filter_np))

    # 可视化
    if (config.is_visual):
        colors = plt.cm.tab10(np.linspace(0, 1, num_clusters))[:, :3]
        color_points = [colors[label] if label != -1 else [0, 0, 0] for label in labels]     # 设置噪声点labels=-1的点为黑色
        pcd.colors = o3d.utility.Vector3dVector(color_points)
        # 通过平移调整第二个点云的位置
        pcd_filter_copy = copy.deepcopy(pcd_filter).translate((25, 0, 0))  # 将第二个点云向右平移1.5单位
        o3d.visualization.draw_geometries([pcd, pcd_filter_copy], window_name="左-聚类，右-聚类排除", width=1200,
                                          height=600)

    # 保存
    if (config.is_save):
        import os
        import time
        output_dir = os.path.join("../Data2", f"{str(time.time())}" + " _cluster.xyz")
        from scan.util.common import save_pcd
        save_pcd(pcd_filter, output_dir)
        print(f"保存成功: {output_dir}")

    return pcd_filter
