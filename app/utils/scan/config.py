# 可视化
is_visual = False

# 保存切割
is_save = False
is_save_z_translation = False   # 保存运动中纠偏按照起重机z值平移点云
is_save_filter = False
is_save_align_area = False # 保存对齐切片的点云

# 地面高度
floor_height = 0.65  # 米

# 对齐装置 -- 单位米
align_device = {
    # x_small: 北侧对齐，x_large：南侧对齐
    # 延伸通道
    "TPC9": {
        "x_small": [9.80, 10.17, 413.60, 415.86, 2.162],  # x_small, x_large, y_small, y_large，对齐装置下限高度值
        "x_large": [17.418, 17.773, 413.60, 415.823, 2.147],
        "uniform_addition": [0.05, 0.05]  # 对齐装置统一偏差加值 [北，南]
    },
    "TPC11": {
        "x_small": [9.84, 10.17, 425.717, 427.804, 2.235],
        "x_large": [17.344, 17.725, 425.717, 427.804, 2.272],
        "uniform_addition": [0.05, 0.05]
    },
    "TPC10": {
        "x_small": [30.53, 30.85, 413.60, 415.92, 2.151],
        "x_large": [38.00, 38.30, 413.60, 415.95, 2.155],
        "uniform_addition": [0.04, 0.06]
    },
    "TPC12": {
        "x_small": [30.40, 30.72, 425.70, 427.804, 2.267],
        "x_large": [38.00, 38.31, 425.747, 427.804, 2.259],
        "uniform_addition": [0.05, 0.065]
    },
    # 西三通道
    "TPC1": {
        "x_small": [9.89, 10.26, 90.15, 92.18, 2.216],  # x_small, x_large, y_small, y_large，对齐装置下限高度值
        "x_large": [17.43, 17.84, 90.15, 92.18, 2.226],
        "uniform_addition": [0.00, -0.06]  # 对齐装置统一偏差加值 [北，南]
    },
    "TPC3": {
        "x_small": [9.93, 10.34, 105.86, 107.90, 2.220],
        "x_large": [17.46, 17.91, 105.86, 107.90, 2.226],
        "uniform_addition": [-0.03, -0.09]
    },
    "TPC2": {
        "x_small": [30.46, 30.81, 90.15, 92.19, 2.207],
        "x_large": [38.00, 38.30, 90.15, 92.19, 2.217],
        "uniform_addition": [0.04, 0.04]
    },
    "TPC4": {
        "x_small": [30.40, 30.89, 105.84, 107.91, 2.239],
        "x_large": [38.08, 38.45, 105.84, 107.91, 2.244],
        "uniform_addition": [0.05, 0.05]
    }
}

