"""
Ollama 喷码识别服务

使用 Ollama 大模型进行喷码识别，作为 OCR 识别失败后的备选方案
"""
import base64
import time
from typing import Optional, Tuple

from pydantic import BaseModel

from app.log import logger

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    logger.warning("ollama 模块未安装，Ollama 识别功能将不可用")


class SprayCodeResult(BaseModel):
    """喷码识别结果模型"""
    has_spray_code: bool
    spray_code: str
    in_list: bool


def recognize_spray_code_with_ollama(
    image_data: bytes,
    valid_mat_nos: list,
    model_name: str = "qwen3.5:27b"
) -> Tuple[Optional[str], bool]:
    """
    使用 Ollama 识别喷码
    
    Args:
        image_data: 图片数据（bytes 格式）
        valid_mat_nos: 有效的喷码列表
        model_name: Ollama 模型名称
        
    Returns:
        Tuple[Optional[str], bool]: (识别到的喷码, 是否在有效列表中)
    """
    if not OLLAMA_AVAILABLE:
        logger.warning("Ollama 不可用，跳过 Ollama 识别")
        return None, False
    
    try:
        start_time = time.time()
        
        prompt = f'''请识别图中是否有一个十位由数字和大写英文字母组成的喷码，喷码不含特殊字符和符号，完全由数字和大写英文字母组成。

有效的喷码列表如下：{valid_mat_nos}

请严格按照JSON格式返回，必须包含以下三个字段：
- has_spray_code: 布尔值，表示是否找到喷码
- spray_code: 字符串，喷码内容（如果没有则返回空字符串）
- in_list: 布尔值，表示喷码是否在有效列表中

如果识别到的喷码在有效列表中，in_list返回true，否则返回false。
如果图中没有喷码，spray_code返回空字符串，in_list返回false。
此次请求不涉及上下文，不需要阅读上下文。'''

        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
            tmp_file.write(image_data)
            tmp_path = tmp_file.name
        
        try:
            response = ollama.chat(
                model=model_name,
                messages=[
                    {
                        'role': 'user',
                        'content': prompt,
                        'images': [tmp_path],
                    },
                ],
                format=SprayCodeResult.model_json_schema(),
                options={
                    'temperature': 0,
                },
                keep_alive=-1,
                think=False,
                stream=False,
            )
            
            elapsed_time = time.time() - start_time
            logger.info(f"Ollama 识别耗时: {elapsed_time:.2f} 秒")
            
            if response and response.get('message'):
                content = response['message'].get('content', '')
                
                import re
                json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
                if json_match:
                    content = json_match.group(1).strip()
                
                result = SprayCodeResult.model_validate_json(content)
                
                logger.info(
                    f"Ollama 识别结果: has_spray_code={result.has_spray_code}, "
                    f"spray_code={result.spray_code}, in_list={result.in_list}"
                )
                
                if result.has_spray_code and result.spray_code:
                    return result.spray_code, result.in_list
                    
        finally:
            import os
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
                
    except Exception as e:
        logger.error(f"Ollama 识别异常: {str(e)}")
        import traceback
        traceback.print_exc()
    
    return None, False


def get_ollama_spray_code(
    image_data: bytes,
    valid_mat_nos: list,
    model_name: str = "qwen3.5:27b"
) -> Tuple[Optional[str], bool]:
    """
    使用 Ollama 识别喷码并返回喷码字符串
    
    Args:
        image_data: 图片数据（bytes 格式）
        valid_mat_nos: 有效的喷码列表
        model_name: Ollama 模型名称
        
    Returns:
        Tuple[Optional[str], bool]: (识别到的喷码字符串, 是否在有效列表中)
    """
    return recognize_spray_code_with_ollama(image_data, valid_mat_nos, model_name)


def get_ollama_results(
    image_data: bytes,
    valid_mat_nos: list,
    model_name: str = "qwen3.5:27b"
) -> dict:
    """
    使用 Ollama 识别喷码并返回与 OCR 结果兼容的格式
    
    Args:
        image_data: 图片数据（bytes 格式）
        valid_mat_nos: 有效的喷码列表
        model_name: Ollama 模型名称
        
    Returns:
        dict: 模拟 OCR 结果的字典格式
    """
    spray_code, in_list = recognize_spray_code_with_ollama(image_data, valid_mat_nos, model_name)
    
    if spray_code:
        return {
            "ollama_region": {
                "coordinates": [[0, 0], [100, 0], [100, 50], [0, 50]],
                "ocr_result": [
                    [
                        [
                            None,
                            [[None, (spray_code, 0.95)]],
                            None
                        ]
                    ]
                ]
            }
        }
    
    return {}
