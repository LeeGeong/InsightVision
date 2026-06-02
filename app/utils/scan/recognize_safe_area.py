'''
根据人工选点，判断安全区
'''
import config
import numpy as np
from scan.util.open_file_to_pcd import get_pcd_np_from_file
from scan.util.cut import cut_xy
from scan.util.common import reserve_integer, unit_conversion


# 得到边界框内的点
def get_inner_points(pcd_np: np.array, x_min, x_max, y_min, y_max):
    if (pcd_np.shape[0] != 0):
        x_condition = (pcd_np[:, 0] >= x_min) & (pcd_np[:, 0] <= x_max)
        y_condition = (pcd_np[:, 1] >= y_min) & (pcd_np[:, 1] <= y_max)

        filter_np = pcd_np[x_condition & y_condition]
        filter_points = list(filter_np)
        return filter_points
    else:
        return []


def get_safe_area(pcd_np: np.ndarray, point: list) -> dict:
    # 毫米换米
    point = [value / 1000 for value in point]

    # 切割框大小与边界大小检查匹配，减少区域
    # 查找的安全区范围：中心点左右2米，前后6米
    box_x_min = point[0] - 6
    box_x_max = point[0] + 6
    box_y_min = point[1] - 2
    box_y_max = point[1] + 2

    box_x_min = max(box_x_min, np.min(pcd_np[:, 0]))
    box_x_max = min(box_x_max, np.max(pcd_np[:, 0]))
    box_y_min = max(box_y_min, np.min(pcd_np[:, 1]))
    box_y_max = min(box_y_max, np.max(pcd_np[:, 1]))

    # print(f'边界 -- {box_x_min}, {box_x_max}, {box_y_min}, {box_y_max}')

    # 根据区域切割
    pcd_cut_np = cut_xy(pcd_np, box_x_min, box_x_max, box_y_min, box_y_max)

    # 假定一个平面边界
    x_min = point[0] - 0.2
    x_max = point[0] + 0.2
    y_min = point[1] - 0.2
    y_max = point[1] + 0.2

    border2 = np.array([(x_min, y_min), (x_min, y_max), (x_max, y_max), (x_max, y_min), (x_min, y_min)])

    # 用钢板高度做切除
    # 切割比人工选点高20厘米以下的点（看情况是否用得到的xy值得到一个z值）
    pcd_cut_np = pcd_cut_np[pcd_cut_np[:, 2] > (point[2] + 0.3)]

    # 四个方向拓展
    while (True):
        pcd_inner_list = get_inner_points(pcd_cut_np, x_min, x_max, y_min, y_max)
        try_x_max = x_max + 0.01
        if (try_x_max >= box_x_max):
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
        if (try_x_min <= box_x_min):
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
        if (try_y_max >= box_y_max):
            break
        try_pcd_inner_list = get_inner_points(pcd_cut_np, x_min, x_max, y_min, try_y_max)
        if (len(pcd_inner_list) == len(try_pcd_inner_list)):
            y_max = try_y_max
        else:
            break

    while (True):
        pcd_inner_list = get_inner_points(pcd_cut_np, x_min, x_max, y_min, y_max)
        try_y_min = y_min - 0.01
        if (try_y_min <= box_y_min):
            break
        try_pcd_inner_list = get_inner_points(pcd_cut_np, x_min, x_max, try_y_min, y_max)
        if (len(pcd_inner_list) == len(try_pcd_inner_list)):
            y_min = try_y_min
        else:
            break

    area = {
        "SafetyMaxX": reserve_integer(unit_conversion(x_max)),
        "SafetyMinX": reserve_integer(unit_conversion(x_min)),
        "SafetyMaxY": reserve_integer(unit_conversion(y_max)),
        "SafetyMinY": reserve_integer(unit_conversion(y_min))
    }

    if config.is_visual:
        import matplotlib.pyplot as plt
        plt.figure()
        plt.plot(pcd_cut_np[:, 0], pcd_cut_np[:, 1], 'o', label='Points')
        border = np.array([(x_min, y_min), (x_min, y_max), (x_max, y_max), (x_max, y_min), (x_min, y_min)])
        plt.plot(border[:, 0], border[:, 1], 'g-', lw=2, label='safe_area')
        plt.plot(border2[:, 0], border2[:, 1], 'y-', lw=2, label='steel_border')
        plt.legend(loc='upper right')
        plt.show()

    return area


def get_data(isSuccess: bool, safety_max_x: float = 0, safety_min_x: float = 0, safety_max_y: float = 0,
             safety_min_y: float = 0):
    return {
        "isSuccess": isSuccess,
        "safe_area": {
            "SafetyMinX": safety_min_x,
            "SafetyMaxX": safety_max_x,
            "SafetyMinY": safety_min_y,
            "SafetyMaxY": safety_max_y
        }
    }


def get_result(file_path: str, point: list) -> dict:
    '''
    安全区
    :param file_path: 点云文件地址
    :param point: 钢板抓点
    :return: 安全区（dict）
    '''
    try:
        is_success, pcd_np, _ = get_pcd_np_from_file(file_path)
        if not is_success:
            return get_data(is_success)

        safe_area = get_safe_area(pcd_np, point)

        return get_data(True, safe_area["SafetyMaxX"], safe_area["SafetyMinX"], safe_area["SafetyMaxY"], safe_area["SafetyMinY"])

    except:
        return get_data(False)



if __name__ == '__main__':
    file_dir = r"D:\项目\BaoGang_ScanAlgorithm\Data\TPC11_20250423_668524910198790_192.168.2.198.xyz"
    res = get_result(file_dir, [13675, 423503, 2612])

    print(res)
