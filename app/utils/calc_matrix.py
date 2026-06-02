import cv2
import numpy as np

# img = cv2.imread("static/1.jpg")
#
# height, width = img.shape[:2]
# print(height, width)
#
# world_0 = np.array([[1817, 88715, 0]], dtype=np.float32)
# world_1 = np.array([[1817, 98576, 0]], dtype=np.float32)
# world_2 = np.array([[19817, 98576, 0]], dtype=np.float32)
# world_3 = np.array([[19817, 88715, 0]], dtype=np.float32)
#
# # 要标注的点的坐标
# point_0 = np.array([[59, 162]], dtype=np.float32)
# point_1 = np.array([[392, 25]], dtype=np.float32)
# point_2 = np.array([[988, 313]], dtype=np.float32)
# point_3 = np.array([[595, 613]], dtype=np.float32)
#
# # 变换前的四个点
# dstArr = np.float32([[1817, 88715], [1817, 98576], [19817, 98576], [19817, 88715]])
# # 变换后的四个点
# srcArr = np.float32([[59 * 2, 162 * 2], [392 * 2, 25 * 2], [988 * 2, 313 * 2], [595 * 2, 613 * 2]])
#
# # 求解获取变换矩阵
# MM = cv2.getPerspectiveTransform(srcArr, dstArr)
# print(MM, type(MM))
# np.save('static/array.npy', MM)
# # 输出复原图像
# dst = cv2.warpPerspective(img, MM, (width, height))
# cv2.imwrite("static/A2.png", dst)


# 自定义坐标转换函数
def cvt_pos(u, v, mat):
    x = (mat[0][0] * u + mat[0][1] * v + mat[0][2]) / (mat[2][0] * u + mat[2][1] * v + mat[2][2])
    y = (mat[1][0] * u + mat[1][1] * v + mat[1][2]) / (mat[2][0] * u + mat[2][1] * v + mat[2][2])
    return (int(x), int(y))


# # 调用函数
# u, v = 475 * 2, 240 * 2
# x, y = cvt_pos(u, v, MM)
# print(x, y)
#
# load_arr = np.load('static/array.npy')
# print("load_arr: ", load_arr)
