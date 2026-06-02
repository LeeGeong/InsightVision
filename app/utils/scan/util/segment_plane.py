import open3d as o3d
import scan.config as config
import os
import re


def segment_plane(pcd: o3d.geometry.PointCloud):
    """
    :param pcd:
    :return:
    """
    # 使用RANSAC算法来拟合平面
    _, inliers = pcd.segment_plane(distance_threshold=0.16, ransac_n=3, num_iterations=1000)

    # 获取平面模型参数
    # [a, b, c, d] = plane_model

    # 获取平面内点的索引
    inlier_cloud = pcd.select_by_index(inliers)
    outlier_cloud = pcd.select_by_index(inliers, invert=True)

    # 可视化识别结果
    if config.is_visual:
        print("平面拟合完成")
        inlier_cloud.paint_uniform_color([1, 0, 0])  # 红色
        outlier_cloud.paint_uniform_color([0, 1, 0])  # 绿色
        # o3d.visualization.draw_geometries([inlier_cloud])
        o3d.visualization.draw_geometries([inlier_cloud, outlier_cloud], window_name="平面拟合", width=600, height=500)

    # 输出识别结果
    if len(inliers) > 0:
        return True, inlier_cloud
    else:
        return False, None


if __name__ == "__main__":
    file_dir = r"D:\项目\BaoGang_ScanAlgorithm\Data\TPC12_20250325_658244907765766_192.168.2.199.xyz"

    pcd = o3d.io.read_point_cloud(file_dir)

    _, pcd_filter, _ = segment_plane(pcd)

    if config.is_save:
        output_dir = os.path.join("../Data", re.findall("\d+", file_dir)[0] + "_segment.xyz")
        o3d.io.write_point_cloud(output_dir, pcd_filter)
