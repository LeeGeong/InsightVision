#!/usr/bin/env python3
# """compute_rt.py
#
# 计算世界坐标系到相机坐标系的旋转矩阵 R 和平移向量 t。
# 使用ACEG点来求解，用BDFH点来做验证。
# 输入：预置的 8 个世界点、对应的 PTZ 值、相机在世界中的位置。
# 输出：打印 R、t、各点残差角度，并把结果写到 JSON 文件。
# 可作为脚本直接运行，也可以导入其中的函数到其它项目中。
#
# 用法：
#     python3 compute_rt.py
# """

from math import radians, degrees, acos
import numpy as np
import json
import argparse
from math import cos, sin


# # ==================== 用户输入数据(延伸跨验证) ====================
# # 定义8个空间点在3D世界坐标系中的坐标（单位：毫米）
# 这些点构成一个矩形区域的四个角点和四个边中点
A_3D = [5669, 419143, 612]  # TPC9右上角点 - 用于求解
B_3D = [21969, 419187, 528]  # TPC9右下角点 - 用于验证
C_3D = [5705, 422233, 618]  # TPC11左上角点 - 用于求解
D_3D = [21899, 426262, 476]  # TPC11右下角点 - 用于验证
E_3D = [42463, 419089, 405]  # TPC10左上角点 - 用于求解
F_3D = [42558, 415135, 398]  # TPC10右上角点 - 用于验证
G_3D = [42409, 426254, 401]  # TPC12左上角点 - 用于求解
H_3D = [26152, 426207, 491]  # TPC12左下角点 - 用于验证

# 对应的8个空间点在PTZ相机坐标系中的PTZ参数
# PTZ参数范围：pan(-1到1)，tilt(-1到1)
A_PTZ = [-0.918888867, 0.0160000026]  # 点A的PTZ参数 - 用于求解
B_PTZ = [-0.978333354, -0.808952391]  # 点B的PTZ参数 - 用于验证
C_PTZ = [-0.866666675, 0.0291428342]  # 点C的PTZ参数 - 用于求解
D_PTZ = [-0.509999931, -0.464190453]  # 点D的PTZ参数 - 用于验证
E_PTZ = [0.0983333364, 0.0312380828]  # 点E的PTZ参数 - 用于求解
F_PTZ = [0.162222221, 0.0312380828]  # 点F的PTZ参数 - 用于验证
G_PTZ = [-0.0211110432, 0.0693333223]  # 点G的PTZ参数 - 用于求解
H_PTZ = [-0.309499949, -0.460190475]  # 点H的PTZ参数 - 用于验证

camera_location = [24061, 421651, 15425]   #3.59


# # ==================== 用户输入数据(延申框架车) ====================
# # 定义8个空间点在3D世界坐标系中的坐标（单位：毫米）
# 这些点构成一个矩形区域的四个角点和四个边中点
# A_3D = [6656, 415447, 2450]  # TPC9左上角点 - 用于求解
# B_3D = [21810, 418878, 2463]  # TPC9右下角点 - 用于验证
# C_3D = [6715, 425953, 2115]  # TPC11右上角点 - 用于求解
# D_3D = [18805, 422502, 2083]  # TPC11左下角点 - 用于验证
# E_3D = [40439, 418902, 1945]  # TPC10左上角点 - 用于求解
# F_3D = [28328, 418994, 2041]  # TPC10右下角点 - 用于验证
# G_3D = [37788, 422487, 2530]  # TPC12右上角点 - 用于求解
# H_3D = [28243, 425519, 2696]  # TPC12左下角点 - 用于验证
#
# # 对应的8个空间点在PTZ相机坐标系中的PTZ参数
# # PTZ参数范围：pan(-1到1)，tilt(-1到1)
# A_PTZ = [0.826111078, 0.0979047492]  # 点A的PTZ参数 - 用于求解
# B_PTZ = [0.725555599, -0.713714302]  # 点B的PTZ参数 - 用于验证
# C_PTZ = [-0.99000001, 0.0996190384]  # 点C的PTZ参数 - 用于求解
# D_PTZ = [-0.951111078, -0.49276188]  # 点D的PTZ参数 - 用于验证
# E_PTZ = [-0.0644444749, 0.0577142611]  # 点E的PTZ参数 - 用于求解
# F_PTZ = [0.000555555569, -0.567047536]  # 点F的PTZ参数 - 用于验证
# G_PTZ = [-0.138888896, -0.00685715443]  # 点G的PTZ参数 - 用于求解
# H_PTZ = [-0.372222215, -0.368952364]  # 点H的PTZ参数 - 用于验证
#
# camera_location = [24075, 420267, 15420]   #3.59

