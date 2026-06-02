import open3d as o3d
import numpy as np
import scan.config as config
import matplotlib.pyplot as plt
from scan.util.common import reserve_decimal,unit_conversion


# 得到边界框内的点
def get_inner_points(pcd_np: np.array, x_min, x_max, y_min, y_max):
    if(pcd_np.shape[0] != 0):
        x_condition = (pcd_np[:,0] >= x_min) & (pcd_np[:,0] <= x_max)
        y_condition = (pcd_np[:,1] >= y_min) & (pcd_np[:,1] <= y_max)

        filter_np = pcd_np[x_condition & y_condition]
        filter_points = list(filter_np)
        return filter_points
    else:
        return []


def calculate_safe_area(pcd_np: np.asarray, pcd_segment_plane: o3d.geometry.PointCloud):
    # 找到钢板的四个边界
    pcd_segment_plane_np = np.asarray(pcd_segment_plane.points)
    x_min = np.min(pcd_segment_plane_np[:, 0])
    x_max = np.max(pcd_segment_plane_np[:, 0])
    y_min = np.min(pcd_segment_plane_np[:, 1])
    y_max = np.max(pcd_segment_plane_np[:, 1])
    z_max = np.max(pcd_segment_plane_np[:, 2])

    border2 = np.array([(x_min, y_min), (x_min, y_max), (x_max, y_max), (x_max, y_min), (x_min, y_min)])

    # 用钢板高度做切除
    pcd_cut_np = pcd_np[pcd_np[:, 2] > (z_max) + 0.02]

    # 得到边界框内的点
    pcd_inner = get_inner_points(pcd_cut_np, x_min, x_max, y_min, y_max)

    # 前后左右缩小
    pcd_inner_np = np.asarray(pcd_inner)
    if(pcd_inner_np.shape[0] != 0):
        inner_z_max = np.max(pcd_inner_np[:, 2])
        inner_z_min = np.min(pcd_inner_np[:, 2])
        if ((inner_z_max - inner_z_min) > 0.4):
            x_max = x_max - 0.3
            x_min = x_min + 0.3
            y_max = y_max - 0.3
            y_min = y_min + 0.3

    # 得到边界框内的点
    pcd_inner = get_inner_points(pcd_cut_np, x_min, x_max, y_min, y_max)

    # 缩小框
    # 每一个点先判断与哪个边界距离近，之后缩小框
    if len(pcd_inner) != 0:
        for point in pcd_inner:
            x_min_distance = abs(point[0] - x_min)
            x_max_distance = abs(point[0] - x_max)
            y_min_distance = abs(point[1] - y_min)
            y_max_distance = abs(point[1] - y_max)
            distance = np.array([x_min_distance, x_max_distance, y_min_distance, y_max_distance])
            min_index = np.argmin(distance)
            # 缩小边框
            if (min_index == 0):
                if (point[0] >= x_min):
                    x_min = point[0]
            elif (min_index == 1):
                if (point[0] <= x_max):
                    x_max = point[0]
            elif (min_index == 2):
                if (point[1] >= y_min):
                    y_min = point[1]
            else:
                if (point[1] <= y_max):
                    y_max = point[1]

    border1 = np.array([(x_min, y_min), (x_min, y_max), (x_max, y_max), (x_max, y_min), (x_min, y_min)])

    # 四个方向拓展
    while (True):
        pcd_inner_list = get_inner_points(pcd_cut_np, x_min, x_max, y_min, y_max)
        try_x_max = x_max + 0.01
        if (try_x_max >= np.max(pcd_np[:,0])):
            break
        try_pcd_inner_list = get_inner_points(pcd_cut_np, x_min, try_x_max, y_min, y_max)
        if (len(pcd_inner_list) == len(try_pcd_inner_list)):
            x_max = try_x_max
        else:
            x_max = x_max - 0.1
            break

    while (True):
        pcd_inner_list = get_inner_points(pcd_cut_np, x_min, x_max, y_min, y_max)
        try_x_min = x_min - 0.01
        if (try_x_min <= np.min(pcd_np[:,0])):
            break
        try_pcd_inner_list = get_inner_points(pcd_cut_np, try_x_min, x_max, y_min, y_max)
        if (len(pcd_inner_list) == len(try_pcd_inner_list)):
            x_min = try_x_min
        else:
            x_min = x_min + 0.1
            break

    while (True):
        pcd_inner_list = get_inner_points(pcd_cut_np, x_min, x_max, y_min, y_max)
        try_y_max = y_max + 0.01
        if (try_y_max >= np.max(pcd_np[:,1])):
            break
        try_pcd_inner_list = get_inner_points(pcd_cut_np, x_min, x_max, y_min, try_y_max)
        if (len(pcd_inner_list) == len(try_pcd_inner_list)):
            y_max = try_y_max
        else:
            break

    while (True):
        pcd_inner_list = get_inner_points(pcd_cut_np, x_min, x_max, y_min, y_max)
        try_y_min = y_min - 0.01
        if (try_y_min <= np.min(pcd_np[:,1])):
            break
        try_pcd_inner_list = get_inner_points(pcd_cut_np, x_min, x_max, try_y_min, y_max)
        if (len(pcd_inner_list) == len(try_pcd_inner_list)):
            y_min = try_y_min
        else:
            break

    area = {
        "SafetyMaxX": unit_conversion(reserve_decimal(x_max)),
        "SafetyMinX": unit_conversion(reserve_decimal(x_min)),
        "SafetyMaxY": unit_conversion(reserve_decimal(y_max)),
        "SafetyMinY": unit_conversion(reserve_decimal(y_min))
    }

    print(f"安全区为{area}")

    if (config.is_visual):
        plt.figure()
        plt.plot(pcd_cut_np[:, 0], pcd_cut_np[:, 1], 'o', label='Points')
        border = np.array([(x_min, y_min), (x_min, y_max), (x_max, y_max), (x_max, y_min), (x_min, y_min)])
        plt.plot(border[:, 0], border[:, 1], 'g-', lw=2, label='border')
        plt.plot(border1[:, 0], border1[:, 1], 'r-', lw=2, label='缩小框')
        plt.plot(border2[:, 0], border2[:, 1], 'y-', lw=2, label='钢板边界')
        plt.show()

    return area
