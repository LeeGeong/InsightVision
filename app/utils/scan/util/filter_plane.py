import numpy as np
import scan.config as config


def visual_z_height(x_or_y_2_z_mean: np.ndarray, flag: str):
    """
    可视化x或y方向，对应的z平均值曲线
    :param x_or_y_2_z_mean: numpy数组(n, 2)，格式 [[x或y, x或y对应的z_mean_height], ........]
    """
    x_or_y_total = x_or_y_2_z_mean[:, 0]
    z_total = x_or_y_2_z_mean[:, 1]
    import matplotlib.pyplot as plt
    # 绘制拟合的直线
    plt.plot(x_or_y_total, z_total, color='blue')
    # 添加 X 轴和 Y 轴标签
    if flag == "x":
        plt.xlabel('X')
    else:
        plt.xlabel('Y')
    plt.ylabel('Z_height')
    # 添加图例
    plt.legend("z_height")
    # 显示图表
    plt.show()


def y_range_to_plane(plane: list, pcd_np: np.ndarray) -> np.ndarray:
    """
    根据y的范围，得到平面
    :param plane: [y1,y2,y3, ........]
    :param pcd_np: 要根据范围进行切割的点云
    :return:
    """
    y_z_range_np = np.asarray(plane)
    y_z_range_np = y_z_range_np[y_z_range_np[:, 0].argsort()]  # 按y值从小到大排序
    y_min = y_z_range_np[0][0]
    y_max = y_z_range_np[-1][0]
    plane_np = pcd_np[(pcd_np[:, 1] >= y_min) & (pcd_np[:, 1] <= y_max)]

    return plane_np


def get_z_heights_from_y_interval(pcd_np: np.ndarray, interval=0.05) -> np.ndarray:
    """
    得到每个y间隔的z最大值
    :param pcd_np: 需要计算的点云 numpy数组(n,3)
    :param interval: 设定的y间隔
    :return: numpy数组(n, 2)， 格式[[y, y对应的z_mean_height], ......]
    """
    # 设定 y 值的间隔 (从最小到最大每 0.05 米)
    y_min, y_max = pcd_np[:, 1].min(), pcd_np[:, 1].max()
    y_intervals = np.arange(y_min, y_max + interval, interval)

    # 存储筛选后的点
    filtered_points = []
    for y_start in y_intervals:
        # 选择 X 值在 [x_start, x_start+0.05) 范围内的点
        y = y_start + interval
        mask_y = (pcd_np[:, 1] >= y_start) & (pcd_np[:, 1] < y)
        points_in_range = pcd_np[mask_y]

        if len(points_in_range) == 0:
            continue

        # z_mean = np.mean(points_in_range[:, 2])
        z_max = np.max(points_in_range[:, 2])

        # 将符合条件的点添加到最终列表中
        filtered_points.append(np.array([(y_start + y) / 2, z_max]))
    # 将所有过滤后的点合并成一个数组
    filtered_points = np.vstack(filtered_points)

    if config.is_visual:
        visual_z_height(filtered_points, "y")

    return filtered_points


def recognize_planes_y(processed_points: np.ndarray, slope_threshold=0.2, steel_width_threshold=0.8) -> list:
    """
    识别平面 - 大车方向y
    :param processed_points: numpy数组(n, 2)， 格式[[y, y对应的z_mean_height], ......]
    :param slope_threshold: 两个点的斜率在slope_threshold以下认为是一个平面内的点
    :param steel_width_threshold: 识别出的平面大于steel_width_threshold认为是一个平面
    :return: [平面1，平面2，......]  平面1格式 [y1,y2,y3,......]
    """
    processed_points = processed_points[processed_points[:, 0].argsort()]  # 按 y 值从小到大排序

    planes = []
    current_plane = [processed_points[0]]

    for i in range(1, len(processed_points)):
        y1, z1 = current_plane[-1]
        y2, z2 = processed_points[i]

        # 计算斜率
        slope = abs((z2 - z1) / (y2 - y1))
        # print(f"slope: {slope} - y - {y1} - z {z1}")

        if slope < slope_threshold:
            current_plane.append(processed_points[i])
        else:
            if len(current_plane) > 1:
                current_y_min = np.min(np.array(current_plane)[:, 0])
                current_y_max = np.max(np.array(current_plane)[:, 0])
                dis = current_y_max - current_y_min
                if dis > steel_width_threshold:  # 大于1m的认为可能是钢板
                    planes.append(np.array(current_plane))
            current_plane = [processed_points[i]]

    # 添加最后一个平面（如果存在）
    if len(current_plane) > 1:
        current_y_min = np.min(np.array(current_plane)[:, 0])
        current_y_max = np.max(np.array(current_plane)[:, 0])
        dis = current_y_max - current_y_min
        if dis > steel_width_threshold:  # 大于1m的认为可能是钢板
            planes.append(np.array(current_plane))

    if config.is_visual:
        if len(planes) != 0:
            for index, plane in enumerate(planes):
                print(f"在钢板宽y方向得到平面{index + 1} - y_min:{plane[0][0]} - y_max:{plane[-1][0]}")
        else:
            print(f"在钢板宽y方向没有平面")

    return planes