################################################################################

# # ==================== 用户输入数据(延申车位线) ====================
# # 定义8个空间点在3D世界坐标系中的坐标（单位：毫米）
# 这些点构成一个矩形区域的四个角点和四个边中点
# A_3D = [21969, 419187, 528]  # 左上角点 - 用于求解
# B_3D = [5689, 419143, 612]  # 左下角点 - 用于验证
# C_3D = [42463, 419089, 405]  # 右下角点 - 用于求解
# D_3D = [42558, 415135, 398]  # 右上角点 - 用于验证
# E_3D = [5689, 426117, 507]  # 上边中点 - 用于求解
# F_3D = [21899, 426262, 476]  # 右边中点 - 用于验证
# G_3D = [26152, 426207, 491]  # 下边中点 - 用于求解
# H_3D = [42486, 422291, 397]  # 左边中点 - 用于验证
#
# # 对应的8个空间点在PTZ相机坐标系中的PTZ参数
# # PTZ参数范围：pan(-1到1)，tilt(-1到1)
# A_PTZ = [0.756111145, -0.774666607]  # 点A的PTZ参数 - 用于求解
# B_PTZ = [0.896611094, 0.032952372]  # 点B的PTZ参数 - 用于验证
# C_PTZ = [-0.0694444478, 0.0636190474]  # 点C的PTZ参数 - 用于求解
# D_PTZ = [-0.00388895674, 0.0805714205]  # 点D的PTZ参数 - 用于验证
# E_PTZ = [-0.979444444, 0.0655237809]  # 点E的PTZ参数 - 用于求解
# F_PTZ = [-0.688333273, -0.485142887]  # 点F的PTZ参数 - 用于验证
# G_PTZ = [-0.473388851, -0.473714262]  # 点G的PTZ参数 - 用于求解
# H_PTZ = [-0.12611118, 0.0636190474]  # 点H的PTZ参数 - 用于验证
#
# camera_location = [24061, 421651, 15425]   #3.59



# ############################ 用户输入数据（东三） JJH###########################
# 定义8个空间点在3D世界坐标系中的坐标（单位：毫米）
# 这些点构成一个矩形区域的四个角点和四个边中点
# A_3D = [21314, 308794, 5]  # TPC1左上角点 - 用于求解
# B_3D = [5438, 304844, -10]  # TPC1右下角点 - 用于验证
# C_3D = [27237, 308824, 51]  # TPC2右上角点 - 用于求解
# D_3D = [43843, 308784, 194]  # TPC2左下角点 - 用于验证
# E_3D = [21319, 315033, -47]  # TPC3左上角点 - 用于求解
# F_3D = [5247, 319063, -110]  # TPC3右下角点 - 用于验证
# G_3D = [27291, 319142, -111]  # TPC4右上角点 - 用于求解
# H_3D = [43945, 319124, 90]  # TPC4左上角点 - 用于验证
#
# # 对应的8个空间点在PTZ相机坐标系中的PTZ参数
# # PTZ参数范围：pan(-1到1)，tilt(-1到1)
# A_PTZ = [0.247222215, -0.795619011]  # 点A的PTZ参数 - 用于求解
# B_PTZ = [0.347777784, -0.0114288332]  # 点B的PTZ参数 - 用于验证
# C_PTZ = [-0.406111151, -0.685142875]  # 点C的PTZ参数 - 用于求解
# D_PTZ = [-0.532222152, 0.0598095134]  # 点D的PTZ参数 - 用于验证
# E_PTZ = [0.810500026, -0.605142772]  # 点E的PTZ参数 - 用于求解
# F_PTZ = [0.582777798, 0.0655237809]  # 点F的PTZ参数 - 用于验证
# G_PTZ = [-0.926111102, -0.345904768]  # 点G的PTZ参数 - 用于求解
# H_PTZ = [-0.691666663, 0.0979047492]  # 点H的PTZ参数 - 用于验证 可能不准
#
# camera_location = [23383, 311336, 15504]   #3.50
##########################################################################


