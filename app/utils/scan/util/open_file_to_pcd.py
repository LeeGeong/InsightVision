'''
导入点云文件，转换成pcd
'''
import numpy as np


def file_to_pcd_np(file_path: str) -> np.ndarray:
    pcd_np = np.loadtxt(file_path, delimiter=",")[:, 0:3]

    return pcd_np


def get_pcd_np_from_file(file_path: str) -> tuple:
    '''
    :return: (文件加载成功或失败，numpy类型的点云，失败消息)
    '''
    try:
        pcd_np = np.loadtxt(file_path, delimiter=",")[:, 0:3]
        return True, pcd_np, "加载成功"
    except IndexError:
        return False, None, "点云文件为空"
    except:
        return False, None, "加载文件失败"


def get_pcd_craneZ_np_from_file(file_path: str) -> tuple:
    '''
    :return: (文件加载成功或失败，numpy类型的点云，失败消息) 加上了起重机z信息
    '''
    try:
        pcd_np = np.loadtxt(file_path, delimiter=",")[:, 0:5]
        return True, pcd_np, "加载成功"
    except IndexError:
        return False, None, "点云文件为空"
    except:
        return False, None, "加载文件失败"


# def file_to_pcd(file_path:str) -> o3d.geometry.PointCloud:
#     pcd_np = np.loadtxt(file_path, delimiter=",")
#     pcd = o3d.geometry.PointCloud()
#     pcd.points = o3d.utility.Vector3dVector(pcd_np)
#
#     return pcd

if __name__ == '__main__':
    pcd_path = r"D:\项目\BaoGang_ScanAlgorithm\Data2\C12_2025_2_26_13_56_23_638761749831086107-section.xyz"
    res = get_pcd_np_from_file(pcd_path)
    print(res)
