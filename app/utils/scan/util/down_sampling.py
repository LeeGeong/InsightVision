# 降采样
import open3d as o3d
from typing import Union
import numpy as np


def down_sampling_to_np(pcd: Union[np.ndarray, o3d.geometry.PointCloud]) -> np.ndarray:
    """
    点云降采样
    :param pcd: 需要降采样的点云
    :return: 降采样后的点云
    """
    if isinstance(pcd, o3d.geometry.PointCloud):
        point_cloud = pcd
    else:
        point_cloud = o3d.geometry.PointCloud()
        point_cloud.points = o3d.utility.Vector3dVector(pcd)

    point_cloud = point_cloud.voxel_down_sample(0.03)
    pcd_down_sampling = np.asarray(point_cloud.points)

    return pcd_down_sampling