def filter_planes_y(planes: list, pcd_np: np.ndarray) -> np.ndarray:
    """
    筛选平面 - 大车方向y
    :param planes:[平面1，平面2，......]  平面1格式 [y1,y2,y3,......]
    :param pcd_np:需要切割的点云
    :return:
    """
    if len(planes) == 0:
        # TODO 大车方向，没识别出平面是一种什么情况
        filter_plane_np = pcd_np
    elif len(planes) == 1:
        filter_plane_np = y_range_to_plane(planes[0], pcd_np)
    else:
        # 留下平均高度高的
        max_z_height = 0
        filter_plane_np = None
        for plane in planes:
            current_plane = y_range_to_plane(plane, pcd_np)
            current_z_height = np.mean(current_plane[:, 2])
            # print("height" , current_z_height)
            if current_z_height > max_z_height:
                max_z_height = current_z_height
                filter_plane_np = current_plane

    # print(np.mean(filter_plane_np[:, 2]))
    if config.is_visual:
        if len(planes) != 0:
            processed_points = np.sort(filter_plane_np[:, 1] ) # 按 y 值从小到大排序
            print(f"在钢板宽y方向留下的平面 - y_min:{processed_points[0]} - y_max:{processed_points[-1]}")

    return filter_plane_np


def get_z_heights_from_x_interval(pcd_np: np.ndarray, interval=0.05) -> np.ndarray:
    """
    得到每个x间隔的z平均值
    :param pcd_np: 需要计算的点云 numpy数组(n,3)
    :param interval: 设定的x间隔
    :return: numpy数组(n, 2)， 格式[[y, y对应的z_mean_height], ......]
    """
    # 设定 X 值的间隔 (从最小到最大每 0.1 米)
    x_min, x_max = pcd_np[:, 0].min(), pcd_np[:, 0].max()
    x_intervals = np.arange(x_min, x_max + interval, interval)

    # 存储筛选后的点
    filtered_points = []
    for x_start in x_intervals:
        # 选择 X 值在 [x_start, x_start+0.05) 范围内的点
        x_end = x_start + interval
        mask_x = (pcd_np[:, 0] >= x_start) & (pcd_np[:, 0] < x_end)
        points_in_range = pcd_np[mask_x]

        if len(points_in_range) == 0:
            continue

        # z_mean = np.mean(points_in_range[:, 2])
        z_max = np.max(points_in_range[:, 2])
        # 将符合条件的点添加到最终列表中
        # filtered_points.append(np.array([(x_start + x_end) / 2, z_mean]))
        filtered_points.append(np.array([(x_start + x_end) / 2, z_max]))
    # 将所有过滤后的点合并成一个数组
    filtered_points = np.vstack(filtered_points)

    if config.is_visual:
        visual_z_height(filtered_points, "x")

    return filtered_points


