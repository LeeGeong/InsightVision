import cv2
import numpy as np
from app.utils.image_save import save_image


def sort_corners_clockwise(corners):
    """
    将四个点按左上→右上→右下→左下排序
    
    Args:
        corners: 四个角点坐标，格式为4x2的数组
        
    Returns:
        numpy.ndarray: 排序后的四个角点坐标
    """
    center = np.mean(corners, axis=0)

    sorted_idx = np.argsort([np.arctan2(p[1] - center[1], p[0] - center[0]) for p in corners])[::-1]
    sorted_corners = corners[sorted_idx]

    top_two = sorted(sorted_corners[:2], key=lambda p: p[0])
    bottom_two = sorted(sorted_corners[2:], key=lambda p: -p[0])
    return np.vstack([top_two, bottom_two])


def perspective_warp(scr, M, ip):
    """
    图像透射变换
    
    Args:
        scr (numpy.ndarray): 源图像
        M (numpy.ndarray): 变换矩阵
        ip (str): 设备IP地址，用于确定输出尺寸
        
    Returns:
        tuple: (dst, width, height)
            - dst (numpy.ndarray): 变换后的图像
            - width (int): 图像宽度
            - height (int): 图像高度
    """
    if ip == "192.168.3.70":
        dst = cv2.warpPerspective(scr, M, (3000, 50000))
        dst = dst[40700:42370, 500:2600]
        (width, height) = (500, 40700)
    elif ip == "192.168.3.69":
        dst = cv2.warpPerspective(scr, M, (3000, 50000))
        dst = dst[40700:42800, 600:2600]
        (width, height) = (600, 40700)
    elif ip == "192.168.3.71":
        dst = cv2.warpPerspective(scr, M, (4500, 50000))
        dst = dst[42000:43000, 2500:4500]
        (width, height) = (2500, 42000)
    elif ip == "192.168.3.72":
        dst = cv2.warpPerspective(scr, M, (4500, 50000))
        dst = dst[41000:42000, 2600:4300]
        (width, height) = (2600, 41000)
    save_image("static/steel_output/resize.png", dst)
    return dst, width, height