# # ############################ 用户输入数据（西三） JJH###########################
# # 定义8个空间点在3D世界坐标系中的坐标（单位：毫米）
# # 这些点构成一个矩形区域的四个角点和四个边中点
# A_3D = [5753, 91348, 553]  # TPC1左上角点 - 用于求解
# B_3D = [21884, 95362, 582]  # TPC1右下角点 - 用于验证
# C_3D = [5929, 106730, 537]  # TPC2右上角点 - 用于求解
# D_3D = [21879, 102708, 611]  # TPC2左下角点 - 用于验证
# E_3D = [42345, 95181, 730]  # TPC3左上角点 - 用于求解
# F_3D = [26496, 91252, 579]  # TPC3右下角点 - 用于验证
# G_3D = [42480, 102609, 688]  # TPC4右上角点 - 用于求解
# H_3D = [42501, 106722, 669]  # TPC4左上角点 - 用于验证
#
# # 对应的8个空间点在PTZ相机坐标系中的PTZ参数
# # PTZ参数范围：pan(-1到1)，tilt(-1到1)
# A_PTZ = [-0.851666689, -0.0392381214]  # 点A的PTZ参数 - 用于求解
# B_PTZ = [0.826666713, -0.75942862]  # 点B的PTZ参数 - 用于验证
# C_PTZ = [-0.572777808, 0.00057140534]  # 点C的PTZ参数 - 用于求解
# D_PTZ = [-0.263888896, -0.614666581]  # 点D的PTZ参数 - 用于验证
# E_PTZ = [0.314444423, 0.107428558]  # 点E的PTZ参数 - 用于求解
# F_PTZ = [0.597777784, -0.416571409]  # 点F的PTZ参数 - 用于验证
# G_PTZ = [0.201666668, 0.124380969]  # 点G的PTZ参数 - 用于求解
# H_PTZ = [0.144444451, 0.14171429]  # 点H的PTZ参数 - 用于验证 可能不准
#
# camera_location = [23151, 98415, 15474]   #3.50
# ##########################################################################




# ==================== 核心函数定义 ====================

def ptz_to_angles(ptz_pan, ptz_tilt):
    """将 PTZ 值映射到角度（度）

    参数:
        ptz_pan: pan参数，范围-1到1 -> pan角度: 0..360 (线性映射)
        ptz_tilt: tilt参数，范围-1到1 -> tilt角度: 90..-15 (线性映射)

    返回:
        tuple: (pan_angle, tilt_angle) - pan和tilt角度（度）
    """
    # 将pan参数映射到0-360度范围
    pan_angle = (ptz_pan + 1.0) / 2.0 * 360.0
    pan_angle = pan_angle % 360.0  # 确保角度在0-360范围内

    # 将tilt参数映射到-15到90度范围
    tilt_angle = 90.0 - (ptz_tilt + 1.0) / 2.0 * (90.0 - (-15.0))
    return pan_angle, tilt_angle


def pan_tilt_to_direction(pan_deg, tilt_deg):
    """将 pan/tilt (度) 转换为相机坐标系中的单位方向向量 d。

    采用约定：
    - pan: 从 +X 逆时针到 +Y 的角度
    - tilt: 仰角（0 为水平，+90 为正上方）

    方向向量计算公式：
    d = [cos(tilt)*cos(pan), cos(tilt)*sin(pan), sin(tilt)]

    参数:
        pan_deg: pan角度（度）
        tilt_deg: tilt角度（度）

    返回:
        np.ndarray: 归一化的3D方向向量，形状 (3,)
    """
    # 将角度转换为弧度
    p = radians(pan_deg)
    t = radians(tilt_deg)

    # 计算方向向量的分量
    x = cos(t) * cos(p)  # x分量
    y = cos(t) * sin(p)  # y分量
    z = sin(t)  # z分量

    v = np.array([x, y, z], dtype=float)
    n = np.linalg.norm(v)
    if n == 0:
        return v  # 零向量特殊情况
    return v / n  # 返回单位向量


