import json
import math
import os
import re
import time
from datetime import datetime

import cv2
import numpy as np
import pandas as pd
from sqlmodel import select

from app.api.deps import SessionDep
from app.log import logger
from app.models.device import Device
from app.utils.camera_onvif_ln import Camera_ln
from app.utils.device_utils import get_device_info
from app.utils.image_utils import perspective_warp, sort_corners_clockwise
from app.utils.image_save import save_image
from app.utils.fuzzy_recongnition_claude_thinking import quick_match
from app.core.services.ollama_service import get_ollama_spray_code, OLLAMA_AVAILABLE
from ultralytics import YOLO

model = YOLO("../models/yolo_model/best.pt")

with open('cache/perspective_config.json', 'r') as f:
    perspective_config = json.load(f)


def perform_yolo_detection_bak(roi):
    """
    执行YOLO检测并处理检测结果

    Args:
        roi: 感兴趣区域图像

    Returns:
        list: 包含检测结果的列表
    """
    save_dir = r"E:\JJH\dhhi-insightcore\app\static/yolo_results"
    os.makedirs(save_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    yolo_results = model.predict(
        source=roi,
        conf=0.3,
        iou=0.3,
        imgsz=1024,
        half=False,
        device=None,
        max_det=1000,
        save=True,
        save_txt=False,
        save_conf=False,
        show=False,
        project=save_dir,
        name=timestamp
    )
    
    detections = []
    for result in yolo_results:
        for obb in result.obb:
            cls_id = obb.cls.item()
            if cls_id != 0:
                continue
            cx, cy, w, h, angle = obb.xywhr[0, :5].tolist()
            rect = ((cx, cy), (w, h), np.degrees(angle))
            box_points = cv2.boxPoints(rect).astype(int).tolist()
            center = [int(cx), int(cy)]
            print("检测框中心坐标:", center)
            detections.append({
                "confidence": obb.conf.item(),
                "box_points": box_points,
                "center": center,
                "class": obb.cls.item()
            })
    
    return detections


def perform_yolo_detection(roi, width, height, task_time_str, tcp_id):
    """
    执行YOLO检测并处理检测结果

    Args:
        roi: 感兴趣区域图像
        width: 图像宽度
        height: 图像高度
        task_time_str: 任务时间字符串
        tcp_id: TCP ID

    Returns:
        list: 包含检测结果的列表
    """
    save_dir = r"E:\JJH\dhhi-insightcore\app\static\yolo_results"
    os.makedirs(save_dir, exist_ok=True)
    yolo_results = model.predict(
        source=roi,
        conf=0.3,
        iou=0.3,
        imgsz=1024,
        half=False,
        device=None,
        max_det=1000,
        save=True,
        save_txt=False,
        save_conf=False,
        show=False,
        project=save_dir,
        name=f"{task_time_str}_{tcp_id}"
    )

    detections = []
    for result in yolo_results:
        for obb in result.obb:
            cls_id = obb.cls.item()
            if cls_id != 0:
                continue
            conf = obb.conf.item()
            if conf < 0.7:
                continue
            cx, cy, w, h, angle = obb.xywhr[0, :5].tolist()
            rect = ((cx, cy), (w, h), np.degrees(angle))
            ordered_corners = cv2.boxPoints(rect).astype(np.float32)
            offset = np.array([width, height], dtype=np.float32)
            box_native_np = ordered_corners + offset
            box_native = box_native_np.astype(np.int32).tolist()
            center_xy = box_native_np.mean(axis=0)
            center = [int(round(center_xy[0])), int(round(center_xy[1]))]
            
            def calculate_side_lengths(corners):
                side_lengths = []
                for i in range(4):
                    p1 = corners[i]
                    p2 = corners[(i + 1) % 4]
                    length = np.linalg.norm(p1 - p2)
                    side_lengths.append(length)
                length1 = (side_lengths[0] + side_lengths[2]) / 2
                length2 = (side_lengths[1] + side_lengths[3]) / 2
                actual_length = max(length1, length2)
                actual_width = min(length1, length2)
                return actual_length, actual_width

            long_side, short_side = calculate_side_lengths(box_native_np)
            print(f"检测框中心坐标:{center}, 宽:{long_side:.2f}, 长:{short_side:.2f}")
            logger.info(f"检测框中心坐标:{center}")
            detections.append({
                "confidence": obb.conf.item(),
                "box_points": box_native,
                "center": center,
                "class": obb.cls.item(),
                "long_side": long_side,
                "short_side": short_side
            })

    return detections


def map_lane_ip_and_ranges(ip: str):
    """
    根据传入的"逻辑"ip，映射到真实拍摄 ip 与其 location_ranges。
    
    Args:
        ip (str): 逻辑IP地址
        
    Returns:
        tuple: (ip_ocr, ranges)
            - ip_ocr (str): 真实的OCR相机IP
            - ranges (list): 位置范围列表
    """
    if ip == "192.168.3.69":
        ip_ocr = "192.168.3.59"; ranges = perspective_config[ip_ocr]["location_ranges_tpc11"]
    elif ip == "192.168.3.70":
        ip_ocr = "192.168.3.59"; ranges = perspective_config[ip_ocr]["location_ranges_tpc9"]
    elif ip == "192.168.3.71":
        ip_ocr = "192.168.3.59";  ranges = perspective_config[ip_ocr]["location_ranges_tpc12"]
    elif ip == "192.168.3.72":
        ip_ocr = "192.168.3.59";  ranges = perspective_config[ip_ocr]["location_ranges_tpc10"]
    elif ip == "192.168.3.65":
        ip_ocr = "192.168.3.55"; ranges = perspective_config[ip_ocr]["location_ranges_tpc7"]
    elif ip == "192.168.3.66":
        ip_ocr = "192.168.3.55"; ranges = perspective_config[ip_ocr]["location_ranges_tpc5"]
    elif ip == "192.168.3.67":
        ip_ocr = "192.168.3.55"; ranges = perspective_config[ip_ocr]["location_ranges_tpc8"]
    elif ip == "192.168.3.68":
        ip_ocr = "192.168.3.55"; ranges = perspective_config[ip_ocr]["location_ranges_tpc6"]
    elif ip == "192.168.3.61":
        ip_ocr = "192.168.3.50"; ranges = perspective_config[ip_ocr]["location_ranges_tpc3"]
    elif ip == "192.168.3.62":
        ip_ocr = "192.168.3.50"; ranges = perspective_config[ip_ocr]["location_ranges_tpc1"]
    elif ip == "192.168.3.63":
        ip_ocr = "192.168.3.50"; ranges = perspective_config[ip_ocr]["location_ranges_tpc4"]
    elif ip == "192.168.3.64":
        ip_ocr = "192.168.3.50"; ranges = perspective_config[ip_ocr]["location_ranges_tpc2"]
    else:
        ip_ocr = ip
        ranges = perspective_config.get(ip, {}).get("location_ranges", [])
    return ip_ocr, ranges


def get_fixed_center_by_ip(ip):
    """
    根据IP地址获取固定的中心点坐标
    
    Args:
        ip (str): 设备IP地址
        
    Returns:
        tuple: (center_x, center_y)
            - center_x (int): 中心点X坐标
            - center_y (int): 中心点Y坐标
    """
    ip_center_map = {
        "192.168.3.64": (1655, 843), #TCP2
        "192.168.3.62": (2313,911), #TCP1
        "192.168.3.63": (2059, 901), #TCP4
        "192.168.3.61": (1695, 1055), #TCP3
        "192.168.3.68": (1410, 901), #TCP6
        "192.168.3.66": (2703, 919), #TCP5
        "192.168.3.67": (2281, 827), #TCP8
        "192.168.3.65": (1415, 956), #TCP7
        "192.168.3.70": (2615, 819), #TCP9
        "192.168.3.72": (1096,807), #TCP10
        "192.168.3.69": (1497, 1021), #TCP11
        "192.168.3.71": (1063, 655), #TCP12
    }

    default_center = (1920, 1080)

    return ip_center_map.get(ip, default_center)


def validate_mat_infos(request_data):
    """
    验证物料信息数据的有效性

    Args:
        request_data (dict): 包含物料信息的请求数据

    Returns:
        tuple: (校验结果, 数据/错误信息)
              - 校验成功: (True, mat_infos_df)，其中mat_infos_df是Pandas DataFrame
              - 校验失败: (False, 错误信息字符串)
    """
    if 'mat_infos' not in request_data:
        return False, "JSON缺少必需字段'mat_infos'，将进入人工确认"

    try:
        mat_infos = request_data['mat_infos']

        if not isinstance(mat_infos, list):
            raise TypeError("mat_infos必须是数组类型")
        if len(mat_infos) == 0:
            raise ValueError("mat_infos不能为空数组")

        required_keys = {'mat_no', 'mat_length', 'mat_width', 'mat_thick', 'mat_weight'}
        validated_data = []

        for item in mat_infos:
            missing = required_keys - item.keys()
            if missing:
                raise ValueError(f"钢板{item.get('mat_no', '')}缺少字段：{missing}")
            validated_data.append({
                'mat_no': str(item['mat_no']),
                'mat_length': int(item['mat_length']),
                'mat_width': int(item['mat_width']),
                'mat_thick': int(item['mat_thick']),
                'mat_weight': int(item['mat_weight'])
            })

        mat_infos_df = pd.DataFrame(validated_data)
        return True, mat_infos_df

    except (ValueError, TypeError) as e:
        return False, f"物料信息校验失败: {str(e)}"


def detect_corners(detector, image_input, FLAGS):
    """
    检测图像中的钢板角点

    Args:
        detector: 目标检测器实例
        image_input: 图像文件路径或numpy数组
        FLAGS: 配置参数对象

    Returns:
        tuple: (原始图像, 检测到的角点列表)
              角点列表为按顺时针排序的四个坐标点，格式为[[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
              如果未检测到角点，返回None
    """
    if isinstance(image_input, str):
        if not os.path.exists(image_input):
            raise FileNotFoundError(f"图像文件不存在：{image_input}")
        image = cv2.imread(image_input)
        input_name = os.path.splitext(os.path.basename(image_input))[0]
    elif isinstance(image_input, np.ndarray):
        if len(image_input.shape) != 3 or image_input.shape[2] != 3:
            raise ValueError("输入图像数组格式应为HWC三通道BGR格式")
        image = image_input
        input_name = "memory_image_" + str(hash(image_input.tobytes()))[:8]
    else:
        raise TypeError("不支持的输入类型，请输入文件路径字符串或numpy数组")

    if image is None:
        raise ValueError("无法解析输入图像")
    
    scale_percent = 50
    width = int(image.shape[1] * scale_percent / 100)
    height = int(image.shape[0] * scale_percent / 100)
    resized_img = cv2.resize(image, (width, height))
    
    scale = scale_percent / 100
    inv_scale = 1 / scale
    custom_output_dir = r"E:\JJH\dhhi-insightcore\output_images"
    detector.output_dir = custom_output_dir
    result = detector.predict_image(
        [resized_img],
        FLAGS.run_benchmark,
        repeats=1,
        visual=False,
        save_results=False
    )

    corners = None
    if result and 'masks' in result and len(result['masks']) > 0:
        for i, row in enumerate(result['boxes']):
            if row[1] > 0.30 and int(row[0]) == 0:
                corners = get_steel_corners_from_mask(result['masks'][i])
                if corners is not None:
                    corners = (corners * inv_scale).astype(int)
                    corners = sort_corners_clockwise(corners).tolist()
                    break
    return image, corners


def verify_batch_only(results, mat_infos_df, result_item, image_data=None):
    """
    验证OCR识别结果中的批次号是否与物料信息匹配

    Args:
        results: OCR识别结果，格式为字典，包含各区域的识别文本
        mat_infos_df: 物料信息数据框，包含钢板编号等信息
        result_item: 结果字典，用于存储验证结果
        image_data: 图片数据（bytes 格式），用于 Ollama 二次识别

    Returns:
        pandas.DataFrame: 包含匹配到的物料信息的数据框
    """
    valid_batch_found = False
    return_df = pd.DataFrame()

    # 准备喷码数据列表
    spray_codes = mat_infos_df[['mat_no']].to_dict('records')

    for result in results:
        coordinates = results[result]['coordinates']
        if results[result]['ocr_result'][0] is None:
            continue
        for r in results[result]['ocr_result'][0]:
            text = r[1][0]
            if len(text) < 8:
                continue

            # 使用quick_match进行模糊匹配
            matches = quick_match(text, spray_codes, top_k=3)

            # 筛选置信度大于0.75的匹配结果
            valid_matches = [(code, confidence) for code, confidence in matches if confidence > 0.75]

            if not valid_matches:
                continue

            # 取置信度最高的结果
            best_match, best_confidence = valid_matches[0]

            logger.info(f"OCR文本: {text}, 最佳匹配: {best_match}, 置信度: {best_confidence:.2%}")

            # 查找匹配的物料信息
            matched_row = mat_infos_df[mat_infos_df["mat_no"] == best_match].iloc[0].copy()
            points = coordinates
            x_sum = sum(point[0] for point in points)
            y_sum = sum(point[1] for point in points)
            n = len(points)
            midpoint = (x_sum / n, y_sum / n)
            distance = math.sqrt((midpoint[0] - 1920) ** 2 + (midpoint[1] - 1080) ** 2)
            matched_row['distance'] = distance
            matched_row['confidence'] = best_confidence

            logger.info(f"提取的数据行：{matched_row}")
            return_df = pd.concat([return_df, pd.DataFrame([matched_row])], ignore_index=True)
            valid_batch_found = True

    # 如果 OCR 未匹配到有效结果，尝试 Ollama 二次识别
    if return_df.empty and OLLAMA_AVAILABLE and image_data is not None:
        logger.info("OCR 未匹配到有效喷码，尝试 Ollama 二次识别")
        try:
            valid_mat_nos = mat_infos_df['mat_no'].tolist()
            spray_code, in_list = get_ollama_spray_code(image_data, valid_mat_nos)
            
            if spray_code and in_list:
                logger.info(f"Ollama 二次识别成功: {spray_code}")
                matched_row = mat_infos_df[mat_infos_df["mat_no"] == spray_code].iloc[0].copy()
                matched_row['distance'] = 0
                matched_row['confidence'] = 0.95
                return_df = pd.DataFrame([matched_row])
                valid_batch_found = True
            elif spray_code and not in_list:
                logger.info(f"Ollama 识别到喷码 {spray_code} 但不在有效列表中")
        except Exception as ollama_e:
            logger.error(f"Ollama 二次识别异常: {str(ollama_e)}")

    if not return_df.empty:
        return_df = return_df.drop_duplicates(subset=['mat_no'])
        return_df['mat_area'] = return_df['mat_length'] * return_df['mat_width']

        # 计算综合评分
        # confidence: 越高越好 (0-1)
        # distance: 越低越好，转换为 0-1 的分数
        max_distance = return_df['distance'].max()
        if max_distance > 0:
            return_df['distance_score'] = 1 - (return_df['distance'] / max_distance)
        else:
            return_df['distance_score'] = 1.0

        # 综合评分 = 0.7 * confidence + 0.3 * distance_score
        # 置信度权重更高，因为匹配准确性更重要
        return_df['total_score'] = 0.7 * return_df['confidence'] + 0.3 * return_df['distance_score']

        # 按照综合评分降序排序
        return_df = return_df.sort_values(by='total_score', ascending=False)
        return_df = return_df.head(1)
        result_item["Ocr_BatchNo"] = return_df["mat_no"].values[0]


    if valid_batch_found:
        result_item.update({
            "status": "success",
            "message": "喷码验证成功"
        })
    else:
        result_item.update({
            "status": "error",
            "message": "未找到有效喷码"
        })

    return return_df


def verify_batch_only_old(results, mat_infos_df, result_item):
    """
    验证OCR识别结果中的批次号是否与物料信息匹配

    Args:
        results: OCR识别结果，格式为字典，包含各区域的识别文本
        mat_infos_df: 物料信息数据框，包含钢板编号等信息
        result_item: 结果字典，用于存储验证结果

    Returns:
        pandas.DataFrame: 包含匹配到的物料信息的数据框
    """
    batch_pattern = r"(\d{10}|(?=.*\d)(?=.*[A-Z])[A-Za-z0-9]{10})"

    valid_batch_found = False
    return_list = []
    return_df = pd.DataFrame()

    for result in results:
        coordinates = results[result]['coordinates']
        if results[result]['ocr_result'][0] is None:
            continue
        for r in results[result]['ocr_result'][0]:
            text = r[1][0]
            if len(text) != 10:
                continue
            matches = re.findall(batch_pattern, text)
            if not matches:
                continue
            for match in matches:
                matched = False
                final_match = None
                if match in mat_infos_df["mat_no"].values:
                    final_match = match
                    matched = True
                    print(f"匹配成功：{final_match}")
                if not matched:
                    fixed_match = None
                    if match[1] == "8":
                        fixed_match = match[:1] + "B" + match[2:]
                    elif match[1] == "0":
                        fixed_match = match[:1] + "C" + match[2:]
                    elif match[0] == "5":
                        fixed_match = "6" + match[1:]
                    if fixed_match and fixed_match in mat_infos_df["mat_no"].values:
                        final_match = fixed_match
                        matched = True
                if matched:
                    matched_row = mat_infos_df[mat_infos_df["mat_no"] == final_match].iloc[0].copy()
                    points = coordinates
                    x_sum = sum(point[0] for point in points)
                    y_sum = sum(point[1] for point in points)
                    n = len(points)
                    midpoint = (x_sum / n, y_sum / n)
                    distance = math.sqrt((midpoint[0] - 1920) ** 2 + (midpoint[1] - 1080) ** 2)
                    matched_row['distance'] = distance

                    print(f"提取的数据行：{matched_row}")
                    return_df = pd.concat([return_df, pd.DataFrame([matched_row])], ignore_index=True)
                    valid_batch_found = True

    if not return_df.empty:
        return_df = return_df.drop_duplicates(subset=['mat_no'])
        return_df['mat_area'] = return_df['mat_length'] * return_df['mat_width']
        return_df = return_df.sort_values(by='distance', ascending=True)
        return_df = return_df.head(1)
        result_item["Ocr_BatchNo"] = return_df["mat_no"].values[0]

    if valid_batch_found:
        result_item.update({
            "status": "success",
            "message": "喷码验证成功"
        })
    else:
        result_item.update({
            "status": "error",
            "message": "未找到有效喷码"
        })

    return return_df

def verify_batch_and_weight(results, mat_infos_df, result_item):
    """
    验证OCR识别结果中的批次号、尺寸和重量是否与物料信息匹配

    Args:
        results: OCR识别结果，格式为字典，包含各区域的识别文本
        mat_infos_df: 物料信息数据框，包含钢板编号等信息
        result_item: 结果字典，用于存储验证结果
    """
    batch_pattern = r"(\d{10}|(?=.*\d)(?=.*[A-Z])[A-Za-z0-9]{10})"
    dimension_pattern = r"^(\d+\.\d{2})\*(\d+)\*(\d+)$"
    weight_pattern = r"(\d+)\s*(KG)"

    valid_batch_found = False
    dimension_match = False
    weight_match = False
    detected_dimensions = None
    detected_weight = None
    dimension_calc = None

    for result in results:
        if results[result]['ocr_result'][0] is None:
            continue
        for r in results[result]['ocr_result'][0]:
            text = r[1][0]
            if len(text) == 10:
                matches = re.findall(batch_pattern, text)
                if matches:
                    for match in matches:
                        if match in mat_infos_df["mat_no"].values:
                            print(f"匹配成功：{match}")
                            result_item["Ocr_BatchNo"] = match
                            valid_batch_found = True
                            break
            if valid_batch_found:
                break
        if valid_batch_found:
            break

    if valid_batch_found:
        for result in results:
            if results[result]['ocr_result'][0] is None:
                continue
            for r in results[result]['ocr_result'][0]:
                text = r[1][0]

                dimension_matches = re.findall(dimension_pattern, text)
                if dimension_matches and not dimension_match:
                    length, width, height = map(float, dimension_matches[0])
                    detected_dimensions = (length, width, height)
                    dimension_calc = int(length * width * height * 7850)
                    dimension_match = True

                weight_matches = re.findall(weight_pattern, text)
                if weight_matches and not weight_match:
                    detected_weight = float(weight_matches[0][0])
                    weight_match = True

                if dimension_match and weight_match:
                    break
            if dimension_match and weight_match:
                break

        if dimension_match and weight_match:
            calc_first_four = str(dimension_calc)[:4]
            weight_first_four = str(int(detected_weight))[:4]
            print(f"尺寸前四位：{calc_first_four}, 重量前四位：{weight_first_four}")

            if abs(int(calc_first_four) - int(weight_first_four)) < 2:
                matched_weight = mat_infos_df.loc[mat_infos_df["mat_no"] == match, "mat_weight"].values
                matched_weight_str = str(int(matched_weight[0]))[:4]

                matched = False
                for weight, unit in weight_matches:
                    if weight_first_four == matched_weight_str:
                        result_item.update({
                            "status": "success",
                            "message": "喷码验证成功"
                        })
                        matched = True
                        break

                if not matched:
                    result_item.update({
                        "status": "warning",
                        "message": f"喷码验证成功，但重量信息异常(检测值'{weight_first_four}',预期值'{matched_weight_str}')"
                    })
            else:
                result_item.update({
                    "status": "warning",
                    "message": "喷码验证成功，但尺寸与重量不匹配"
                })
        else:
            if not dimension_match and not weight_match:
                result_item.update({
                    "status": "success",
                    "message": "喷码验证成功，未找到尺寸和重量信息"
                })


def calc_steel(result, img_list, width, height):
    """
    计算钢板的相关信息（中心点、边框、角度等）
    
    Args:
        result: 检测结果
        img_list: 图像列表，支持两种格式：
            - 图像路径列表：["path/to/image.jpg", ...]
            - cv2 图像对象列表：[cv2_image, ...]
        width (int): 图像宽度
        height (int): 图像高度
        
    Returns:
        list: [center_x, center_y, box_native, box, angle1, angle2, annotated_image_path]
    """
    # 兼容两种输入格式：图像路径或 cv2 图像对象
    if isinstance(img_list[0], str):
        img = cv2.imread(img_list[0])
    else:
        img = img_list[0].copy()
    
    boxes_num = result['boxes_num'][0]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_result_folder = r"E:\JJH\dhhi-insightcore\app\static\steel_output"
    warped_concerresult_filename = os.path.join(output_result_folder, f"warped_concerresult_{timestamp}.jpg")

    for i, row in enumerate(result['boxes']):
        if row[1] > 0.30 and int(row[0]) == 0:
            mask = result['masks'][i].astype(np.uint8)
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            sorted_contours = sorted(contours, key=cv2.contourArea, reverse=True)

            if len(sorted_contours) == 0:
                return (0, 0, [[0, 0], [0, 0], [0, 0], [0, 0]], [[0, 0], [0, 0], [0, 0]])

            largest_contour = sorted_contours[0]
            print("Largest contour area:", cv2.contourArea(largest_contour))

            hull = cv2.convexHull(largest_contour)

            rect = cv2.minAreaRect(hull)
            box = cv2.boxPoints(rect)

            corners = sort_corners_clockwise(box)

            center = corners.mean(axis=0)

            def sort_key(point):
                x, y = point - center
                return math.atan2(y, x)

            sorted_corners = sorted(corners, key=sort_key)

            top_points = sorted(sorted_corners, key=lambda x: x[1])[:2]
            tl = min(top_points, key=lambda x: x[0])
            tr = max(top_points, key=lambda x: x[0])

            bottom_points = sorted(sorted_corners, key=lambda x: -x[1])[:2]
            br = max(bottom_points, key=lambda x: x[0])
            bl = min(bottom_points, key=lambda x: x[0])

            ordered_corners = np.array([tl, tr, br, bl])

            upper_edge = tr - tl
            upper_angle = math.degrees(math.atan2(upper_edge[1], upper_edge[0]))

            lower_edge = br - bl
            lower_angle = math.degrees(math.atan2(lower_edge[1], lower_edge[0]))

            M = cv2.moments(largest_contour)
            cx = int(M['m10'] / M['m00'])
            cy = int(M['m01'] / M['m00'])

            cv2.circle(img, (cx, cy), 5, (225, 225, 225), -1)

            box_native = ordered_corners.tolist()
            box = (ordered_corners + np.array([width, height])).tolist()

            cv2.polylines(img, [ordered_corners.astype(int)], True, (0, 255, 0), 2)

            output_filename = warped_concerresult_filename
            save_image(output_filename, img)
            # print(f"Image saved as {output_filename}")

            cx_o = cx + width
            cy_o = cy + height

            return (cx_o, cy_o, box, box_native, upper_angle, lower_angle, output_filename)

    return (0, 0, [[0, 0], [0, 0], [0, 0], [0, 0]], [[0, 0], [0, 0], [0, 0]])


def get_steel_corners_from_mask(mask):
    """从分割mask提取四个精确角点"""
    contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    largest_contour = max(contours, key=cv2.contourArea)
    hull = cv2.convexHull(largest_contour)

    epsilon = 0.02 * cv2.arcLength(hull, True)
    approx = cv2.approxPolyDP(hull, epsilon, True)

    if len(approx) != 4:
        rect = cv2.minAreaRect(hull)
        box = cv2.boxPoints(rect)
        corners = sort_corners_clockwise(box)
    else:
        corners = approx.reshape(4, 2)
    return corners


def get_perspective_data(session: SessionDep, ip: str, height: float = None, image = None):
    """统一配置解析函数
    Args:
        ip: 设备IP地址
        height: 可选高度参数，当需要计算变换矩阵时传入
    Returns:
        包含 dstArr 和变换矩阵的字典，或 None
    """
    if ip not in perspective_config:
        print(f"未找到配置文件中对应的 IP: {ip}")
        return None
    config = perspective_config[ip]
    account, password, _ = get_device_info(session, ip)
    if "location_ranges" in config and len(config["location_ranges"]) > 0:
        try:
            camera_ocr = Camera_ln(ip, account, password, 0, 0)
            camera_ocr.connect_ONVIF()
            current_pos = camera_ocr.get_camera_location1()
            target_pos = config["location_ranges"][0]
            tolerance = 0.02
            needs_adjust = any(
                abs(current_pos[key] - target_pos[key]) > tolerance
                for key in ["x", "y", "z"]
            )

            if needs_adjust:
                print(f"[{ip}] Adjusting PTZ from {current_pos} to {target_pos}")
                camera_ocr.ptz_absolute_move(
                    target_pos["x"],
                    target_pos["y"],
                    target_pos["z"]
                )
                time.sleep(1.5)
            else:
                print(f"[{ip}] PTZ position is correct")

        except Exception as e:
            print(f"[{ip}] PTZ adjustment failed: {str(e)}")
    result = {
        "10x_dstArr": np.float32(config["10x_reduction_dstArr"]),
        "native_dstArr": np.float32(config.get("native_dstArr", [[0]*2]*4))
    }
    if height is not None:
        for entry in config["height_ranges"]:
            if entry["height_min"] <= height < entry["height_max"]:
                src = np.float32(entry["srcArr"])
                dst = result["10x_dstArr"]
                original_dst = np.float32(dst)

                min_x = int(original_dst[:,0].min())-300
                min_y = int(original_dst[:,1].min())-500

                translated_dst = original_dst - np.array([min_x, min_y]).astype(np.float32)

                assert src.shape == (4, 2), "src 必须为 4×2 的数组"
                assert translated_dst.shape == (4, 2), "dst 必须为 4×2 的数组"

                MM = cv2.getPerspectiveTransform(src, translated_dst)
                result["transform_matrix"] = MM

                re_pic = cv2.warpPerspective(image, MM, (int(translated_dst[:,0].max()) + 300, int(translated_dst[:,1].max()) + 500))

                (width, height) = (min_x, min_y)
                result["width"] = width
                result["height"] = height
                return result, re_pic
        print(f"未找到匹配的高度区间: {height}")
        return None

    return result
