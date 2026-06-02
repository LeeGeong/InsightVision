import json
import os
import ast
import cv2
import base64
import numpy as np
from sqlmodel import select
from fastapi import APIRouter, HTTPException
from log import logger
from app.api.deps import SessionDep
from app.models.device import Device
from app.utils.camera_onvif import Camera
from app.utils.scan import recognize_car_height
from app.core.deploy.python.test_infer_steel import init_detector
from app.utils.scan import recognize_center_point
from app.utils.calc_matrix import cvt_pos
from app.utils.scan import recognize_truck_area
from app.utils.scan import recognize_safe_area
from app.utils.scan import recognize_offset
from app.utils.scan import recoginize_plate_height_difference
from paddleocr import PaddleOCR, draw_ocr

################################初始化模型#################
# os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "timeout;3000"
router = APIRouter()
detector, FLAGS = init_detector()
ocr = PaddleOCR(use_angle_cls=True, lang="ch")

r"""
F:\20240801-DHHI-InsightCore\app\static\638610404557880366.3.scan_result_got.xyz
"""


@router.get("/steel_plate")
async def intelligence_steel_plate(session: SessionDep, ip: str = "192.168.1.64", file_path: str = "", Id: str = "",
                                   CmdNo: str = "", length: int = 0, width: int = 0, depth: int = 0):
    """
    钢板识别：金重钢板库使用
    Args:
        ip:传入相机ip
        file_path:点云数据存放路径
        Id: 扫描请求id
        CmdNo: 扫描请求命令number
        length: 钢板长度
        width:  钢板宽度
        depth:  钢板高度

    Returns:
            {
            "status": "success",
            "Id": 输入参数Id,
            "CmdNo": 输入参数CmdNo,
            "length": 输入参数length,
            "width": 输入参数width,
            "depth": 输入参数depth,
            "height": 根据点云信息计算出来的高度，无点云或报错为0,
            "result": {
                "center_1": 图像识别中心点,
                "center_2": 点云识别中心点,
                "box": 画框三维坐标,
                "box_native": 画框二维坐标,
                "safe_region": 安全区域坐标
            },
            "image_native_base64": "原始图片base64编码",
            "image_visualize_base64": "带识别信息的图片base64编码"
            }
    """
    account, password, ip = get_device_info(session, ip)
    return_dict = {
        "status": "success",
        "Id": Id,
        "CmdNo": CmdNo,
        "length": length,
        "width": width,
        "depth": depth,
        "height": 0.0,
        "result": {
            "center_1": [0, 0, 0],
            "center_2": [0, 0, 0],
            "box": [[0, 0], [0, 0], [0, 0], [0, 0]],
            "box_native": [[0, 0], [0, 0], [0, 0], [0, 0]],
            "safe_region": {
                "SafetyMaxX": 0.0,
                "SafetyMinX": 0.0,
                "SafetyMaxY": 0.0,
                "SafetyMinY": 0.0
            }
        },
        "image_native_base64": "",
        "image_visualize_base64": ""
    }
    height = 0
    if file_path:
        height = recognize_car_height.get_result(file_path)
        return_dict["height"] = height
        print("当前高度：", height)
    # rtsp = "rtsp://%s:%s@%s:554/Streaming/Channels/101" % (account, password, ip)
    # 获取当前ip的透射矩阵
    MM = solve_transformation_matrix(height, ip)
    rtsp = "rtsp://%s:%s@%s:554/LiveMedia/ch1/Media1/trackID=1" % (account, password, ip)
    # rtsp = 0
    cap = cv2.VideoCapture(rtsp, cv2.CAP_FFMPEG)
    if not cap.isOpened():
        logger.info("无法打开相机。")
        return_dict["status"] = "error"
        return return_dict
    # 获取一帧图像
    ret, frame = cap.read()
    # 关闭摄像头
    cap.release()
    if ret:
        img_list = [frame[:, :, ::-1]]
        perspective_warp_img = perspective_warp(frame, MM, ip)
        cv2.imwrite("static/steel_plate_perspective_warp.jpg", perspective_warp_img)
        cv2.imwrite("static/steel_plate_native.jpg", frame)
    else:
        logger.info("无法捕获图像。")
        return_dict["status"] = "error"
        return return_dict
    img_list_perspective_warp = ["static/steel_plate_perspective_warp.jpg"]
    img_list = ["static/steel_plate_native.jpg"]
    # img_list = ["static/638610404557880366.5.result1.jpg"]
    try:
        result = detector.predict_image(
            img_list,
            FLAGS.run_benchmark,
            repeats=100,
            visual=FLAGS.save_images,
            save_results=FLAGS.save_results)
        # print(result)
        # 计算透射变换矩阵
        # MM = solve_transformation_matrix(height, ip)
        coord_2d = calc_steel(result, img_list, MM)
        return_dict["result"]["center_1"] = [coord_2d[0], coord_2d[1], height]
        return_dict["result"]["center_2"] = [0, 0, 0]
        return_dict["result"]["box"] = coord_2d[2].tolist()
        return_dict["result"]["box_native"] = coord_2d[3][0].tolist()
        if file_path:
            coord_3d = recognize_center_point.recognize_center_point(file_path, coord_2d[2])
            if coord_3d["isSuccess"] == True:
                grab_point = coord_3d["grab_point"]
                return_dict["result"]["center_2"] = [grab_point[0], grab_point[1], grab_point[2]]
            return_dict["result"]["safe_region"] = recognize_safe_area.get_result(file_path, [coord_2d[0], coord_2d[1], height])["safe_area"]
    except Exception as e:
        print(e)
        return_dict['status'] = "error"
        with open(img_list[0], "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read())
            encoded_string = encoded_string.decode('utf-8')
            return_dict['image_native_base64'] = encoded_string
            return_dict['image_visualize_base64'] = encoded_string
        print(return_dict)
        return return_dict

    # re_data = predict_image_qr(d_qr, ["./ai/deploy/imgs/8.jpg"], f_qr, 1)
    # print(re_data)
    # return json.dumps(result['label'].tolist())
    with open(img_list[0], "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read())
        encoded_string = encoded_string.decode('utf-8')
        return_dict['image_native_base64'] = encoded_string
    path_list = img_list[0].split("/")
    # path_new = "output/" + path_list[-1]
    path_new = "output/annotated_image.png"
    with open(path_new, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read())
        encoded_string = encoded_string.decode('utf-8')
        return_dict['image_visualize_base64'] = encoded_string

    print(return_dict)
    return return_dict


@router.get("/barcode_ocr")
async def barcode_ocr(session: SessionDep, ip: str = "192.168.1.64"):
    """
    喷码识别：宝钢钢板库
    Args:
        ip: 传入相机IP

    Returns:
            {
            "status": "success",
            "result": [[[[[68,48],[1288,48],[1288,139],[68,139]],["2024年06月14日星期五09:21:36",0.9616556167602539]]]],
            "image_base64": "图片base64编码"
            }
    """
    if ip == "192.168.3.70":
        ip = "192.168.3.60"
    elif ip == "192.168.3.69":
        ip = "192.168.3.60"
    account, password, ip = get_device_info(session, ip)
    return_dict = {
        "status": "success",
        "result": {
            "Ocr_Manufactor": "",  # OCR钢板厂家
            "Ocr_BatchNo": "",  # OCR钢板批号
            "Ocr_Length": 0,  # OCR钢板规格
            "Ocr_Width": 0,  # OCR钢板规格
            "Ocr_Height": 0,  # OCR钢板规格
            "Ocr_Weight": 0,  # OCR钢板重量
            "Ocr_Code": ""  # OCR钢板编号
        },
        "image_base64": ""
    }

    # rtsp = "rtsp://%s:%s@%s:554/Streaming/Channels/101" % (account, password, ip)
    rtsp = "rtsp://%s:%s@%s:554/LiveMedia/ch1/Media1/trackID=1" % (account, password, ip)
    camera_ocr = Camera(ip, account, password, 0, 0)
    camera_ocr.connect_ONVIF()
    location = camera_ocr.get_camera_location()
    print("OCR相机当前位置：", location)
    camera_ocr.ptz_absolute_move(0.392722249, -0.416571409, 0.0772727281)
    # rtsp = 0
    cap = cv2.VideoCapture(rtsp)
    if not cap.isOpened():
        print("无法打开相机。")
        return_dict["status"] = "error"
        return return_dict
    # 获取一帧图像
    ret, frame = cap.read()
    # 关闭摄像头
    cap.release()
    if ret:
        cv2.imwrite("static/paddleocr.jpg", frame)
    else:
        print("无法捕获图像。")
        return_dict["status"] = "error"
        return return_dict
    img_path = "static/paddleocr.jpg"
    # img_path = 'static/20240614/ocr1.jpeg'
    result = ocr.ocr(img_path, cls=True)

    for idx in range(len(result)):
        res = result[idx]
        for line in res:
            print(line)

    # return_dict['result'] = result
    with open(img_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read())
        encoded_string = encoded_string.decode('utf-8')
        return_dict['image_base64'] = encoded_string

    # 显示结果
    from PIL import Image
    result = result[0]
    image = Image.open(img_path).convert('RGB')
    boxes = [line[0] for line in result]
    txts = [line[1][0] for line in result]
    scores = [line[1][1] for line in result]
    im_show = draw_ocr(image, boxes, txts, scores, font_path='./fonts/simfang.ttf')
    im_show = Image.fromarray(im_show)
    im_show.save('static/result.jpg')
    return return_dict


@router.get("/camera_image")
async def camera_image(session: SessionDep, ip: str = "192.168.1.64"):
    account, password, ip = get_device_info(session, ip)
    return_dict = {
        "status": "success",
        "image_base64": ""
    }
    # rtsp = "rtsp://%s:%s@%s:554/Streaming/Channels/101" % (account, password, ip)
    rtsp = "rtsp://%s:%s@%s:554/LiveMedia/ch1/Media1/trackID=1" % (account, password, ip)
    # rtsp = 0
    cap = cv2.VideoCapture(rtsp)
    if not cap.isOpened():
        print("无法打开相机。")
        return_dict["status"] = "error"
        return return_dict
    # 获取一帧图像
    ret, frame = cap.read()
    # 关闭摄像头
    cap.release()
    if ret:
        cv2.imwrite("static/baogangsteel.jpg", frame)
        encoded_string = base64.b64encode(frame)
        encoded_string = encoded_string.decode('utf-8')
        return_dict['image_base64'] = encoded_string
    else:
        print("无法捕获图像。")
        return_dict["status"] = "error"
        return return_dict
    return return_dict


@router.get("/point_cloud_processing")
async def point_cloud_processing(session: SessionDep, points: str = "[[1,2],[3,4],[4,5],[5,6]]", height: int = 0, ip="192.168.1.64"):
    """
    三维点列表 计算 中心点
    """
    return_dict = {
        "status": "success",
        "result": ""
    }
    box = ast.literal_eval(points)
    # 求解获取变换矩阵
    MM = solve_transformation_matrix(height, ip)
    box[0] = cvt_pos(box[0][0], box[0][1], MM)
    box[1] = cvt_pos(box[1][0], box[1][1], MM)
    box[2] = cvt_pos(box[2][0], box[2][1], MM)
    box[3] = cvt_pos(box[3][0], box[3][1], MM)

    return_dict["result"] = {
        "center_1": [int((box[0][0] + box[1][0] + box[2][0] + box[3][0]) / 4),
                     int((box[0][1] + box[1][1] + box[2][1] + box[3][1]) / 4), 0],
        "center_2": [0, 0],
        "box": box
    }
    print(return_dict)
    return return_dict


@router.get("/safe_region")
async def safe_region(session: SessionDep, file_path: str = "", points: str = "[23.2, 90.14, 1.97]"):
    point_info = eval(points)
    res = recognize_safe_area.get_result(file_path, point_info)
    return res


@router.get("/truck_area")
async def truck_area(session: SessionDep, file_path: str = ""):
    res = recognize_truck_area.get_result(file_path)
    return res


@router.get("/offset")
async def steel_plate_offset(session: SessionDep, file_path: str = "", equipment_number: str = "", length: int = 0, width: int = 0):
    res = recognize_offset.recoginize_center(file_path, equipment_number, length, width)
    return res

@router.get("/height_difference")
async def plate_height_difference(session: SessionDep, file_path: str = "", angle_points: str = "[[29573, 416296], [28957, 418269], [36490, 418240], [37145, 416207]]"):
    angel_points_info = eval(angle_points)
    res = recoginize_plate_height_difference.get_result(file_path, angel_points_info)
    return res


# 获取设备信息
def get_device_info(session: SessionDep, ip=None, device_name=None):
    if ip:
        statement = select(Device).where(Device.ip == ip)
    if device_name:
        statement = select(Device).where(Device.name == device_name)
    result = session.exec(statement).all()
    # result 一直有值，没法判断查询为空
    if not result:
        raise HTTPException(status_code=404, detail="device not found")
    account = result[0].account
    password = result[0].password
    ip = result[0].ip
    return account, password, ip


def calc_steel(result, img_list, MM):
    img = cv2.imread(img_list[0])
    boxes_num = result['boxes_num'][0]
    for i in range(0, boxes_num - 1):
        if result['score'][i] > 0.45:
            if result['label'][i] == 0:
                contours, _ = cv2.findContours(result['segm'][i], cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                # 按照面积进行排序，面积最大的轮廓排在前面
                # sorted_contours = sorted(contours, key=cv2.contourArea, reverse=True)
                # # 选择面积最大的轮廓
                # largest_contour = sorted_contours[0]
                # # 打印最大的轮廓的面积
                # print("Largest contour area:", cv2.contourArea(largest_contour))
                # filtered_contours = largest_contour
                filtered_contours = [cnt for cnt in contours if cv2.contourArea(cnt) >= 6000]
                if filtered_contours:
                    contours = filtered_contours
                else:
                    continue
                #############################################################
                rect = cv2.minAreaRect(contours[0])
                boxes = cv2.boxPoints(rect)
                ##############################################################
                cv2.drawContours(img, contours, -1, (0, 255, 0), 3)
                ##############################################################
                # 转换成点集
                contour_points = contours[0].astype(np.float32)
                # 应用透视变换
                transformed_contour = cv2.perspectiveTransform(contour_points, MM)
                rect = cv2.minAreaRect(transformed_contour)
                boxes = cv2.boxPoints(rect)
                box = np.int0(boxes)
                M = cv2.moments(transformed_contour)
                cx = int(M['m10'] / M['m00'])
                cy = int(M['m01'] / M['m00'])
                # 计算逆变换矩阵
                MM_inv = np.linalg.inv(MM)
                # 这是你想要变换回原空间的点(x, y)
                point_transformed = np.array([cx, cy, 1])
                # 应用逆变换
                point_original = np.dot(MM_inv, point_transformed)
                # 注意这里需要将坐标转换成齐次坐标形式
                homogeneous_points = np.hstack((box, np.ones((4, 1))))
                unwarped_points = np.dot(MM_inv, homogeneous_points.T).T
                unwarped_points = unwarped_points[:, :2] / unwarped_points[:, 2:]
                print("Unwarped points:", unwarped_points)
                contourss = [np.array(unwarped_points, dtype=np.int32)]
                cv2.drawContours(img, contourss, -1, (0, 255, 0), 10)
                # 转换为原空间中的坐标
                point_original = point_original / point_original[2]
                # 输出原空间中的坐标
                print(point_original[:2])
                cx_o = int(point_original[0])
                cy_o = int(point_original[1])
                # 在图像上绘制质心
                cv2.circle(img, (cx_o, cy_o), 5, (225, 225, 225), -1)
                ##############################################################
                dst = cv2.warpPerspective(img, MM, (30000, 100000))
                cv2.drawContours(dst, [box], -1, (0, 255, 0), 2)
                dst = cv2.resize(dst, (3000, 10000))
                cv2.imwrite("output/resize.png", dst)
                ###############################################################
                # 保存图像
                output_filename = "output/annotated_image.png"
                cv2.imwrite(output_filename, img)
                print(f"Image saved as {output_filename}")
                return (cx, cy, box, contourss)


# 图像透射变换
def perspective_warp(scr, M, ip):
    """
    destination:目标dst
    source：源数据src
    """
    if ip == "192.168.3.70":
        dst = cv2.warpPerspective(scr, M, (3000, 50000))
        dst = dst[40700:42370, 600:2600]
        (width, height) = (600, 40700)
    cv2.imwrite("output/resize.png", dst)
    return dst, (width, height)


# 坐标转换
def coordinate_transformation(coord_2d, MM):
    cx = coord_2d[0]
    cy = coord_2d[1]
    box = coord_2d[2]
    x, y = cvt_pos(cx, cy, MM)
    box[0] = cvt_pos(box[0][0], box[0][1], MM)
    box[1] = cvt_pos(box[1][0], box[1][1], MM)
    box[2] = cvt_pos(box[2][0], box[2][1], MM)
    box[3] = cvt_pos(box[3][0], box[3][1], MM)
    return x, y, box


# 计算透射变换矩阵
def solve_transformation_matrix(height, ip="0"):
    if ip == "0" or ip == "192.168.1.64":
        if height > 1700:
            dstArr = np.float32([[25893, 85410], [25626, 93528], [15880, 94325], [15770, 85694]])
            srcArr = np.float32([[398, 740], [1562, 986], [1764, 304], [1004, 218]])
        elif 1200 < height <= 1700:
            dstArr = np.float32([[25893, 85410], [25626, 93528], [15880, 94325], [15770, 85694]])
            srcArr = np.float32([[430, 810], [1548, 1058], [1758, 352], [1014, 264]])
        elif 700 < height <= 1200:
            dstArr = np.float32([[25893, 85410], [25626, 93528], [15880, 94325], [15770, 85694]])
            srcArr = np.float32([[448, 842], [1540, 1102], [1754, 394], [1012, 294]])
        elif 0 <= height <= 700:
            dstArr = np.float32([[25893, 85410], [25626, 93528], [15880, 94325], [15770, 85694]])
            srcArr = np.float32([[488, 928], [1528, 1192], [1744, 468], [1018, 364]])
    elif ip == "192.168.3.69":  # TCP11
        dstArr = np.float32([[25440, 51200], [25444, 54890], [43560, 54890], [43560, 51200]])
        srcArr = np.float32([[3333, 211], [3560, 942], [251, 1550], [230, 711]])
    elif ip == "192.168.3.70":  # TCP9
        # dstArr = np.float32([[21222, 414733], [6258, 415368], [6364, 419709], [21250, 419131]])
        # srcArr = np.float32([[535, 303], [3725, 983], [3784, 1926], [40, 1130]])
        # 钢板四角
        # dstArr = np.float32([[19499, 414553], [7207, 414782], [7376, 419395], [19653, 418967]])
        # srcArr = np.float32([[1083, 265], [3679, 882], [3600, 1900], [598, 1061]])
        dstArr = np.float32([[7150, 419476], [7080, 413844], [22335, 413770], [21454, 419090]])
        if height >= 2900:
            srcArr = np.float32([[3662, 1900], [3714, 694], [527, 5], [151, 951]])
        elif 2900 > height >= 2800:
            srcArr = np.float32([[3648, 1907], [3704, 708], [533, 20], [163, 964]])
        elif 2800 > height >= 2700:
            srcArr = np.float32([[3634, 1914], [3693, 721], [540, 35], [174, 976]])
        elif 2700 > height >= 2600:
            srcArr = np.float32([[3620, 1923], [3684, 734], [547, 52], [186, 989]])
        elif 2600 > height >= 2500:
            srcArr = np.float32([[3607, 1930], [3672, 747], [554, 68], [197, 1002]])
        elif 2500 > height >= 2400:
            srcArr = np.float32([[3595, 1936], [3663, 760], [562, 85], [209, 1014]])
        elif 2400 > height >= 2300:
            srcArr = np.float32([[3580, 1944], [3652, 773], [569, 100], [220, 1026]])
        elif 2300 > height >= 2200:
            srcArr = np.float32([[3568, 1950], [3641, 784], [576, 115], [231, 1038]])
        elif 2200 > height >= 2100:
            srcArr = np.float32([[3555, 1958], [3631, 797], [582, 130], [242, 1050]])
        elif 2100 > height:
            srcArr = np.float32([[3555, 1958], [3631, 797], [582, 130], [242, 1050]])
    MM = cv2.getPerspectiveTransform(srcArr, dstArr)
    return MM


if __name__ == "__main__":
    intelligence_steel_plate("192.168.1.0")