def kabsch_solve(U_pts, D_pts):
    """用 Kabsch 方法求解最优正交矩阵 R，使得 R * U ≈ D。

    算法原理：
    1. 计算互相关矩阵 H = U * D^T
    2. 对H进行SVD分解：H = U_s * S * Vt
    3. 计算旋转矩阵：R = Vt^T * U_s^T
    4. 确保行列式为+1（右手坐标系）

    参数:
        U_pts: 源点集，形状 (N,3)，表示对应的单位向量
        D_pts: 目标点集，形状 (N,3)，表示对应的单位向量

    返回:
        np.ndarray: 最优旋转矩阵 R，形状 (3,3)

    注意:
        确保U_pts和D_pts都是单位向量，且点数相同
    """
    assert U_pts.shape == D_pts.shape and U_pts.shape[1] == 3, \
        "输入矩阵形状必须相同且第二维为3"

    # 转置为 3xN 矩阵，便于矩阵运算
    U = U_pts.T  # 源点矩阵 (3,N)
    D = D_pts.T  # 目标点矩阵 (3,N)

    # 计算互相关矩阵
    H = U @ D.T  # 形状 (3,3)

    # 对H矩阵进行SVD分解
    U_s, S, Vt = np.linalg.svd(H)

    # 计算初始旋转矩阵
    R = Vt.T @ U_s.T

    # 确保是 proper rotation（行列式 = +1）
    if np.linalg.det(R) < 0:
        # 如果行列式为负，翻转最后一个奇异向量的符号
        Vt[2, :] *= -1
        R = Vt.T @ U_s.T

    return R


def compute_rt(world_pts, ptz_vals, camera_loc):
    """主计算流程：根据世界坐标点和PTZ值计算相机外参

    算法步骤：
    1. 根据PTZ值计算每个点的理论方向向量
    2. 计算世界点到相机的方向向量
    3. 使用Kabsch算法求解最优旋转矩阵
    4. 计算平移向量
    5. 计算每个点的角度残差

    参数:
        world_pts: 世界坐标点，形状 (N,3)
        ptz_vals: PTZ参数，形状 (N,2)，每行是 (ptz_pan, ptz_tilt)
        camera_loc: 相机位置，形状 (3,)

    返回:
        tuple: (R, t, residuals)
            R: 旋转矩阵，形状 (3,3) - 世界坐标系到相机坐标系
            t: 平移向量，形状 (3,) - 使得 x_cam = R*P + t
            residuals: 残差角度列表，每个点的角度误差（度）

    异常:
        ValueError: 如果相机位置与某个世界点重合
    """
    # 转换为numpy数组并确保数据类型
    world_pts = np.asarray(world_pts, dtype=float)
    ptz_vals = np.asarray(ptz_vals, dtype=float)
    camera_loc = np.asarray(camera_loc, dtype=float)

    # 步骤1：由 PTZ 生成方向向量 d_i
    d_list = []
    for p in ptz_vals:
        pan, tilt = ptz_to_angles(p[0], p[1])  # 转换为角度
        d = pan_tilt_to_direction(pan, tilt)  # 计算方向向量

        d_list.append(d)
    D = np.vstack(d_list)  # 合并为 N x 3 矩阵

    # 步骤2：计算世界点到相机的方向向量 u_i = (P - C)/||P - C||
    u_list = []
    for P in world_pts:
        v = P - camera_loc  # 从相机到点的向量
        n = np.linalg.norm(v)
        if n == 0:
            raise ValueError("相机位置与某个世界点重合，无法计算方向")
        u_list.append(v / n)  # 单位化
    U = np.vstack(u_list)  # 合并为 N x 3 矩阵

    # 步骤3：使用Kabsch算法求解最优旋转矩阵 R
    R = kabsch_solve(U, D)

    # 步骤4：计算平移向量 t = -R * C
    # 这样使得 x_cam = R*P + t 满足相机坐标系定义
    t = -R @ camera_loc

    # 步骤5：计算每个点的角度残差（度）作为评估
    residuals = []
    for i in range(U.shape[0]):
        # U[i]是世界坐标系中从相机到点的方向向量
        # R @ U[i]将其转换到相机坐标系
        predicted_dir_cam = R @ U[i]
        predicted_dir_cam = predicted_dir_cam / np.linalg.norm(predicted_dir_cam)  # 单位化

        # D[i]是根据PTZ值计算的理论方向向量（已在相机坐标系中）
        measured_dir_cam = D[i] / np.linalg.norm(D[i])

        # 计算预测方向与测量方向之间的角度误差
        cosang = np.clip(np.dot(predicted_dir_cam, measured_dir_cam), -1.0, 1.0)
        ang = degrees(acos(cosang))  # 转换为角度
        residuals.append(float(ang))

    return R, t, residuals