# 纠偏
# 1.设备编号，与对应的切割参数
EqNo2CutParam = {
    "C12": {
        "x_small": -14.26,  # 长16米，  以问现场，钢板最长13米
        "x_large": 1.74,
        "y_small": -3.63,  # 宽6米
        "y_large": 2.37,
        "k": 1.007,  # 一元一次方程 -> 一个最低craneZ值 对应 一个切割的z值(吊具和钢板的中间点)
        "b": -11.6136,
        "z_small_1": -6.59,  # lifting_height1:5400 -> 已弃用
        "z_large_1": -6.09,
        "z_small_2": -8.04,  # lifting_height2:4000 -> 已弃用
        "z_large_2": -7.54,
        "crane_spreader_center_point": [-6.261, -0.63],  # 吊具中心点
        "electromagnet_lifting_cut": [
            [-12.56, 0.17, -2.17, 0.89, -6.09, -5.83],   # 电磁铁吊具 x_min, x_max, y_min, y_max, z_min -> 已弃用, z_max -> 已弃用
            [[-12.56, -11.13],      # 每块电磁铁范围 x_min, x_max
             [-10.10, -8.8],
             [-7.98, -6.72],
             [-5.82, -4.48],
             [-3.64, -2.26],
             [-1.32, 0.03]],
        ]
    },
    "C11": {
        "x_small": -1.76,  # 长16米
        "x_large": 14.24,
        "y_small": -2.29,  # 宽6米
        "y_large": 3.71,
        "k": 1.0067,  # 一元一次方程 -> 一个最低craneZ值 对应 一个切割的z值(吊具和钢板的中间点)
        "b": -11.7107,
        "z_small_1": -6.76,  # lifting_height1:5400 -> 已弃用
        "z_large_1": -6.26,
        "z_small_2": -8.16,  # lifting_height2:4000, 没配置 -> 已弃用
        "z_large_2": -7.66,
        "crane_spreader_center_point": [6.24, 0.712],  # 吊具中心点
        "electromagnet_lifting_cut": [
            [-0.23, 12.72, -0.79, 2.00,-6.26,-5.91],  # 电磁铁吊具 x_min, x_max, y_min, y_max, z_min -> 已弃用, z_max -> 已弃用
            [[0.01, 1.27],  # 每块电磁铁范围 x_min, x_max
             [2.22, 3.65],
             [4.43, 5.84],
             [6.57, 7.95],
             [8.80, 10.12],
             [11.12, 12.37]],
        ]
    },
    "C10": {
        "x_small": -1.75,  # 长16米，  以问现场，钢板最长13米
        "x_large": 14.25,
        "y_small": -2.71,  # 宽6米
        "y_large": 3.29,
        "k": 1.0131,  # 一元一次方程 -> 一个最低craneZ值 对应 一个切割的z值(吊具和钢板的中间点)
        "b": -11.7631,
        "z_small_1": 0,  # lifting_height1:5400 -> 已弃用
        "z_large_1": -6.27,
        "z_small_2": 0,  # lifting_height2:4000 -> 已弃用
        "z_large_2": 0,
        "crane_spreader_center_point": [6.254, 0.291],  # 吊具中心点
        "electromagnet_lifting_cut": [
            [-0.11, 12.54, -1.68, 1.96, 0, 0],  # 电磁铁吊具 x_min, x_max, y_min, y_max, z_min -> 已弃用, z_max -> 已弃用
            [[0.01, 1.32],  # 每块电磁铁范围 x_min, x_max
             [2.26, 3.58],
             [4.43, 5.84],
             [6.57, 7.99],
             [8.80, 10.18],
             [11.12, 12.37]],
        ]
    },
    "C9": {
        "x_small": -1.64,  # 长16米，  以问现场，钢板最长13米
        "x_large": 14.36,
        "y_small": -2.76,  # 宽6米
        "y_large": 3.24,
        "k": 1.0187,  # 一元一次方程 -> 一个最低craneZ值 对应 一个切割的z值(吊具和钢板的中间点)
        "b": -11.69,
        "z_small_1": -6.59,  # lifting_height1:5400 -> 已弃用
        "z_large_1": -6.09,
        "z_small_2": -8.16,  # lifting_height2:4000, 没配置 -> 已弃用
        "z_large_2": -7.66,
        "crane_spreader_center_point": [6.36, 0.24],  # 吊具中心点 没配置
        "electromagnet_lifting_cut": [
            [-0.10, 12.66, -1.23, 1.72, -6.09, -5.84],  # 电磁铁吊具 x_min, x_max, y_min, y_max, z_min -> 已弃用, z_max -> 已弃用
            [[-0.01, 1.34],  # 每块电磁铁范围 x_min, x_max
             [2.37, 3.59],
             [4.60, 5.72],
             [6.78, 8.10],
             [8.99, 10.26],
             [11.24, 12.37]],
        ]
    }
}

# 2.异常阈值
point_count = 10000
#todo 阈值根据现场看调整
offset_x_threshold = 0.27    # 小车方向异常检测阈值，单位米
offset_y_threshold = 0.15   # 大车方向异常检测阈值，单位米
offset_angle_threshold = 2  # 钢板角度异常检测阈值，单位度；调度超过正负2度会纠偏，阈值大于这个值


# 钢板高低差 - 扫描误差
error = 0.02  # 米
