"""
OCR 服务模块

统一管理 OCR 识别操作，包括：
- 喷码识别
- 模糊匹配
- 结果验证
- Ollama 二次识别

开发者: JJH
"""
import math
import time
from typing import Dict, Any, List, Tuple, Optional

import numpy as np
import pandas as pd

from app.log import logger
from app.core.config.settings_v2 import settings


class OCRError(Exception):
    """OCR 操作异常"""
    pass


class OCRResult:
    """OCR 识别结果"""
    
    def __init__(
        self,
        text: str = "",
        confidence: float = 0.0,
        box: List[List[int]] = None,
        status: str = "error",
        message: str = ""
    ):
        self.text = text
        self.confidence = confidence
        self.box = box or []
        self.status = status
        self.message = message
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "confidence": self.confidence,
            "box": self.box,
            "status": self.status,
            "message": self.message
    }


class SprayCodeMatcher:
    """
    喷码匹配器
    
    使用模糊匹配算法将 OCR 识别结果与有效喷码列表进行匹配
    """
    
    def __init__(self, valid_codes: List[str], threshold: float = None):
        """
        初始化匹配器

        Args:
            valid_codes: 有效喷码列表
            threshold: 匹配置信度阈值
        """
        self.valid_codes = valid_codes
        self.threshold = threshold or settings.ocr.MATCH_CONFIDENCE_THRESHOLD
    
    def match(self, text: str, top_k: int = 3) -> List[Tuple[str, float]]:
        """
        匹配喷码

        Args:
            text: OCR 识别文本
            top_k: 返回前 K 个匹配结果

        Returns:
            List[Tuple[str, float]]: [(喷码, 置信度), ...]
        """
        try:
            from app.utils.fuzzy_recongnition_claude_thinking import quick_match
            
            spray_codes = [{"mat_no": code} for code in self.valid_codes]
            matches = quick_match(text, spray_codes, top_k=top_k)
            
            return matches
            
        except Exception as e:
            logger.error(f"喷码匹配失败: {str(e)}")
            return []
    
    def find_best_match(self, text: str) -> Optional[Tuple[str, float]]:
        """
        找到最佳匹配

        Args:
            text: OCR 识别文本

        Returns:
            Optional[Tuple[str, float]]: (喷码, 置信度) 或 None
        """
        matches = self.match(text, top_k=1)
        
        if matches and matches[0][1] >= self.threshold:
            return matches[0]
        
        return None