def verify_points(R, t, world_pts, ptz_vals, camera_loc):
    """验证已求解的R,t在验证点上的精度

    参数:
        R: 已求解的旋转矩阵
        t: 已求解的平移向量
        world_pts: 验证点世界坐标，形状 (N,3)
        ptz_vals: 验证点PTZ参数，形状 (N,2)
        camera_loc: 相机位置，形状 (3,)

    返回:
        list: 每个验证点的角度残差（度）
    """
    # 计算验证点的理论方向向量（基于PTZ值，在相机坐标系中）
    measured_dir_list = []
    for p in ptz_vals:
        pan, tilt = ptz_to_angles(p[0], p[1])
        d = pan_tilt_to_direction(pan, tilt)
        measured_dir_list.append(d)
    measured_dirs_cam = np.vstack(measured_dir_list)

    # 计算验证点的世界到相机方向向量（在世界坐标系中）
    world_dir_list = []
    for P in world_pts:
        v = P - camera_loc  # 从相机到点的向量
        n = np.linalg.norm(v)
        if n == 0:
            raise ValueError("相机位置与验证点重合")
        world_dir_list.append(v / n)  # 单位化
    world_dirs = np.vstack(world_dir_list)

    # 计算每个验证点的角度残差
    residuals = []
    for i in range(world_dirs.shape[0]):
        # 使用已求解的R将世界方向向量转换到相机坐标系
        predicted_dir_cam = R @ world_dirs[i]
        predicted_dir_cam = predicted_dir_cam / np.linalg.norm(predicted_dir_cam)

        # 理论方向向量（已在相机坐标系中）
        measured_dir_cam = measured_dirs_cam[i] / np.linalg.norm(measured_dirs_cam[i])

        # 计算预测方向与测量方向之间的角度误差
        cosang = np.clip(np.dot(predicted_dir_cam, measured_dir_cam), -1.0, 1.0)
        ang = degrees(acos(cosang))
        residuals.append(float(ang))

    return residuals


def compute_ptz_from_point(R, t, world_point, camera_loc):
    """根据已知的R,t和三维点坐标，计算对应的PTZ参数

    这是compute_rt的逆过程：已知相机外参和三维点，求PTZ值。
    可用于验证已标定的相机参数是否正确。

    算法步骤：
    1. 计算世界点到相机的方向向量（世界坐标系）
    2. 使用R将方向向量转换到相机坐标系
    3. 根据相机坐标系中的方向向量计算pan/tilt角度
    4. 将角度转换为PTZ参数

    参数:
        R: 旋转矩阵，形状 (3,3) - 世界坐标系到相机坐标系
        t: 平移向量，形状 (3,) - 使得 x_cam = R*P + t
        world_point: 三维点坐标，形状 (3,) - 世界坐标系中的点
        camera_loc: 相机位置，形状 (3,) - 世界坐标系中的位置

    返回:
        tuple: (ptz_pan, ptz_tilt) - 计算得到的PTZ参数

    异常:
        ValueError: 如果点与相机位置重合
    """
    # 转换为numpy数组
    world_point = np.asarray(world_point, dtype=float)
    camera_loc = np.asarray(camera_loc, dtype=float)

    # 步骤1：计算从相机到点的方向向量（世界坐标系）
    vec_cam_to_point = world_point - camera_loc
    norm = np.linalg.norm(vec_cam_to_point)
    if norm == 0:
        raise ValueError("点与相机位置重合，无法计算方向")

    # 单位化方向向量
    direction_world = vec_cam_to_point / norm

    # 步骤2：使用旋转矩阵将方向向量转换到相机坐标系
    direction_camera = R @ direction_world

    # 单位化（确保数值稳定性）
    direction_camera = direction_camera / np.linalg.norm(direction_camera)

    # 步骤3：根据相机坐标系中的方向向量计算pan和tilt角度
    dx, dy, dz = direction_camera

    # 计算pan角度（水平角度）
    # pan = atan2(dy, dx)，范围 -180° 到 180°
    pan_rad = np.arctan2(dy, dx)
    pan_deg = np.degrees(pan_rad)

    # 确保pan角度在0-360°范围内
    if pan_deg < 0:
        pan_deg += 360.0

    # 计算tilt角度（垂直角度）
    # tilt = asin(dz)，范围 -90° 到 90°
    # 限制dz在[-1,1]范围内，避免数值误差
    dz_clipped = np.clip(dz, -1.0, 1.0)
    tilt_rad = np.arcsin(dz_clipped)
    tilt_deg = np.degrees(tilt_rad)

    # 步骤4：将角度转换为PTZ参数
    # pan: 0-360° -> -1到1
    ptz_pan = (pan_deg / 360.0) * 2.0 - 1.0

    # tilt: -15-90° -> -1到1
    # 注意：PTZ的tilt参数映射是反向的
    # PTZ=-1 对应 tilt=90°（向上）
    # PTZ=1 对应 tilt=-15°（向下）
    ptz_tilt = -((tilt_deg + 15.0) / (90.0 + 15.0) * 2.0 - 1.0)

    return ptz_pan, ptz_tilt


