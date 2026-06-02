import open3d as o3d
import scan.config as config
from scan.util.common import unit_conversion, reserve_decimal


def get_grab_point(pcd: o3d.geometry.PointCloud) -> list:
    bbox = pcd.get_oriented_bounding_box()
    center_point = bbox.get_center()

    center_point = [unit_conversion(reserve_decimal(value)) for value in center_point]

    print(f"抓点为 -- {center_point}")

    if (config.is_visual):
        bbox.color = [0, 1, 0]
        o3d.visualization.draw_geometries([pcd, bbox])

    return center_point


def get_center_point(pcd: o3d.geometry.PointCloud) -> list:
    bbox = pcd.get_oriented_bounding_box()
    center_point = bbox.get_center()

    if (config.is_visual):
        print(f"中心点为 -- {center_point}")
        bbox.color = [0, 1, 0]  # 绿色
        o3d.visualization.draw_geometries([pcd, bbox])

    return center_point


if __name__ == "__main__":
    file_dir = r"D:\项目\JinZhongSteelRecognize\Data\638580312587878729_segment.xyz"
    pcd = o3d.io.read_point_cloud(file_dir)

    get_grab_point(pcd)
