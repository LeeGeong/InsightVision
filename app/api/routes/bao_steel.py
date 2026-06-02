import base64
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

import cv2
import numpy as np
import pandas as pd
from fastapi import APIRouter, Body
from ultralytics import YOLO

from app.api.deps import SessionDep
from app.core.config.settings import settings
from app.core.deploy.python.test_infer_car import init_detector_car
from app.core.deploy.python.test_infer_steel import init_detector_steel
from app.core.func_calc import remove_duplicates, filtering_algorithm
from app.core.services.bao_steel_services import (
    perform_yolo_detection,
    map_lane_ip_and_ranges,
    validate_mat_infos,
    detect_corners,
    verify_batch_only,
    calc_steel,
    get_perspective_data
)
from app.core.services.ollama_service import get_ollama_spray_code, OLLAMA_AVAILABLE
from app.log import logger
from app.utils.camera_onvif_ln import Camera_ln
from app.utils.device_utils import camera_check, get_device_info
from app.utils.scan import (
    recoginize_plate_height_difference,
    recognize_align_and_crosser,
    recognize_car_height,
    recognize_center_point,
    recognize_empty_car,
    recognize_offset,
    recognize_safe_area,
    recognize_truck_area
)
from app.utils.yolo11_ocr_pre import OcrProcessor

# 设置 pandas 显示选项
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', None)

# 初始化路由
router = APIRouter()

# 初始化检测器
detector_steel, FLAGS_STEEL = init_detector_steel()
detector_car, FLAGS_CAR = init_detector_car()
# ocr = PaddleOCR(use_angle_cls=True, lang="ch")
processor = OcrProcessor(
    yolo_model_path="../models/yolo_model/best.pt",
    det_model_dir="../models/ocr_model/det_ch_PP-OCRv3_inference_0117/Student",
    rec_model_dir="../models/ocr_model/rec_en_PP-OCRv4_inference_0109",
    rec_char_dict_path="../models/ocr_model/en_dict.txt",
    output_dir="./static/ocr_results"
)

# 初始化 YOLO 模型
model = YOLO("../models/yolo_model/best.pt")

# 读取透视变换配置文件
config_path = Path(__file__).parent.parent.parent / "cache" / "perspective_config.json"
# print(config_path)
# 读取配置文件
# with open('cache/perspective_config.json', 'r') as f:
with open(config_path, 'r', encoding='utf-8') as f:
    perspective_config = json.load(f)