def verify_rt_accuracy(R, t, world_pts, true_ptz_vals, camera_loc):
    """综合验证R,t的精度：计算PTZ并与真实值比较

    参数:
        R: 旋转矩阵
        t: 平移向量
        world_pts: 世界坐标点列表，形状 (N,3)
        true_ptz_vals: 真实的PTZ参数，形状 (N,2)
        camera_loc: 相机位置

    返回:
        dict: 验证结果，包含计算PTZ、误差分析等
    """
    world_pts = np.asarray(world_pts, dtype=float)
    true_ptz_vals = np.asarray(true_ptz_vals, dtype=float)

    computed_ptz_list = []
    ptz_errors = []

    for i, (world_point, true_ptz) in enumerate(zip(world_pts, true_ptz_vals)):
        # 计算PTZ
        computed_ptz = compute_ptz_from_point(R, t, world_point, camera_loc)
        computed_ptz_list.append(computed_ptz)

        # 计算PTZ误差
        pan_error = computed_ptz[0] - true_ptz[0]
        tilt_error = computed_ptz[1] - true_ptz[1]
        ptz_errors.append([pan_error, tilt_error])

    computed_ptz_vals = np.array(computed_ptz_list)
    ptz_errors = np.array(ptz_errors)

    # 计算统计信息
    result = {
        'computed_ptz': computed_ptz_vals.tolist(),
        'true_ptz': true_ptz_vals.tolist(),
        'ptz_errors': ptz_errors.tolist(),
        'pan_error_mean': np.mean(np.abs(ptz_errors[:, 0])),
        'pan_error_std': np.std(ptz_errors[:, 0]),
        'tilt_error_mean': np.mean(np.abs(ptz_errors[:, 1])),
        'tilt_error_std': np.std(ptz_errors[:, 1]),
        'ptz_error_mean': np.mean(np.abs(ptz_errors)),
        'ptz_error_max': np.max(np.abs(ptz_errors))
    }

    return result


# ==================== 脚本主函数 ====================

