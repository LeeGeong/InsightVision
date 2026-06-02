import numpy as np
from typing import Union
import open3d as o3d

# 米 -> 毫米
def unit_conversion(number: Union[np.ndarray,float]) -> float:
    return number * 1000


# 保留三位小数
def reserve_decimal(number: Union[np.ndarray, float]) -> np.ndarray:
    return np.round(number, 3)

# 取整
def reserve_integer(number: Union[np.ndarray, float]) -> float:
    return float(np.floor(number))

# 毫米 -> 米
def unit_conversion_millimeter_to_meter(number: Union[np.ndarray,float]) -> float:
    return number / 1000

def estimate_pcd_np_size(pcd_np: np.ndarray) -> bool:
    points_size = pcd_np.shape[0]
    flag = True if points_size == 0 else False

    return flag

def visualization_pcd(pcd: Union[np.ndarray, o3d.geometry.PointCloud], window_name :str):
    """
    可视化点云
    :param pcd: 点云(numpy数组或者o3d.geometry.PointCloud)
    :param window_name: 窗口title
    :return:
    """
    if(isinstance(pcd, o3d.geometry.PointCloud)):
        point_cloud = pcd
    else:
        point_cloud = o3d.geometry.PointCloud()
        point_cloud.points = o3d.utility.Vector3dVector(pcd)

    o3d.visualization.draw_geometries([point_cloud], window_name=window_name, width=600, height=500)

def save_pcd(pcd: Union[np.ndarray, o3d.geometry.PointCloud], output_path:str):
    if(isinstance(pcd, o3d.geometry.PointCloud)):
        point_cloud = pcd
    else:
        point_cloud = o3d.geometry.PointCloud()
        point_cloud.points = o3d.utility.Vector3dVector(pcd)

    o3d.io.write_point_cloud(output_path, point_cloud)