def recognize_planes_x(processed_points: np.ndarray, slope_threshold=0.2, steel_length_threshold=3) -> list:
    """
    识别平面 - 小车方向x
    :param processed_points: numpy数组(n, 2)， 格式[[x, x对应的z_mean_height], ......]
    :param slope_threshold: 两个点的斜率在slope_threshold以下认为是一个平面内的点
    :param steel_length_threshold: 识别出的平面大于steel_length_threshold认为是一个平面
    :return: [平面1，平面2，......]  平面1格式 [y1,y2,y3,......]
    """
    processed_points = processed_points[processed_points[:, 0].argsort()]  # 按 x 值从小到大排序

    planes = []
    current_plane = [processed_points[0]]

    for i in range(1, len(processed_points)):
        x1, z1 = current_plane[-1]
        x2, z2 = processed_points[i]

        # 计算斜率
        slope = abs((z2 - z1) / (x2 - x1))
        # print(f"slope: {slope} - x - {x1} - z {z1}")

        if slope < slope_threshold:
            current_plane.append(processed_points[i])
        else:
            if len(current_plane) > 1:
                current_x_min = np.min(np.array(current_plane)[:, 0])
                current_x_max = np.max(np.array(current_plane)[:, 0])
                dis = current_x_max - current_x_min
                if dis > steel_length_threshold:  # 大于1m的认为可能是钢板
                    planes.append(np.array(current_plane))
            current_plane = [processed_points[i]]

    # 添加最后一个平面（如果存在）
    if len(current_plane) > 1:
        current_x_min = np.min(np.array(current_plane)[:, 0])
        current_x_max = np.max(np.array(current_plane)[:, 0])
        dis = current_x_max - current_x_min
        if dis > steel_length_threshold:  # 大于1m的认为可能是钢板
            planes.append(np.array(current_plane))

    if config.is_visual:
        if len(planes) != 0:
            for index, plane in enumerate(planes):
                print(f"在钢板长x方向得到平面{index + 1} - x_min:{plane[0][0]} - x_max:{plane[-1][0]}")
        else:
            print(f"在钢板长x方向没有平面")

    return planes


def filter_planes_x(planes: list, x_z_mean: np.ndarray, pcd_car_body: np.ndarray) -> float:
    """
    筛选平面 - 大车方向y
    :param planes:[平面1，平面2，......]  平面1格式 [y1,y2,y3,......]
    :param y_z_mean:
    :param pcd_car_body:
    :return:
    """
    if len(planes) == 0:
        # 空框架车
        x_z_mean_np = np.asarray(x_z_mean)
        x_z_mean_np = x_z_mean_np[x_z_mean_np[:, 0].argsort()]  # 按x值从小到大排序
        z_height = (x_z_mean_np[0][1] + x_z_mean_np[-1][1]) / 2
        # z_height = np.mean(pcd_car_body[:, 2])
    elif len(planes) == 1:
        z_height = plane_to_height(planes[0], pcd_car_body)
    else:
        # 留下平均高度高的
        z_heights = []
        for plane in planes:
            z_current_height = plane_to_height(plane, pcd_car_body)
            z_heights.append(z_current_height)
        z_height = np.max(np.asarray(z_heights))
    return z_height


def plane_to_height(plane: list, pcd_np: np.ndarray) -> np.ndarray:
    """
    得到每个平面的z_height
    :param plane:  平面格式 [x1,x2,x3,......]
    :param pcd_np: 需要切割的点云
    :return:
    """
    x_z_range_np = np.asarray(plane)
    x_z_range_np = x_z_range_np[x_z_range_np[:, 0].argsort()]  # 按x值从小到大排序
    x_min = x_z_range_np[0][0]
    x_max = x_z_range_np[-1][0]
    plane_body_np = pcd_np[(pcd_np[:, 0] >= x_min) & (pcd_np[:, 0] <= x_max)]
    z_height = np.mean(plane_body_np[:, 2])
    # z_height = get_z_height_plane(plane_body_np)

    return z_height

def get_z_height_plane(pcd_plane_np: np.ndarray) -> np.ndarray:
    """
    '''得到每个平面的z_height'''
    :param pcd_plane_np:
    :return:
    """
    # y两边往回缩40cm
    # 设定 X 值的间隔 (从最小到最大每 0.1 米)
    x_min = pcd_plane_np[:, 0].min()
    x_max = pcd_plane_np[:, 0].max()
    x_intervals = np.arange(x_min, x_max, 0.1)

    # 存储筛选后的点
    filtered_points = []

    for x_start in x_intervals:
        # 选择 X 值在 [x_start, x_start+0.1) 范围内的点
        mask_x = (pcd_plane_np[:, 0] >= x_start) & (pcd_plane_np[:, 0] < x_start + 0.1)
        points_in_range = pcd_plane_np[mask_x]

        if len(points_in_range) == 0:
            continue

        y_max = np.max(points_in_range[:, 1])
        y_min = np.min(points_in_range[:, 1])

        # # 选择 Z 值大于等于 max_z - 0.3 的点
        mask_z = (points_in_range[:, 1] >= y_min + 0.2) & (points_in_range[:, 1] <= y_max - 0.2)
        filtered_points_in_range = points_in_range[mask_z]

        # 将符合条件的点添加到最终列表中
        filtered_points.append(filtered_points_in_range)

    # 将所有过滤后的点合并成一个数组
    filtered_points = np.vstack(filtered_points)
    z_mean = np.mean(filtered_points[:, 2])

    return z_mean