def main(out_json='./compute_rt_result.json'):
    """主函数：使用ACEG点求解，BDFH点验证，保存结果

    参数:
        out_json: 输出JSON文件路径，保存计算结果
    """
    print("=== 使用ACEG点求解相机外参 ===")

    # 准备求解数据：ACEG点（角点）
    solve_world_pts = np.vstack([A_3D, C_3D, E_3D, G_3D])  # 角点
    solve_ptz_vals = np.vstack([A_PTZ, C_PTZ, E_PTZ, G_PTZ])  # 对应PTZ
    cam = np.array(camera_location, dtype=float)

    # 使用ACEG点计算相机外参
    R, t, solve_residuals = compute_rt(solve_world_pts, solve_ptz_vals, cam)

    print(f"使用ACEG点({len(solve_world_pts)}个点)求解结果:")
    print("Rotation matrix R (world -> camera):")
    print(np.array(R))
    print("\nTranslation vector t (such that x_cam = R*P + t):")
    print(np.array(t))
    print(f"\nACEG点残差角度（度）: {solve_residuals}")
    print(f"ACEG点RMS误差: {np.sqrt(np.mean(np.array(solve_residuals) ** 2)):.4f}°")

    print("\n=== 使用BDFH点验证求解结果 ===")

    # 准备验证数据：BDFH点（边中点）
    verify_world_pts = np.vstack([B_3D, D_3D, F_3D, H_3D])  # 边中点
    verify_ptz_vals = np.vstack([B_PTZ, D_PTZ, F_PTZ, H_PTZ])  # 对应PTZ

    # 使用已求解的R,t验证BDFH点
    verify_residuals = verify_points(R, t, verify_world_pts, verify_ptz_vals, cam)

    print(f"使用BDFH点({len(verify_world_pts)}个点)验证结果:")
    print(f"BDFH点残差角度（度）: {verify_residuals}")
    print(f"BDFH点RMS误差: {np.sqrt(np.mean(np.array(verify_residuals) ** 2)):.4f}°")

    # 添加PTZ反向验证
    print("\n=== PTZ反向验证 ===")
    all_world_pts = [A_3D, B_3D, C_3D, D_3D, E_3D, F_3D, G_3D, H_3D]
    all_true_ptz = [A_PTZ, B_PTZ, C_PTZ, D_PTZ, E_PTZ, F_PTZ, G_PTZ, H_PTZ]
    all_names = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']

    print("点\t真实PTZ\t\t计算PTZ\t\tPan误差\t\tTilt误差")
    print("-" * 80)

    computed_ptz_list = []
    ptz_errors = []

    for name, world_pt, true_pz in zip(all_names, all_world_pts, all_true_ptz):
        computed_pz = compute_ptz_from_point(R, t, world_pt, cam)
        pan_err = computed_pz[0] - true_pz[0]
        tilt_err = computed_pz[1] - true_pz[1]

        computed_ptz_list.append(computed_pz)
        ptz_errors.append([abs(pan_err), abs(tilt_err)])

        print(
            f"{name}\t[{true_pz[0]:.6f}, {true_pz[1]:.6f}]\t[{computed_pz[0]:.6f}, {computed_pz[1]:.6f}]\t{pan_err:.6f}\t{tilt_err:.6f}")

    # 计算PTZ误差统计
    error_array = np.array(ptz_errors)
    print(f"\nPTZ误差统计:")
    print(f"Pan误差均值: {np.mean(error_array[:, 0]):.6f}")
    print(f"Pan误差标准差: {np.std(error_array[:, 0]):.6f}")
    print(f"Tilt误差均值: {np.mean(error_array[:, 1]):.6f}")
    print(f"Tilt误差标准差: {np.std(error_array[:, 1]):.6f}")
    print(f"总体PTZ误差均值: {np.mean(error_array):.6f}")
    print(f"最大PTZ误差: {np.max(error_array):.6f}")

    # 准备完整结果字典
    result = {
        'R': R.tolist(),  # 旋转矩阵（基于ACEG点求解）
        't': t.tolist(),  # 平移向量
        'solve_points': ['A', 'C', 'E', 'G'],  # 用于求解的点
        'solve_residuals_deg': solve_residuals,  # ACEG点残差
        'solve_rms_deg': float(np.sqrt(np.mean(np.array(solve_residuals) ** 2))),
        'verify_points': ['B', 'D', 'F', 'H'],  # 用于验证的点
        'verify_residuals_deg': verify_residuals,  # BDFH点残差
        'verify_rms_deg': float(np.sqrt(np.mean(np.array(verify_residuals) ** 2))),
        'all_points_residuals_deg': solve_residuals + verify_residuals,  # 所有点残差
        'overall_rms_deg': float(np.sqrt(np.mean(np.array(solve_residuals + verify_residuals) ** 2)))
    }

    # 添加PTZ反向验证结果
    result['ptz_verification'] = {
        'computed_ptz': computed_ptz_list,
        'true_ptz': all_true_ptz,
        'ptz_errors': ptz_errors,
        'pan_error_mean': float(np.mean(error_array[:, 0])),
        'pan_error_std': float(np.std(error_array[:, 0])),
        'tilt_error_mean': float(np.mean(error_array[:, 1])),
        'tilt_error_std': float(np.std(error_array[:, 1])),
        'ptz_error_mean': float(np.mean(error_array)),
        'ptz_error_max': float(np.max(error_array))
    }

    return result


if __name__ == '__main__':
    result = main()
    # 保存结果到JSON文件
    # with open('./compute_rt_result.json', 'w', encoding='utf-8') as f:
    #     json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"\n结果已保存到 compute_rt_result.json")
