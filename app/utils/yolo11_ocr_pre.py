import os
import cv2
import numpy as np
from ultralytics import YOLO
from paddleocr import PaddleOCR, draw_ocr
from PIL import Image
from pathlib import Path


class OcrProcessor:
    """
    OCR处理类：用于检测喷码区域并识别喷码文字
    
    主要功能：
    1. 使用YOLO模型检测喷码区域
    2. 对检测到的区域进行旋转和裁剪
    3. 对裁剪后的图像进行剪切校正（修正文字倾斜）
    4. 使用PaddleOCR识别喷码文字
    5. 对原始和旋转180度的图像分别进行OCR，提高识别率
    """
    
    def __init__(self,
                 yolo_model_path: str,
                 det_model_dir: str,
                 rec_model_dir: str,
                 rec_char_dict_path: str,
                 output_dir: str = "./output"):
        """
        初始化OCR处理类
        
        Args:
            yolo_model_path: YOLO模型路径，用于检测喷码区域
            det_model_dir: PaddleOCR检测模型目录
            rec_model_dir: PaddleOCR识别模型目录
            rec_char_dict_path: 字符字典文件路径
            output_dir: 输出目录，用于保存中间结果和可视化图片
        """
        # 初始化YOLO模型，用于检测喷码区域
        self.yolo_model = YOLO(yolo_model_path)
        
        # 初始化PaddleOCR模型，用于识别喷码文字
        self.ocr_model = PaddleOCR(
            lang="en",  # 使用英文模型
            det_model_dir=det_model_dir,
            rec_model_dir=rec_model_dir,
            rec_char_dict_path=rec_char_dict_path,
            show_log=False
        )
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def _rotate_and_crop(self, image: np.ndarray, points: np.ndarray, class_id: int) -> tuple:
        """
        执行旋转和裁剪操作，将检测到的喷码区域旋转至水平方向并裁剪
        
        Args:
            image: 输入图像（BGR格式）
            points: 检测框的四个角点坐标
            class_id: 检测类别ID
            
        Returns:
            tuple: (cropped_image, rotated_180)
                - cropped_image: 裁剪后的图像（可能旋转90度）
                - rotated_180: 裁剪后旋转180度的图像
        """
        # 计算最小外接矩形
        rect = cv2.minAreaRect(points)
        box = cv2.boxPoints(rect)
        box = np.int0(box)

        center, size, angle = rect
        
        # 如果角度小于-45度，调整角度和尺寸
        if angle < -45:
            angle += 90
            size = (size[1], size[0])

        # 打印角点信息（调试用）
        # for i, (x, y) in enumerate(box):
        #     print(f"Point {i}: ({x}, {y})")

        # 扩展裁剪区域尺寸，确保包含完整内容
        expanded_size = (int(size[0]+200), int(size[1]+200))

        h, w = image.shape[:2]
        
        # 计算旋转矩阵并应用旋转
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated_image = cv2.warpAffine(image, rotation_matrix, (w, h))
        
        # 保存旋转后的图像（调试用）
        save_path = Path(__file__).parent / "static" / "processed_results" / "rotated_image.jpg"
        cv2.imwrite(save_path, rotated_image)
        
        # 计算裁剪区域，保证不越界
        cx, cy = int(center[0]), int(center[1])
        half_w, half_h = expanded_size[0] // 2, expanded_size[1] // 2
        x1, y1 = max(0, cx - half_w), max(0, cy - half_h)
        x2, y2 = min(w, cx + half_w), min(h, cy + half_h)
        cropped_image = rotated_image[y1:y2, x1:x2]
        
        # 如果宽度小于高度，顺时针旋转90度
        h_c, w_c = cropped_image.shape[:2]
        if w_c < h_c:
            cropped_image = cv2.rotate(cropped_image, cv2.ROTATE_90_CLOCKWISE)

        # 生成180度旋转版本，用于处理反向喷码
        rotated_180 = cv2.rotate(cropped_image, cv2.ROTATE_180)

        return cropped_image, rotated_180

    def shear_correct(self, image: np.ndarray) -> np.ndarray:
        """
        对图像进行剪切校正，修正因拍摄角度导致的文字倾斜
        
        Args:
            image: 输入图像（BGR格式）
            
        Returns:
            np.ndarray: 校正后的图像
        """
        # 转换为灰度图
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # 高斯模糊 + 自适应二值化
        thresh = cv2.adaptiveThreshold(cv2.GaussianBlur(gray, (5, 5), 0), 255,
                                       cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY_INV, 11, 4)

        # 形态学操作：先水平闭运算连接字符，再垂直闭运算
        kernel_h = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 3))
        kernel_v = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 15))
        morph = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel_h)
        morph = cv2.morphologyEx(morph, cv2.MORPH_CLOSE, kernel_v)

        # 找到最大轮廓并计算凸包
        contours, _ = cv2.findContours(morph, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        hull = cv2.convexHull(max(contours, key=cv2.contourArea))
        points = hull.reshape(-1, 2)

        # 找左侧最长的垂直边，用于计算剪切角度
        min_x = np.min(points[:, 0])
        left_thresh = min_x + (np.max(points[:, 0]) - min_x) * 0.3

        best_len, best_edge = 0, None
        for i in range(len(points)):
            p1, p2 = points[i], points[(i + 1) % len(points)]
            # 只考虑左侧30%区域的边
            if p1[0] <= left_thresh and p2[0] <= left_thresh:
                length = np.linalg.norm(p2 - p1)
                # 计算边的角度
                angle = abs(np.degrees(np.arctan2(p2[1] - p1[1], p2[0] - p1[0])))
                # 只考虑60-120度的垂直边
                if 60 <= angle <= 120 and length > best_len:
                    best_len, best_edge = length, (p1, p2)

        # 如果没找到合适的边，直接返回原图
        if best_edge is None:
            return image

        # 计算剪切系数（根据找到的垂直边）
        p1, p2 = (best_edge[0], best_edge[1]) if best_edge[0][1] < best_edge[1][1] else (best_edge[1], best_edge[0])
        shear = -(p2[0] - p1[0]) / (p2[1] - p1[1])

        # 应用剪切变换
        h, w = image.shape[:2]
        offset = max(0, -shear * h)
        new_w = int(w + abs(shear * h))
        matrix = np.array([[1, shear, offset], [0, 1, 0]], dtype=np.float32)
        result = cv2.warpAffine(image, matrix, (new_w, h), borderValue=(255, 255, 255))

        # 可视化检测结果（调试用，已注释）
        # vis = img.copy()
        # cv2.drawContours(vis, [hull], 0, (255, 0, 0), 2)
        # cv2.line(vis, tuple(p1.astype(int)), tuple(p2.astype(int)), (0, 255, 0), 5)

        return result

    def _process_ocr(self, image: np.ndarray, output_prefix: str) -> list:
        """
        执行OCR处理并保存结果
        
        Args:
            image: 输入图像（BGR格式）
            output_prefix: 输出文件名前缀
            
        Returns:
            list: PaddleOCR的识别结果
        """
        # 保存临时图像（PaddleOCR需要文件路径）
        temp_path = os.path.join(self.output_dir, "temp_crop.png")
        cv2.imwrite(temp_path, image, [cv2.IMWRITE_JPEG_QUALITY, 100])

        # 执行OCR识别
        result = self.ocr_model.ocr(image, cls=False)
        
        # 删除临时文件
        if os.path.exists(temp_path):
            os.remove(temp_path)

        # 如果没有识别结果，直接返回
        if result[0] is None:
            return result
        
        # 可视化处理：绘制检测框和识别文字
        if len(result[0]) > 0:
            image_pil = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            boxes = [line[0] for line in result[0]]
            txts = [line[1][0] for line in result[0]]
            scores = [line[1][1] for line in result[0]]

            # 使用PaddleOCR提供的可视化函数
            visualized = draw_ocr(
                image_pil,
                boxes,
                txts,
                scores,
                font_path='./PaddleOCR/doc/fonts/simfang.ttf'
            )
            # 保存可视化结果
            save_path = os.path.join(self.output_dir, f"{output_prefix}_result.jpg")
            Image.fromarray(visualized).save(save_path)

        return result

    def process_image(self, image_input) -> dict:
        """
        主处理流程：YOLO检测 -> 旋转裁剪 -> 剪切校正 -> OCR识别
        
        Args:
            image_input: 输入图像，可以是文件路径（str）或numpy数组
            
        Returns:
            dict: 包含所有检测结果的字典
                - key: "detection_{idx}_{i}" 格式的键
                - value: {
                    "class_id": 类别ID,
                    "coordinates": 检测框坐标,
                    "ocr_result": OCR识别结果,
                    "image_variants": 包含原始和旋转180度的图像
                }
        """
        # 处理不同类型的输入
        if isinstance(image_input, str):
            # 输入是文件路径
            if not os.path.exists(image_input):
                raise FileNotFoundError(f"图像文件不存在：{image_input}")
            image = cv2.imread(image_input)
            input_name = os.path.splitext(os.path.basename(image_input))[0]
        elif isinstance(image_input, np.ndarray):
            # 输入是numpy数组
            if len(image_input.shape) != 3 or image_input.shape[2] != 3:
                raise ValueError("输入图像数组格式应为HWC三通道BGR格式")
            image = image_input
            input_name = "memory_image_" + str(hash(image_input.tobytes()))[:8]
        else:
            raise TypeError("不支持的输入类型，请输入文件路径字符串或numpy数组")

        if image is None:
            raise ValueError("无法解析输入图像")

        # 使用YOLO模型检测喷码区域
        results = self.yolo_model.predict(
            source=image,  # 输入图像
            conf=0.3,  # 置信度阈值
            iou=0.3,  # IoU阈值，用于NMS
            imgsz=1024,  # 输入图像大小
            half=False,  # 不使用半精度
            device=None,  # 自动选择设备（CPU或GPU）
            max_det=1000,  # 最大检测数量
            save=False,  # 不保存推理结果
            verbose=False,  # 不显示推理信息
            save_txt=False,  # 不保存检测结果到文本文件
            save_conf=False,  # 不保存置信度
            show=False,  # 不显示推理图像
        )

        final_results = {}
        try:
            # 遍历所有检测结果
            for idx, result in enumerate(results):
                # 跳过无效结果
                if result.obb.xyxyxyxy is None or result.obb.cls is None:
                    continue
                    
                # 遍历每个检测框
                for i in range(len(result.obb.cls)):
                    class_id = int(result.obb.cls[i])
                    
                    # 只处理类别为0的检测框（喷码类别）
                    if class_id != 0:
                        continue
                        
                    # 获取检测框坐标
                    points = result.obb.xyxyxyxy[i].cpu().numpy()

                    # 获取两种方向的裁剪结果（原始和旋转180度）
                    cropped_img, rotated_img = self._rotate_and_crop(image, points, class_id)
                    
                    # 对两种图像分别进行剪切校正
                    cropped_img_corrected = self.shear_correct(cropped_img)
                    rotated_img_corrected = self.shear_correct(rotated_img)

                    # 对两种图像分别进行OCR处理
                    ocr_result1 = self._process_ocr(cropped_img_corrected, f"{os.path.basename(input_name)}_{idx}_{i}_raw")
                    ocr_result2 = self._process_ocr(rotated_img_corrected, f"{os.path.basename(input_name)}_{idx}_{i}_rotated")

                    # 合并两种OCR结果
                    combined_results = []
                    if ocr_result1[0] is not None:
                        combined_results.extend(ocr_result1[0])
                    if ocr_result2[0] is not None:
                        combined_results.extend(ocr_result2[0])

                    # 保存最终结果
                    final_results[f"detection_{idx}_{i}"] = {
                        "class_id": class_id,
                        "coordinates": points.tolist(),
                        "ocr_result": [combined_results] if combined_results else [None],
                        "image_variants": {
                            "original": cropped_img,
                            "rotated_180": rotated_img
                        }
                    }
        except Exception as e:
            print(e)
        return final_results


# 使用示例
if __name__ == "__main__":
    import re

    processor = OcrProcessor(
        yolo_model_path="E:/JJH/dhhi-insightcore/models/yolo_model/best.pt",
        det_model_dir="E:/JJH/dhhi-insightcore/models/ocr_model/det_ch_PP-OCRv3_inference_0117/Student",
        rec_model_dir="E:/JJH/dhhi-insightcore/models/ocr_model/rec_en_PP-OCRv4_inference_0109",
        rec_char_dict_path="E:/JJH/dhhi-insightcore/models/ocr_model/en_dict.txt",
        output_dir="E:/JJH/dhhi-insightcore/app/static/processed_results"
    )

    results = processor.process_image(
        r"C:\Users\CTOS\Desktop\每日异常统计\OCR\20260113\字符识别错误\1768260961500_0.jpg")

    print("OCR处理完成，结果保存至：", processor.output_dir)

    # 正则匹配处理
    pattern = r"(\d{10}|(?=.*\d)(?=.*[A-Z])[A-Za-z0-9]{10})"
    all_matches = []

    if len(results) > 0:
        for result_id in results:
            ocr_results = results[result_id]['ocr_result'][0]

            if ocr_results is None:
                continue

            for r in ocr_results:
                text = r[1][0]
                confidence = r[1][1]

                if len(text) == 10:
                    matches = re.findall(pattern, text)
                    if matches:
                        for match in matches:
                            print(f"区域 {result_id} 匹配到: {match} (置信度: {confidence:.2f})")
                            all_matches.append({
                                'region': result_id,
                                'text': match,
                                'confidence': confidence
                            })
                            # -----------------------------
                            # 新增：第二位若为 '8' → 自动替换为 'B'
                            # -----------------------------
                            if match[1] == '8':  # 第二个字符，下标1
                                modified = match[:1] + 'B' + match[2:]

                                print(f"区域 {result_id} 修正匹配: {modified} (8→B 修正, 置信度: {confidence:.2f})")
                                all_matches.append({
                                    'region': result_id,
                                    'text': modified,
                                    'confidence': confidence,
                                    'fix': '8->B'
                                })

    print("\n所有匹配结果汇总:")
    for match in all_matches:
        print(
            f"- {match['text']} (来自区域 {match['region']}, 置信度 {match['confidence']:.2f})")