# 为了让代码更具可读性和维护性，可以添加函数文档字符串说明该路由的功能和参数等信息
@router.get("/steel_plate", summary="获取钢板相关信息", description="该接口用于获取钢板的相关信息，具体返回内容根据业务逻辑确定。")
async def intelligence_steel_plate(session: SessionDep, ip: str = "192.168.1.64", file_path: str = "", park_no: str = "", height :int = 0, classId:int =1, task_id: str = ""):
    """
    钢板识别：供宝钢钢板库使用

    Args:
        ip (str): 传入相机的 IP 地址
        file_path (str): 点云数据的存放路径
        task_id (str): 任务ID

    Returns:
        dict: 包含以下信息的字典
            - status (str): 操作状态，成功为 "success"
            - height (float): 根据点云信息计算得出的高度，若无点云数据或计算报错则为 0
            - result (dict): 包含识别结果的字典
                - center_1 (list): 图像识别得到的中心点坐标
                - center_2 (list): 点云识别得到的中心点坐标
                - box (list): 画框的三维坐标
                - box_native (list): 画框的二维坐标
                - safe_region (dict): 安全区域的坐标
                - angle1(float):上边缘角度
                - angle2(float):下边缘角度
            - image_native_base64 (str): 原始图片的 Base64 编码
            - image_visualize_base64 (str): 带有识别信息的图片的 Base64 编码
    """
    logger.info(f"接口请求: GET /steel_plate, 参数: ip={ip}, file_path={file_path}, park_no={park_no}, height={height}, classId={classId}, task_id={task_id}")
    start_time = time.time()
    account, password, ip = get_device_info(session, ip)
    return_dict = {
        "status": "success",
        "message": "",
        "result": {
            "center_1": [0, 0, 0],
            "center_2": [0, 0, 0],
            "box": [[0, 0], [0, 0], [0, 0], [0, 0]],
            "box_native": [[0, 0], [0, 0], [0, 0], [0, 0]],
            "width_height": [0, 0],
            "perspective_box": [[0, 0], [0, 0], [0, 0], [0, 0]],
            "perspective_box_native": [[0, 0], [0, 0], [0, 0], [0, 0]],
            "safe_region": {
                "SafetyMaxX": 0.0,
                "SafetyMinX": 0.0,
                "SafetyMaxY": 0.0,
                "SafetyMinY": 0.0
            },
            "angle1": 0.0,  # 新增上边缘角度
            "angle2": 0.0  # 新增下边缘角度
        },
        "image_native_base64": "",
        "image_visualize_base64": "",
        "time_usage": 0.0  # 初始化总耗时
    }
    # if file_path:
    #     height, align_z, crosser_z = recognize_car_height.get_result(file_path, park_no)
    #     return_dict["height"] = height
    #     return_dict["result"]["align_z"] = align_z
    #     return_dict["result"]["crosser_z"] = crosser_z
    #     print("当前高度：", height)
    #     print("当前align_z：", align_z)
    #     print("当前crosser_z：", crosser_z)
    # rtsp = "rtsp://%s:%s@%s:554/Streaming/Channels/101" % (account, password, ip)
    output_folder = "static/uploads/steel"
    os.makedirs(output_folder, exist_ok=True)

    # 生成基于时间戳的唯一文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    native_filename = os.path.join(output_folder, f"native_{timestamp}.jpg")
    warped_filename = os.path.join(output_folder, f"warped_{timestamp}.jpg")

    rtsp = "rtsp://%s:%s@%s:554/LiveMedia/ch1/Media1/trackID=1" % (account, password, ip)
    camera_status, camera_msg, camera_img = camera_check(rtsp)
    # camera_status = True
    # camera_img = cv2.imread("static/steel_plate_native.jpg")


    if camera_status:
        # 保存原始相机图片
        cv2.imwrite(native_filename, camera_img)
        # 获取当前ip的透射矩阵
        perspective_data, perspective_warp_img = get_perspective_data(session, ip, height, camera_img)
        if perspective_data is None:
            return_dict["message"] = "获取透射矩阵失败"
            return_dict["status"] = "error"
            return return_dict
        else:
            MM = perspective_data["transform_matrix"]
            perspective_box = perspective_data["10x_dstArr"].tolist()
            width_p = perspective_data["width"]
            height_p = perspective_data["height"]

        # perspective_warp_img, width_p, height_p = perspective_warp(camera_img, MM, ip)

        # cv2.imwrite("static/steel_plate_perspective_warp.jpg", perspective_warp_img)
        # 保存透射变换后的图片
        cv2.imwrite(warped_filename, perspective_warp_img)

    else:
        return_dict["message"] = camera_msg
        return_dict["status"] = "error"
        return return_dict

    # img_list_perspective_warp = ["static/steel_plate_perspective_warp.jpg"]
    # img_list_native = ["static/steel_plate_native.jpg"]
    # img_list = ["static/steel_plate_native.jpg"]
    # img_list = ["static/638610404557880366.5.result1.jpg"]
    # 更新返回的图片路径
    img_list_perspective_warp = [warped_filename]
    img_list_native = [native_filename]
    try:
        if classId ==1:
            result = detector_car.predict_image(
                img_list_perspective_warp,
                FLAGS_CAR.run_benchmark,
                repeats=100,
                visual=FLAGS_CAR.save_images,
                save_results=FLAGS_CAR.save_results)
        elif classId > 1:
            result = detector_steel.predict_image(
                img_list_perspective_warp,
                FLAGS_STEEL.run_benchmark,
                repeats=100,
                visual=FLAGS_STEEL.save_images,
                save_results=FLAGS_STEEL.save_results)
        # print(result)
        return_dict["result"]["width_height"] = [width_p, height_p]
        # 计算透射变换矩阵


        coord_2d = calc_steel(result, img_list_perspective_warp, width_p, height_p)
        if coord_2d[0] == 0:
            with open(img_list_perspective_warp[0], "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read())
                encoded_string = encoded_string.decode('utf-8')
                return_dict['image_native_base64'] = encoded_string
                return_dict['image_visualize_base64'] = encoded_string
            return return_dict
        return_dict["result"]["center_1"] = [coord_2d[0] - width_p, coord_2d[1] - height_p, height]
        return_dict["result"]["center_2"] = [0, 0, 0]
        return_dict["result"]["box"] = coord_2d[3]  # coord_2d[2]
        return_dict["result"]["box_native"] = coord_2d[2]
        return_dict["result"]["angle1"] = coord_2d[4]  # 上边缘角度
        return_dict["result"]["angle2"] = coord_2d[5]  # 下边缘角度
        annotated_filename = coord_2d[6]  # 获取可视化图路径
        # return_dict["result"]["perspective_box"] = perspective_box
        # perspective_box_native = [[x - width_p, y - height_p] for x, y in perspective_box]
        # return_dict["result"]["perspective_box_native"] = perspective_box_native


        if file_path:
            coord_3d = recognize_center_point.recognize_center_point(file_path, coord_2d[2])
            if coord_3d["isSuccess"] == True:
                grab_point = coord_3d["grab_point"]
                return_dict["result"]["center_2"] = [grab_point[0], grab_point[1], grab_point[2]]
            return_dict["result"]["safe_region"] = recognize_safe_area.get_result(file_path, [coord_2d[0], coord_2d[1], height])["safe_area"]
    except Exception as e:
        logger.error(e)
        return_dict['status'] = "error"
        with open(img_list_perspective_warp[0], "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read())
            encoded_string = encoded_string.decode('utf-8')
            return_dict['image_native_base64'] = encoded_string
            return_dict['image_visualize_base64'] = encoded_string
        p_return_dict = return_dict.copy()
        del p_return_dict["image_native_base64"]
        del p_return_dict["image_visualize_base64"]
        logger.info(p_return_dict)
        return return_dict


    with open(img_list_perspective_warp[0], "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read())
        encoded_string = encoded_string.decode('utf-8')
        return_dict['image_native_base64'] = encoded_string
    # path_new = "static/steel_output/annotated_image.png"
    with open(annotated_filename, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read())
        encoded_string = encoded_string.decode('utf-8')
        return_dict['image_visualize_base64'] = encoded_string


    p_return_dict = return_dict.copy()
    del p_return_dict["image_native_base64"]
    del p_return_dict["image_visualize_base64"]
    logger.info(p_return_dict)
    return_dict["time_usage"] = round(time.time() - start_time, 3)
    logger.info(f"总处理耗时: {return_dict['time_usage']}秒")

    return return_dict


@router.post("/barcode_ocr")
async def barcode_ocr_test(session: SessionDep, request_data: Dict[str, Any] = Body(...),request_mode:int =0,height:int =2300, task_id: str = ""):
    """
    喷码识别：宝钢钢板库
    Args:
        ip: 传入相机IP
        task_id: 任务ID

    Returns:
            {
            "status": "success",
            "result": [[[[[68,48],[1288,48],[1288,139],[68,139]],["2024年06月14日星期五09:21:36",0.9616556167602539]]]],
            "image_base64": "图片base64编码"
            }
    """
    logger.info(f"接口请求: POST /barcode_ocr, 参数: request_mode={request_mode}, height={height}, task_id={task_id}")
    logger.info(f"barcode_ocr_test 请求 body: {request_data}")
    import gc
    def _release(*vars_):
        """删除变量并触发垃圾回收"""
        for v in vars_:
            try:
                del v
            except Exception:
                pass
        gc.collect()
    # =======任务时间=========================================
    task_ts = time.time()  # float 秒
    task_dt = datetime.fromtimestamp(task_ts)
    task_time_str = task_dt.strftime("%Y%m%d_%H%M%S")
    # ========================================================
    #初始化时间统计
    time_stats = {
        "start_time": time.time(),
        "camera_setup": 0,        # 相机初始化时间
        "mat_info_check": 0,      # 物料校验时间
        "camera_shooting": 0,     # 相机拍摄时间
        "ocr_processing": 0,     # OCR处理总时间
        "corner_detection": 0,   # 角点检测时间
        "yolo_detection": 0,     # YOLO检测时间
        "camera_movement": 0,    # 相机移动时间
        "detail_processing": 0   # 细节处理时间
    }

    return_dict = {
        "status": "success",
        "results": [
            {
                "Ocr_Manufactor": "",  # OCR钢板厂家
                "Ocr_BatchNo": "",  # OCR钢板批号
                "Ocr_Length": 0,  # OCR钢板规格
                "Ocr_Width": 0,  # OCR钢板规格
                "Ocr_Height": 0,  # OCR钢板规格
                "Ocr_Weight": 0,  # OCR钢板重量
                "Ocr_Code": "",  # OCR钢板编号
                "Priority": 0,  # 优先级
                "status": "",
                "message": "",
                "image_base64_detail": ""
            }
        ],
        "image_base64_overview": "",
        "time_usage": {}
    }

    try:
        # 记录开始时间
        stage_start = time.time()
        ip = request_data["ip"]
        # IP → TCP 映射
        TCP_MAP = {
            "192.168.3.61": "TCP3", "192.168.3.62": "TCP1", "192.168.3.63": "TCP4", "192.168.3.64": "TCP2",
            "192.168.3.65": "TCP7", "192.168.3.66": "TCP5", "192.168.3.67": "TCP8", "192.168.3.68": "TCP6",
            "192.168.3.69": "TCP11", "192.168.3.70": "TCP9", "192.168.3.71": "TCP12", "192.168.3.72": "TCP10"
        }
        tcp_id = TCP_MAP.get(ip, "TCP_UNKNOWN")

        #初始化相机参数
        ip_ocr, location_ranges = map_lane_ip_and_ranges(ip)
        account, password, ip = get_device_info(session, ip)
        account_ocr, password_ocr, ip_ocr = get_device_info(session, ip_ocr)

        # account, password, ip = get_device_info(session, ip)
        # account, password, _ = get_device_info(session, ip)
        # rtsp = "rtsp://%s:%s@%s:554/Streaming/Channels/101" % (account, password, ip)
        # rtsp = "rtsp://%s:%s@%s:554/LiveMedia/ch1/Media1/trackID=1" % (account_ocr, password_ocr, ip_ocr)

        # 记录相机初始化耗时
        time_stats["camera_setup"] = time.time() - stage_start
        stage_start = time.time()

        # 校验核心字段存在性
        mat_infos_valid, mat_infos_df_or_msg = validate_mat_infos(request_data)
        if mat_infos_valid:
            mat_infos_df = mat_infos_df_or_msg
            # logger.info(f"物料信息验证通过: {mat_infos_df}")
        else:
            logger.info(mat_infos_df_or_msg)
        # 记录物料校验耗时
        time_stats["mat_info_check"] = time.time() - stage_start
        stage_start = time.time()


        # print(mat_infos_df)
        # 使用本地图片路径进行测试
        # img_path = r'D:\UGit\dhhi-insightcore\test\0438.jpg'  # 你可以将测试图放在这个路径
        camera_ocr = Camera_ln(ip_ocr, account_ocr, password_ocr, 0, 0)
        camera_ocr.connect_ONVIF()
        camera_ocr.get_camera_location()

        # if ip_ocr =='192.168.3.50':
        output_folder = "static/uploads/ocr"

        rtsp = "rtsp://%s:%s@%s:554/LiveMedia/ch1/Media1/trackID=1" % (account, password, ip)
        rtsp_ocr = "rtsp://%s:%s@%s:554/LiveMedia/ch1/Media1/trackID=1" % (account_ocr, password_ocr, ip_ocr)
        camera_status, camera_msg, camera_img = camera_check(rtsp)
        if camera_status:
            # 获取当前ip的透射矩阵
            # height =2300
            perspective_data, perspective_warp_img = get_perspective_data(session, ip, height, camera_img)
            if perspective_data is None:
                return_dict["message"] = "获取透射矩阵失败"
                return_dict["status"] = "error"
                _release(camera_img)
                return return_dict
            else:
                MM = perspective_data["transform_matrix"]
                width_p = perspective_data["width"]
                height_p = perspective_data["height"]

        else:
            return_dict["message"] = camera_msg
            return_dict["status"] = "error"
            return return_dict
        # 更新返回的图片路径
        image = perspective_warp_img.copy()
        image_width = image.shape[1]
        image_height = image.shape[0]
        # 选择区域 用于防止识别到旁边车位的钢板
        start_point = (0, 1000)  # 左上角坐标
        end_point = (2228, 1446)  # 右下角坐标
        color = (0, 0, 0)
        thickness = -1  # 填充整个区域
        cv2.rectangle(image, start_point, end_point, color, thickness)
        #  文件命名：任务时间 + TCP
        filename = f"{request_mode}_{task_time_str}_{tcp_id}.png"
        img_path_overview = os.path.join(output_folder, filename)
        image_overview = image.copy()
        if settings.DEBUG:
            cv2.imwrite(img_path_overview, image)
        time_stats["camera_shooting"] = time.time() - stage_start
        _release(camera_img, image)

        # 记录OCR开始时间
        ocr_start_time = time.time()
        if mat_infos_valid and mat_infos_df is not None:
            try:
                if request_mode==0:
                    image, corners = detect_corners(detector_steel, image, FLAGS_STEEL)
                    # return_dict["result"]["box"] = corners if corners else [[0, 0], [0, 0], [0, 0], [0, 0]]
                    time_stats["corner_detection"] = time.time() - stage_start
                    # 如果检测到钢板角点，继续处理
                    if corners and len(corners) == 4:
                        stage_start = time.time()
                        # 裁剪ROI区域进行检测
                        pts = np.array(corners, dtype=np.int32)
                        # 1. 创建精确的四边形掩膜
                        mask = np.zeros(image.shape[:2], dtype=np.uint8)
                        cv2.fillPoly(mask, [pts], color=255)
                        # 2. 提取四边形区域（非ROI区域为黑色）
                        roi = cv2.bitwise_and(image, image, mask=mask)
                        # 调试模式保存ROI图像
                        if settings.DEBUG:
                            img_path_roi = os.path.join(output_folder, f"{task_time_str}_{tcp_id}_ROI.jpg")
                            cv2.imwrite(img_path_roi, roi)

                        # 执行YOLO检测并返回结果
                        detections = perform_yolo_detection(roi,width_p, height_p,task_time_str, tcp_id)

                        # 如果没检测到则进行一次全图检测
                        if not detections:
                            detections = perform_yolo_detection(image,width_p, height_p,task_time_str, tcp_id)
                        _release(roi, image)

                        # 根据检测结果数量处理不同情况
                        if not detections:
                            logger.info("未检测到任何喷码")
                            return_dict["results"] = [
                                {
                                    "Ocr_Manufactor": "",  # OCR钢板厂家
                                    "Ocr_BatchNo": "",  # OCR钢板批号
                                    "Ocr_Length": 0,  # OCR钢板规格
                                    "Ocr_Width": 0,  # OCR钢板规格
                                    "Ocr_Height": 0,  # OCR钢板规格
                                    "Ocr_Weight": 0,  # OCR钢板重量
                                    "Ocr_Code": "",  # OCR钢板编号
                                    "Priority": 0,  # 优先级
                                    "status": "error",
                                    "message": "未检测到任何喷码",
                                    "image_base64_detail": ""
                                }
                            ]

                        else:
                            logger.info(f"检测到({len(detections)}个喷码)，进行处理")
                            # 按置信度从高到低排序
                            # detections.sort(key=lambda x: x["confidence"], reverse=True)
                            # 计算图像中心点
                            image_center_x = image_width / 2
                            image_center_y = image_height / 2
                            logger.info(f"图像尺寸: width={image_width},_height={image_height}, 图像中心=({image_center_x}, {image_center_y})")
                            # 按距离图像中心的距离排序
                            detections.sort(key=lambda x: ((x["center"][0] - image_center_x) ** 2 + (x["center"][1] - image_center_y) ** 2) ** 0.5)
                            print(detections)
                            logger.info(f"喷码排序结果: {[(i+1, d['center'], round(d['confidence'], 2)) for i, d in enumerate(detections)]}")
                            return_dict["results"] = []  # 初始化结果列表

                            for i, detection in enumerate(detections):
                                logger.info(f"正在处理第 {i + 1} 个喷码 (置信度: {detection['confidence']:.2f})")
                                camera_img = None  # 提前初始化，确保 finally 中可用
                                try:
                                    # 计算检测框的宽高
                                    w = detection["short_side"]
                                    h = detection["long_side"]
                                    # zoom_level = camera_ocr.calculate_zoom_level1(w, h)
                                    zoom_level = camera_ocr.calculate_zoom_level_JJH(detection, height)
                                    camera_ocr.move_to_xyz(pixel_x=detection["center"][0],
                                                               pixel_y=detection["center"][1], height=height,
                                                               zoom_level=zoom_level)
                                    time.sleep(6)  # 等待相机稳定
                                    time_stats["camera_movement"] += time.time() - stage_start
                                    stage_start = time.time()
                                    camera_status, camera_msg, camera_img = camera_check(rtsp_ocr)
                                    img_path_code = os.path.join(output_folder, f"{task_time_str}_{tcp_id}_{i}.jpg")
                                    if settings.DEBUG:
                                        cv2.imwrite(img_path_code, camera_img)
                                    time_stats["camera_shooting"] += time.time() - stage_start
                                    # 执行OCR识别
                                    stage_start = time.time()
                                    results = processor.process_image(camera_img)
                                    time_stats["detail_processing"] = time.time() - stage_start
                                    # 创建单个喷码的结果字典
                                    single_result = {
                                        "Ocr_Manufactor": "",
                                        "Ocr_BatchNo": "",
                                        "Ocr_Length": 0,
                                        "Ocr_Width": 0,
                                        "Ocr_Height": 0,
                                        "Ocr_Weight": 0,
                                        "Ocr_Code": "",
                                        "Priority": i,  # 优先级
                                        "box": detection["box_points"],
                                        "status": "success",
                                        "message": f"第 {i + 1} 个喷码识别成功",
                                        "image_base64_detail": ""
                                    }
                                    if results:
                                        # 将图片编码为 bytes，用于 Ollama 二次识别
                                        _, img_encoded = cv2.imencode('.jpg', camera_img)
                                        img_bytes = img_encoded.tobytes()
                                        
                                        # 验证批号和重量（内部会调用 Ollama 二次识别）
                                        verify_result = verify_batch_only(results, mat_infos_df, single_result, img_bytes)
                                    else:
                                        # OCR 未识别出结果，尝试使用 Ollama 进行二次识别
                                        logger.info(f"第 {i + 1} 个喷码 OCR 未识别出结果，尝试 Ollama 二次识别")
                                        
                                        if OLLAMA_AVAILABLE and mat_infos_valid:
                                            try:
                                                # 将图片编码为 bytes
                                                _, img_encoded = cv2.imencode('.jpg', camera_img)
                                                img_bytes = img_encoded.tobytes()
                                                
                                                # 获取有效的喷码列表
                                                valid_mat_nos = mat_infos_df['mat_no'].tolist()
                                                
                                                # 调用 Ollama 进行识别
                                                spray_code, in_list = get_ollama_spray_code(img_bytes, valid_mat_nos)
                                                
                                                if spray_code and in_list:
                                                    # Ollama 识别成功且在有效列表中
                                                    logger.info(f"Ollama 二次识别成功: {spray_code}")
                                                    single_result["Ocr_BatchNo"] = spray_code
                                                    single_result["status"] = "success"
                                                    single_result["message"] = f"第 {i + 1} 个喷码 Ollama 识别成功"
                                                elif spray_code and not in_list:
                                                    # 识别到喷码但不在有效列表中
                                                    logger.info(f"Ollama 识别到喷码 {spray_code} 但不在有效列表中")
                                                    single_result["Ocr_BatchNo"] = spray_code
                                                    single_result["status"] = "error"
                                                    single_result["message"] = f"第 {i + 1} 个喷码识别结果 {spray_code} 不在有效列表中"
                                                else:
                                                    logger.info(f"Ollama 二次识别也未找到有效喷码")
                                                    single_result["status"] = "error"
                                                    single_result["message"] = f"第 {i + 1} 个喷码未识别出结果（OCR 和 Ollama 均失败）"
                                            except Exception as ollama_e:
                                                logger.error(f"Ollama 二次识别异常: {str(ollama_e)}")
                                                single_result["status"] = "error"
                                                single_result["message"] = f"第 {i + 1} 个喷码未识别出结果（Ollama 异常）"
                                        else:
                                            if not OLLAMA_AVAILABLE:
                                                logger.warning("Ollama 不可用，跳过二次识别")
                                            if not mat_infos_valid:
                                                logger.warning("物料信息无效，跳过 Ollama 二次识别")
                                            single_result["status"] = "error"
                                            single_result["message"] = f"第 {i + 1} 个喷码未识别出结果"
                                except Exception as e:
                                    logger.error(f"处理喷码第 {i + 1} 个发生错误: {str(e)}")
                                    single_result = {
                                        "box": detection.get("box_points", []),
                                        "status": "error",
                                        "message": f"第 {i + 1} 个喷码处理异常: {str(e)}",
                                        "image_base64_detail": ""
                                    }
                                finally:
                                    # 无论成功还是失败，都尝试添加图片base64编码
                                    if camera_img is not None:
                                        try:
                                            single_result["image_base64_detail"] = base64.b64encode(
                                                cv2.imencode('.jpg', camera_img)[1].tobytes()
                                            ).decode("utf-8")
                                        except Exception as encode_e:
                                            logger.warning(f"图片编码失败: {str(encode_e)}")
                                        finally:
                                            _release(camera_img)
                                return_dict["results"].append(single_result)
                elif request_mode == 1:
                    logger.info(f"人工处理")
                    return_dict["results"] = [
                                                {
                                                    "Ocr_Manufactor": "",  # OCR钢板厂家
                                                    "Ocr_BatchNo": "",  # OCR钢板批号
                                                    "Ocr_Length": 0,  # OCR钢板规格
                                                    "Ocr_Width": 0,  # OCR钢板规格
                                                    "Ocr_Height": 0,  # OCR钢板规格
                                                    "Ocr_Weight": 0,  # OCR钢板重量
                                                    "Ocr_Code": "",  # OCR钢板编号
                                                    "Priority": 0,  # 优先级
                                                    "box": [],
                                                    "status": "error",
                                                    "message": "",
                                                    "image_base64_detail": ""
                                                }
                                            ]

            except Exception as e:
                logger.error(f"OCR处理异常: {str(e)}")
            finally:
                # 记录OCR耗时
                time_stats["ocr_processing"] = time.time() - ocr_start_time
            # # 7. 添加整体图片base64编码
            # with open(img_path_overview, "rb") as image_file:
            #     return_dict['image_base64_overview'] = base64.b64encode(image_file.read()).decode('utf-8')
            # 7. 添加整体图片base64编码（直接从内存编码）
            return_dict['image_base64_overview'] = base64.b64encode(cv2.imencode('.jpg', image_overview)[1]).decode('utf-8')
    except Exception as e:
        return_dict["status"] = "error"
        logger.error(f"处理过程中发生错误: {str(e)}")
    finally:
        # 计算总耗时
        total_time = time.time() - time_stats["start_time"]
        return_dict["time_usage"] = {
            "total": f"{round(total_time, 2)}s",
            "camera_setup": round(time_stats["camera_setup"], 2),
            "mat_info_check": round(time_stats["mat_info_check"], 2),
            "camera_shooting": round(time_stats["camera_shooting"], 2),
            "ocr_processing": round(time_stats["ocr_processing"], 2),
            "corner_detection": round(time_stats["corner_detection"], 2),
            "yolo_detection": round(time_stats["yolo_detection"], 2),
            "camera_movement": round(time_stats["camera_movement"], 2),
            "detail_processing": round(time_stats["detail_processing"], 2)
        }
        logger.info(f"处理完成，耗时统计: {return_dict['time_usage']}")

        # 去重ocr结果
        # return_dict = remove_duplicates(return_dict)
        return_dict = filtering_algorithm(return_dict)

    
    # 创建不包含base64字段的日志对象
    log_dict = return_dict.copy()
    if "image_base64_overview" in log_dict:
        del log_dict["image_base64_overview"]
    if "results" in log_dict:
        for result in log_dict["results"]:
            if "image_base64_detail" in result:
                del result["image_base64_detail"]
    logger.info(f"去重后的返回字典: {log_dict}")
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
    camera_status, camera_msg, camera_img = camera_check(rtsp)
    if camera_status:
        cv2.imwrite("static/baogangsteel.jpg", camera_img)
        encoded_string = base64.b64encode(camera_img)
        encoded_string = encoded_string.decode('utf-8')
        return_dict['image_base64'] = encoded_string
    else:
        logger.info(camera_msg)
        return_dict["status"] = "error"
        return return_dict
    return return_dict


@router.get("/car_height")
async def car_height(session: SessionDep, park_no: str = "", file_path: str = ""):
    """
    获取高度
    """
    return_dict = {
        "status": "success",
        "height": 0.0,
        "message": "",
    }

    get_result_dict = recognize_car_height.get_result(file_path, park_no)
    isSuccess = get_result_dict["isSuccess"]
    if not isSuccess:
        return_dict["status"] = "error"
        return_dict["message"] = get_result_dict["message"]
        return return_dict
    return_dict["message"] = get_result_dict["message"]
    return_dict["height"] = get_result_dict["height"]
    logger.info(f"当前高度：{get_result_dict['height']}")
    return return_dict




@router.get("/safe_region")
async def safe_region(session: SessionDep, file_path: str = "", points: str = "[23.2, 90.14, 1.97]"):
    """
    获取安全区域信息
    
    Args:
        file_path (str): 点云数据文件路径
        points (str): 点坐标字符串，格式为"[x, y, z]"
        
    Returns:
        dict: 安全区域计算结果
    """
    point_info = eval(points)
    res = recognize_safe_area.get_result(file_path, point_info)
    return res


@router.get("/truck_area")
async def truck_area(session: SessionDep, file_path: str = ""):
    """
    获取卡车区域信息
    
    Args:
        file_path (str): 点云数据文件路径
        
    Returns:
        dict: 卡车区域计算结果
    """
    res = recognize_truck_area.get_result(file_path)
    return res


@router.get("/offset")
async def steel_plate_offset(session: SessionDep, file_path: str = "", equipment_number: str = "", length: int = 0, width: int = 0, lifiting_height: int = 0, magnet_offset: int = 0):
    """
    计算钢板偏移量
    
    Args:
        file_path (str): 点云数据文件路径
        equipment_number (str): 设备编号
        length (int): 长度
        width (int): 宽度
        lifiting_height (int): 起升高度
        magnet_offset (int): 磁铁偏移
        
    Returns:
        dict: 偏移量计算结果
    """
    res = recognize_offset.recognize_center(file_path, equipment_number, length, width, lifiting_height, magnet_offset)
    return res


@router.get("/align_and_crosser")
async def align_and_crosser(session: SessionDep, park_no: str = "", file_path: str = "", frame_type: int = 0, empty_statu: int = 0):
    """
    获取对齐和横梁信息
    
    Args:
        park_no (str): 停车位编号
        file_path (str): 点云数据文件路径
        frame_type (int): 框架类型
        empty_statu (int): 空车状态
        
    Returns:
        dict: 对齐和横梁计算结果
    """
    res = recognize_align_and_crosser.get_result(file_path, park_no, frame_type, empty_statu)
    return res


@router.get("/height_difference")
async def plate_height_difference(session: SessionDep, file_path: str = "", angle_points: str = "[[29573, 416296], [28957, 418269], [36490, 418240], [37145, 416207]]"):
    """
    计算钢板高度差
    
    Args:
        file_path (str): 点云数据文件路径
        angle_points (str): 角度点字符串，格式为"[[x1,y1],[x2,y2],[x3,y3],[x4,y4]]"
        
    Returns:
        dict: 高度差计算结果
    """
    angel_points_info = eval(angle_points)
    res = recoginize_plate_height_difference.get_result(file_path, angel_points_info)
    return res


@router.get("/empty_car_position")
async def empty_car_position(session: SessionDep, file_path: str = "", park_no: str = "", car_type: int = 0):
    """
    获取空车位置信息
    
    Args:
        file_path (str): 点云数据文件路径
        park_no (str): 停车位编号
        car_type (int): 车辆类型
        
    Returns:
        dict: 空车位置计算结果
    """
    res = recognize_empty_car.get_result(file_path, park_no, car_type)
    return res


if __name__ == "__main__":
    intelligence_steel_plate("192.168.1.0")
