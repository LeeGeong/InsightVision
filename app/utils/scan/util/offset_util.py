import numpy as np
import scan.config as config
from scan.util.common import unit_conversion_millimeter_to_meter


def z_translation(pcd_np: np.ndarray) -> tuple:
    """
    运动中纠偏按照起重机z值平移
    :param pcd_np: 每行数据 -（x米；y 米；z米；r 反射率；craneZ 毫米）
    :return: (单位转换后的点云， craneZ最小值)
    """
    # x米；y 米；z米；r 反射率；craneZ 毫米
    x = pcd_np[:, 0]  # 米
    y = pcd_np[:, 1]  # 米
    z = pcd_np[:, 2]  # 米
    crane_z = unit_conversion_millimeter_to_meter(pcd_np[:, 4])  # 毫米->米
    idx = np.argmin(crane_z)
    min_crane_z = crane_z[idx]  # 最小craneZ值

    new_z = z - (crane_z - min_crane_z)
    # 构建新数组(x, y, new_z)
    pcd_translation_np = np.column_stack((x, y, new_z))

    if config.is_visual:
        import open3d as o3d
        if isinstance(pcd_translation_np, o3d.geometry.PointCloud):
            point_cloud = pcd_translation_np
        else:
            point_cloud = o3d.geometry.PointCloud()
            point_cloud.points = o3d.utility.Vector3dVector(pcd_translation_np)

        o3d.visualization.draw_geometries([point_cloud], window_name="高度平移", width=600, height=500)

    if config.is_save_z_translation:
        import os
        import time
        import open3d as o3d
        output_dir = os.path.join("../Data2", f"{str(time.time())}_z_translate.xyz")
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(pcd_translation_np)
        o3d.io.write_point_cloud(filename=output_dir, pointcloud=pcd)
        print(f"保存成功: {output_dir}")

    return pcd_translation_np, min_crane_z
