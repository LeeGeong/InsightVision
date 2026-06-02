import cv2
import numpy as np
from paddleocr import PaddleOCR
from typing import List, Dict, Tuple, Optional
from difflib import SequenceMatcher
from app.utils.fuzzy_recognition_claude import AdvancedSprayCodeMatcher, SprayCodeMatcher
import logging
import time
from functools import wraps

logger = logging.getLogger(__name__)


def timing_decorator(func):
    """运行时间统计装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        elapsed_time = (end_time - start_time) * 1000  # 转换为毫秒
        logger.debug(f"{func.__name__} 执行时间: {elapsed_time:.2f}ms")
        return result
    return wrapper


class SprayCodeOCRSystem:
    """完整的喷码OCR识别与匹配系统"""

    def __init__(self, spray_codes: List[Dict[str, str]]):
        """
        初始化系统

        Args:
            spray_codes: 喷码列表
        """
        # 初始化OCR
        self.ocr = PaddleOCR(
            use_angle_cls=True,
            lang='en',
            use_gpu=True,
            det_db_thresh=0.3,
            rec_batch_num=6
        )

        # 初始化匹配器
        self.matcher = AdvancedSprayCodeMatcher(spray_codes)

        # 历史记录（用于提高准确率）
        self.history = {}

    @timing_decorator
    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """图像预处理"""
        if image is None or image.size == 0:
            raise ValueError("输入图像为空")

        # 转灰度
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # 确保图像不为空
        if gray.size == 0:
            raise ValueError("灰度转换失败")

        # 对比度增强
        try:
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
        except cv2.error:
            enhanced = gray

        # 去噪
        try:
            denoised = cv2.fastNlMeansDenoising(enhanced, None, 10, 7, 21)
        except cv2.error:
            denoised = enhanced

        # 二值化
        try:
            _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        except cv2.error:
            binary = denoised

        # 形态学操作
        try:
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
            processed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        except cv2.error:
            processed = binary

        return processed

    @timing_decorator
    def extract_spray_code_region(self, image: np.ndarray) -> List[np.ndarray]:
        """提取喷码区域"""
        if image is None or image.size == 0:
            return []

        # 使用OCR检测文本区域
        try:
            result = self.ocr.ocr(image, cls=True)
        except Exception as e:
            logger.error(f"OCR检测失败: {e}")
            return []

        regions = []
        if result and result[0]:
            for line in result[0]:
                try:
                    box = line[0]
                    # 提取区域
                    x_coords = [p[0] for p in box]
                    y_coords = [p[1] for p in box]
                    x_min, x_max = int(min(x_coords)), int(max(x_coords))
                    y_min, y_max = int(min(y_coords)), int(max(y_coords))

                    # 添加边距
                    padding = 5
                    x_min = max(0, x_min - padding)
                    y_min = max(0, y_min - padding)
                    x_max = min(image.shape[1], x_max + padding)
                    y_max = min(image.shape[0], y_max + padding)

                    # 确保区域有效
                    if x_max > x_min and y_max > y_min:
                        region = image[y_min:y_max, x_min:x_max]
                        if region.size > 0:
                            regions.append(region)
                except (IndexError, ValueError, TypeError) as e:
                    logger.warning(f"提取区域失败: {e}")
                    continue

        return regions

    @timing_decorator
    def recognize_and_match(self, image: np.ndarray,
                            confidence_threshold: float = 0.6) -> Dict:
        """
        识别并匹配喷码

        Args:
            image: 输入图像
            confidence_threshold: 置信度阈值

        Returns:
            {
                'ocr_text': OCR识别文本,
                'matched_code': 匹配的喷码,
                'confidence': 置信度,
                'alternatives': 备选结果,
                'image_quality': 图像质量评分
            }
        """
        if image is None or image.size == 0:
            return {
                'ocr_text': '',
                'matched_code': None,
                'confidence': 0.0,
                'alternatives': [],
                'image_quality': 0.0,
                'details': {}
            }

        try:
            # 评估图像质量
            image_quality = self._assess_image_quality(image)

            # 预处理
            processed = self.preprocess_image(image)

            # 多次OCR识别（使用不同参数）
            ocr_results = self._multi_ocr(processed)

            # 合并OCR结果
            merged_text = self._merge_ocr_results(ocr_results)

            # 匹配喷码
            context = {
                'image_quality': image_quality,
                'history': self.history
            }

            best_match, confidence, details = self.matcher.smart_match(merged_text, context)
            alternatives = self.matcher.find_best_match(merged_text, top_k=3)

            # 更新历史记录
            if confidence > confidence_threshold:
                self.history[best_match] = self.history.get(best_match, 0) + 1

            return {
                'ocr_text': merged_text,
                'matched_code': best_match if confidence > confidence_threshold else None,
                'confidence': confidence,
                'alternatives': alternatives,
                'image_quality': image_quality,
                'details': details
            }
        except Exception as e:
            logger.error(f"识别匹配失败: {e}")
            return {
                'ocr_text': '',
                'matched_code': None,
                'confidence': 0.0,
                'alternatives': [],
                'image_quality': 0.0,
                'details': {}
            }

    def _assess_image_quality(self, image: np.ndarray) -> float:
        """评估图像质量"""
        if image is None or image.size == 0:
            return 0.0

        try:
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image

            # 拉普拉斯方差（清晰度）
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            sharpness = min(laplacian_var / 500, 1.0)

            # 对比度
            contrast = gray.std() / 128
            contrast = min(contrast, 1.0)

            # 亮度
            brightness = gray.mean() / 255
            brightness_score = 1 - abs(brightness - 0.5) * 2

            # 综合评分
            quality = sharpness * 0.4 + contrast * 0.3 + brightness_score * 0.3

            return max(0.0, min(1.0, quality))
        except Exception as e:
            logger.error(f"图像质量评估失败: {e}")
            return 0.5

    @timing_decorator
    def _multi_ocr(self, image: np.ndarray) -> List[str]:
        """多参数OCR识别"""
        results = []

        if image is None or image.size == 0:
            return results

        # 原始图像OCR
        try:
            result1 = self.ocr.ocr(image, cls=True)
            if result1 and result1[0]:
                for line in result1[0]:
                    text = line[1][0]
                    results.append(text)
        except Exception as e:
            logger.warning(f"原始图像OCR失败: {e}")

        # 反色图像OCR
        try:
            inverted = cv2.bitwise_not(image)
            result2 = self.ocr.ocr(inverted, cls=True)
            if result2 and result2[0]:
                for line in result2[0]:
                    text = line[1][0]
                    results.append(text)
        except Exception as e:
            logger.warning(f"反色图像OCR失败: {e}")

        # 不同缩放比例
        for scale in [1.5, 2.0]:
            try:
                scaled = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
                result = self.ocr.ocr(scaled, cls=True)
                if result and result[0]:
                    for line in result[0]:
                        text = line[1][0]
                        results.append(text)
            except Exception as e:
                logger.warning(f"缩放图像OCR失败(scale={scale}): {e}")

        return results

    def _merge_ocr_results(self, results: List[str]) -> str:
        """合并多次OCR结果"""
        if not results:
            return ""

        # 预处理所有结果
        cleaned = []
        for text in results:
            if not text:
                continue
            clean_text = ''.join(c for c in text if c.isalnum()).upper()
            if len(clean_text) >= 8:  # 喷码通常至少8位
                cleaned.append(clean_text)

        if not cleaned:
            # 如果没有符合条件的清理结果，返回第一个有效结果
            for text in results:
                if text:
                    return ''.join(c for c in text if c.isalnum()).upper()
            return ""

        # 使用投票机制选择最佳结果
        # 计算每个结果与其他结果的平均相似度
        best_result = None
        best_score = -1

        for candidate in cleaned:
            total_similarity = 0
            for other in cleaned:
                if candidate != other:
                    similarity = SequenceMatcher(None, candidate, other).ratio()
                    total_similarity += similarity

            avg_similarity = total_similarity / (len(cleaned) - 1) if len(cleaned) > 1 else 1

            if avg_similarity > best_score:
                best_score = avg_similarity
                best_result = candidate

        return best_result or cleaned[0]


# 实时处理系统
class RealTimeSprayCodeSystem:
    """实时喷码识别系统"""

    def __init__(self, spray_codes: List[Dict[str, str]]):
        self.ocr_system = SprayCodeOCRSystem(spray_codes)
        self.results_buffer = []
        self.max_buffer_size = 10

    def process_frame(self, frame: np.ndarray) -> Dict:
        """处理单帧图像"""
        if frame is None or frame.size == 0:
            return {
                'current': {
                    'ocr_text': '',
                    'matched_code': None,
                    'confidence': 0.0,
                    'alternatives': [],
                    'image_quality': 0.0,
                    'details': {}
                },
                'stable': None,
                'processing_time': 0.0
            }

        start_time = time.time()
        try:
            result = self.ocr_system.recognize_and_match(frame)

            # 添加到缓冲区
            self.results_buffer.append(result)
            if len(self.results_buffer) > self.max_buffer_size:
                self.results_buffer.pop(0)

            # 使用缓冲区数据提高准确率
            stable_result = self._get_stable_result()

            end_time = time.time()
            processing_time = (end_time - start_time) * 1000  # 转换为毫秒

            return {
                'current': result,
                'stable': stable_result,
                'processing_time': processing_time
            }
        except Exception as e:
            logger.error(f"处理帧失败: {e}")
            end_time = time.time()
            processing_time = (end_time - start_time) * 1000
            return {
                'current': {
                    'ocr_text': '',
                    'matched_code': None,
                    'confidence': 0.0,
                    'alternatives': [],
                    'image_quality': 0.0,
                    'details': {}
                },
                'stable': None,
                'processing_time': processing_time
            }

    def _get_stable_result(self) -> Optional[str]:
        """从缓冲区获取稳定结果"""
        if len(self.results_buffer) < 3:
            return None

        # 统计最近N帧的匹配结果
        code_counts = {}
        for result in self.results_buffer[-5:]:
            if result['matched_code'] and result['confidence'] > 0.7:
                code = result['matched_code']
                code_counts[code] = code_counts.get(code, 0) + 1

        # 返回出现次数最多的
        if code_counts:
            stable_code = max(code_counts.items(), key=lambda x: x[1])
            if stable_code[1] >= 2:  # 至少出现2次
                return stable_code[0]

        return None

    def run_video_stream(self, video_source=0):
        """运行视频流处理"""
        cap = cv2.VideoCapture(video_source)

        if not cap.isOpened():
            logger.error(f"无法打开视频源: {video_source}")
            return

        logger.info("按 'q' 退出")

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    logger.warning("无法读取帧，退出")
                    break

                # 处理帧
                result = self.process_frame(frame)

                # 显示结果
                display_frame = frame.copy()

                # 添加文本
                current = result['current']
                stable = result['stable']
                processing_time = result.get('processing_time', 0.0)

                y_offset = 30
                cv2.putText(display_frame, f"OCR: {current['ocr_text']}",
                            (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

                y_offset += 30
                if current['matched_code']:
                    color = (0, 255, 0) if current['confidence'] > 0.8 else (0, 255, 255)
                    cv2.putText(display_frame,
                                f"Match: {current['matched_code']} ({current['confidence']:.1%})",
                                (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

                y_offset += 30
                if stable:
                    cv2.putText(display_frame, f"Stable: {stable}",
                                (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

                # 显示图像质量
                y_offset += 30
                quality = current['image_quality']
                quality_color = (0, 255, 0) if quality > 0.7 else (0, 255, 255) if quality > 0.5 else (0, 0, 255)
                cv2.putText(display_frame, f"Quality: {quality:.1%}",
                            (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, quality_color, 2)

                # 显示处理时间
                y_offset += 30
                time_color = (0, 255, 0) if processing_time < 100 else (0, 255, 255) if processing_time < 200 else (0, 0, 255)
                cv2.putText(display_frame, f"Time: {processing_time:.1f}ms",
                            (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, time_color, 2)

                cv2.imshow('Spray Code Recognition', display_frame)

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        except KeyboardInterrupt:
            logger.info("用户中断")
        except Exception as e:
            logger.error(f"视频流处理错误: {e}")
        finally:
            cap.release()
            cv2.destroyAllWindows()


# 简化版快速匹配函数
@timing_decorator
def quick_match(ocr_text: str, spray_codes: List[Dict[str, str]],
                top_k: int = 1) -> List[Tuple[str, float]]:
    """
    快速匹配函数

    Args:
        ocr_text: OCR识别的文本
        spray_codes: 喷码列表
        top_k: 返回前k个结果

    Returns:
        [(匹配的喷码, 置信度), ...]
    """
    if not ocr_text or not spray_codes:
        return []

    try:
        matcher = SprayCodeMatcher(spray_codes)
        results = matcher.find_best_match(ocr_text, top_k=top_k)
        return [(code, score) for code, score, _ in results]
    except Exception as e:
        logger.error(f"快速匹配失败: {e}")
        return []


# 使用示例
if __name__ == "__main__":
    import logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 您的喷码数据
    spray_codes = [
        {'mat_no': '5C31401130'},
        {'mat_no': '5C31401140'},
        {'mat_no': '6113162100'},
        {'mat_no': '6117206200'},
        {'mat_no': '6117077200'},
        {'mat_no': '6112394500'},
        {'mat_no': '6116266100'},
        {'mat_no': '6117193100'},
        {'mat_no': '6116266200'},
        {'mat_no': '6118146600'},
        {'mat_no': '6118146300'},
        {'mat_no': '6117192300'},
        {'mat_no': '6118137300'},
        {'mat_no': '6115059200'},
        {'mat_no': '6118137500'},
        {'mat_no': '6118278100'},
        {'mat_no': '6118137600'},
        {'mat_no': '6118146500'},
        {'mat_no': '6118137200'},
        {'mat_no': '6118146200'},
        {'mat_no': '6118277100'},
        {'mat_no': '6106173300'},
        {'mat_no': '6114132300'}
    ]

    print("=" * 60)
    print("快速匹配演示（带时间统计）")
    print("=" * 60)

    # 快速使用
    ocr_result = "611814660O"  # 模拟OCR结果
    matches = quick_match(ocr_result, spray_codes, top_k=3)

    print(f"\nOCR结果: {ocr_result}")
    print("匹配结果:")
    for code, confidence in matches:
        print(f"  {code}: {confidence:.1%}")

    print("\n" + "=" * 60)
    print("批量匹配演示（带时间统计）")
    print("=" * 60)

    # 批量测试多个OCR结果
    test_cases = [
        "5C3140113O",  # 最后一位0识别成O
        "6II3I62I00",  # 多个1识别成I
        "SC31401140",  # 5识别成S
        "6118137Z00",  # 2识别成Z
    ]

    for i, ocr_text in enumerate(test_cases, 1):
        print(f"\n测试 {i}: {ocr_text}")
        matches = quick_match(ocr_text, spray_codes, top_k=1)
        if matches:
            best_match, confidence = matches[0]
            print(f"  最佳匹配: {best_match} (置信度: {confidence:.1%})")
        else:
            print("  未找到匹配")

    print("\n" + "=" * 60)
    print("性能测试（100次匹配）")
    print("=" * 60)

    import time as time_module
    start_time = time_module.time()
    for _ in range(100):
        quick_match("611814660O", spray_codes, top_k=1)
    end_time = time_module.time()
    total_time = (end_time - start_time) * 1000
    avg_time = total_time / 100

    print(f"\n总耗时: {total_time:.2f}ms")
    print(f"平均耗时: {avg_time:.2f}ms")
    print(f"吞吐量: {1000 / avg_time:.1f} 次/秒")