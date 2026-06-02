import cv2
from app.core.config.settings import settings


def save_image(filepath: str, image, force: bool = False) -> bool:
    if settings.IMAGE_SAVE or force:
        try:
            cv2.imwrite(filepath, image)
            return True
        except Exception as e:
            print(f"保存图片失败 {filepath}: {e}")
            return False
    return False
