'''
识别卡车范围
'''
import open3d as o3d
import numpy as np
from scan.util.open_file_to_pcd import file_to_pcd_np
from scan.util.filter import filter_np2np
from scan.util.cut import cut_floor
from scan.util.common import reserve_decimal,unit_conversion
from scan.util.cluster import car_cluster


# 得到卡车范围
def get_truck_area(pcd: o3d.geometry.PointCloud) -> dict:
    pcd_np = np.asarray(pcd.points)
    truck_maxX = unit_conversion(reserve_decimal(np.max(pcd_np[:, 0])))
    truck_minX = unit_conversion(reserve_decimal(np.min(pcd_np[:, 0])))
    truck_maxY = unit_conversion(reserve_decimal(np.max(pcd_np[:, 1])))
    truck_minY = unit_conversion(reserve_decimal(np.min(pcd_np[:, 1])))
    truck_maxZ = unit_conversion(reserve_decimal(np.max(pcd_np[:, 2])))
    truck_minZ = 0.0
    truck_area = {
        "TruckMaxX": truck_maxX,
        "TruckMinX": truck_minX,
        "TruckMaxY": truck_maxY,
        "TruckMinY": truck_minY,
        "TruckMaxZ": truck_maxZ,
        "TruckMinZ": truck_minZ,
    }

    return truck_area


def get_result(file_path: str) -> dict:
    '''
    卡车范围
    :param file_path:点云文件路径
    :return:识别结果（dict）
    '''
    result = {
        "isSuccess": True,
        "truck_area": None,
    }
    try:
        pcd_np = file_to_pcd_np(file_path)
        # 离群点去除
        pcd_filter = filter_np2np(pcd_np)
        # 切割地面
        pcd_not_floor = cut_floor(pcd_filter)
        # 聚类 - 得到车的点云
        pcd_truck = car_cluster(pcd_not_floor)
        # 得到车辆范围
        truck_area = get_truck_area(pcd_truck)
        result["truck_area"] = truck_area
    except:
        result["isSuccess"] = False
        result["truck_area"] = {
            "TruckMaxX": 0.0,
            "TruckMinX": 0.0,
            "TruckMaxY": 0.0,
            "TruckMinY": 0.0,
            "TruckMaxZ": 0.0,
            "TruckMinZ": 0.0,
        }

    return result


if __name__ == "__main__":
    file_dir = r"D:\项目\BaoGang_ScanAlgorithm\Data\638678751396409734.xyz"
    area = get_result(file_dir)

    print(f"卡车范围：{area}")