class OCRService:
    """
    OCR 服务类
    
    统一管理 OCR 识别流程
    
    使用方式:
        ocr_service = OCRService()
        
        # 处理图像
        results = ocr_service.process_image(image)
        
        # 验证结果
        verified = ocr_service.verify_results(results, valid_codes)
    """
    
    def __init__(self, processor=None):
        self._processor = processor
        self._initialized = False
    
    def _ensure_processor(self):
        """确保 OCR 处理器已初始化"""
        if self._initialized:
            return
        
        if self._processor is None:
            try:
                from app.utils.fuzzy_recongnition_claude_thinking import SprayCodeOCRSystem
                self._processor = SprayCodeOCRSystem([])
            except Exception as e:
                logger.error(f"OCR 处理器初始化失败: {str(e)}")
        
        self._initialized = True
    
    def process_image(self, image: np.ndarray) -> Dict[str, Any]:
        """
        处理图像并返回 OCR 结果

        Args:
            image: 输入图像

        Returns:
            Dict: OCR 识别结果
        """
        self._ensure_processor()
        
        if self._processor is None:
            logger.error("OCR 处理器未初始化")
            return {}
        
        try:
            start_time = time.time()
            results = self._processor.process_image(image)
            elapsed = time.time() - start_time
            logger.info(f"OCR 处理耗时: {elapsed:.2f}s")
            
            return results
            
        except Exception as e:
            logger.error(f"OCR 处理失败: {str(e)}")
            return {}
    
    def verify_batch(
        self,
        results: Dict[str, Any],
        mat_infos_df: pd.DataFrame,
        image_data: bytes = None
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        验证 OCR 结果

        Args:
            results: OCR 识别结果
            mat_infos_df: 物料信息 DataFrame
            image_data: 图片数据（用于 Ollama 二次识别）

        Returns:
            Tuple[pd.DataFrame, Dict]: (匹配结果 DataFrame, 结果字典)
        """
        result_item = {
            "Ocr_Manufactor": "",
            "Ocr_BatchNo": "",
            "Ocr_Length": 0,
            "Ocr_Width": 0,
            "Ocr_Height": 0,
            "Ocr_Weight": 0,
            "Ocr_Code": "",
            "Priority": 0,
            "box": [],
            "status": "error",
            "message": "未找到有效喷码",
            "image_base64_detail": ""
        }
        
        return_df = pd.DataFrame()
        
        if not results:
            # OCR 无结果，尝试 Ollama
            if image_data:
                return self._try_ollama(image_data, mat_infos_df, result_item)
            return return_df, result_item
        
        valid_codes = mat_infos_df['mat_no'].tolist()
        matcher = SprayCodeMatcher(valid_codes)
        
        for result_key, result_data in results.items():
            coordinates = result_data.get('coordinates', [])
            ocr_results = result_data.get('ocr_result', [])
            
            if not ocr_results or ocr_results[0] is None:
                continue
            
            for r in ocr_results[0]:
                text = r[1][0] if r[1] else ""
                
                if len(text) < settings.ocr.SPRAY_CODE_MIN_LENGTH:
                    continue
                
                match_result = matcher.find_best_match(text)
                
                if match_result:
                    best_match, best_confidence = match_result
                    logger.info(f"OCR文本: {text}, 最佳匹配: {best_match}, 置信度: {best_confidence:.2%}")
                    
                    matched_row = mat_infos_df[mat_infos_df["mat_no"] == best_match].iloc[0].copy()
                    
                    points = coordinates
                    x_sum = sum(point[0] for point in points)
                    y_sum = sum(point[1] for point in points)
                    n = len(points)
                    midpoint = (x_sum / n, y_sum / n)
                    distance = math.sqrt((midpoint[0] - 1920) ** 2 + (midpoint[1] - 1080) ** 2)
                    
                    matched_row['distance'] = distance
                    matched_row['confidence'] = best_confidence
                    
                    return_df = pd.concat([return_df, pd.DataFrame([matched_row])], ignore_index=True)
        
        if not return_df.empty:
            return_df = self._rank_results(return_df)
            result_item["Ocr_BatchNo"] = return_df["mat_no"].values[0]
            result_item.update({
                "status": "success",
                "message": "喷码验证成功"
            })
        elif image_data:
            return self._try_ollama(image_data, mat_infos_df, result_item)
        
        return return_df, result_item
    
    def _rank_results(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        对结果进行排序和筛选

        Args:
            df: 结果 DataFrame

        Returns:
            pd.DataFrame: 排序后的结果
        """
        if df.empty:
            return df
        
        df = df.drop_duplicates(subset=['mat_no'])
        df['mat_area'] = df['mat_length'] * df['mat_width']
        
        max_distance = df['distance'].max()
        if max_distance > 0:
            df['distance_score'] = 1 - (df['distance'] / max_distance)
        else:
            df['distance_score'] = 1.0
        
        df['total_score'] = 0.7 * df['confidence'] + 0.3 * df['distance_score']
        df = df.sort_values(by='total_score', ascending=False)
        df = df.head(1)
        
        return df
    
    def _try_ollama(
        self,
        image_data: bytes,
        mat_infos_df: pd.DataFrame,
        result_item: Dict[str, Any]
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        尝试使用 Ollama 进行二次识别

        Args:
            image_data: 图片数据
            mat_infos_df: 物料信息 DataFrame
            result_item: 结果字典

        Returns:
            Tuple[pd.DataFrame, Dict]: (结果 DataFrame, 结果字典)
        """
        logger.info("OCR 未匹配到有效喷码，尝试 Ollama 二次识别")
        
        try:
            from app.core.services.ollama_service import get_ollama_spray_code, OLLAMA_AVAILABLE
            
            if not OLLAMA_AVAILABLE:
                logger.warning("Ollama 不可用，跳过二次识别")
                return pd.DataFrame(), result_item
            
            valid_codes = mat_infos_df['mat_no'].tolist()
            spray_code, in_list = get_ollama_spray_code(image_data, valid_codes)
            
            if spray_code and in_list:
                logger.info(f"Ollama 二次识别成功: {spray_code}")
                matched_row = mat_infos_df[mat_infos_df["mat_no"] == spray_code].iloc[0].copy()
                matched_row['distance'] = 0
                matched_row['confidence'] = 0.95
                
                result_item["Ocr_BatchNo"] = spray_code
                result_item.update({
                    "status": "success",
                    "message": "Ollama 二次识别成功"
                })
                
                return pd.DataFrame([matched_row]), result_item
            
            elif spray_code and not in_list:
                logger.info(f"Ollama 识别到喷码 {spray_code} 但不在有效列表中")
                result_item["Ocr_BatchNo"] = spray_code
                result_item.update({
                    "status": "error",
                    "message": f"识别结果 {spray_code} 不在有效列表中"
                })
            
            else:
                logger.info("Ollama 二次识别也未找到有效喷码")
                result_item.update({
                    "status": "error",
                    "message": "未找到有效喷码（OCR 和 Ollama 均失败）"
                })
            
        except Exception as e:
            logger.error(f"Ollama 二次识别异常: {str(e)}")
            result_item.update({
                "status": "error",
                "message": f"Ollama 识别异常: {str(e)}"
            })
        
        return pd.DataFrame(), result_item


class YoloDetectionService:
    """
    YOLO 检测服务
    
    统一管理 YOLO 检测操作
    """
    
    _model = None
    
    @classmethod
    def _ensure_model(cls):
        """确保模型已加载"""
        if cls._model is None:
            try:
                from ultralytics import YOLO
                model_path = settings.paths.YOLO_MODEL_PATH
                
                if model_path.exists():
                    cls._model = YOLO(str(model_path))
                    logger.info(f"YOLO 模型加载成功: {model_path}")
                else:
                    logger.warning(f"YOLO 模型文件不存在: {model_path}")
            except Exception as e:
                logger.error(f"YOLO 模型加载失败: {str(e)}")
    
    @classmethod
    def detect(
        cls,
        image: np.ndarray,
        confidence: float = None,
        iou: float = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        执行 YOLO 检测

        Args:
            image: 输入图像
            confidence: 置信度阈值
            iou: IOU 阈值

        Returns:
            List[Dict]: 检测结果列表
        """
        cls._ensure_model()
        
        if cls._model is None:
            logger.error("YOLO 模型未加载")
            return []
        
        confidence = confidence or settings.yolo.CONFIDENCE_THRESHOLD
        iou = iou or settings.yolo.IOU_THRESHOLD
        
        try:
            results = cls._model.predict(
                source=image,
                conf=confidence,
                iou=iou,
                imgsz=settings.yolo.IMAGE_SIZE,
                half=settings.yolo.USE_HALF,
                device=settings.yolo.DEVICE,
                max_det=settings.yolo.MAX_DETECTIONS,
                verbose=False
            )
            
            detections = []
            for result in results:
                for obb in result.obb:
                    cls_id = obb.cls.item()
                    if cls_id != 0:
                        continue
                    
                    cx, cy, w, h, angle = obb.xywhr[0, :5].tolist()
                    rect = ((cx, cy), (w, h), np.degrees(angle))
                    box_points = cv2.boxPoints(rect).astype(int).tolist()
                    
                    detections.append({
                        "confidence": obb.conf.item(),
                        "box_points": box_points,
                        "center": [int(cx), int(cy)],
                        "short_side": min(w, h),
                        "long_side": max(w, h),
                        "angle": np.degrees(angle),
                        "class": cls_id
                    })
            
            return detections
            
        except Exception as e:
            logger.error(f"YOLO 检测失败: {str(e)}")
            return []


def get_ocr_service() -> OCRService:
    """依赖注入：获取 OCR 服务实例"""
    return OCRService()


if __name__ == "__main__":
    print("OCR 服务模块")
    print("=" * 50)
    print("主要功能:")
    print("  - OCRService: OCR 识别和验证")
    print("  - SprayCodeMatcher: 喷码模糊匹配")
    print("  - YoloDetectionService: YOLO 检测")
    print()
    print("使用示例:")
    print("  ocr_service = OCRService()")
    print("  results = ocr_service.process_image(image)")
