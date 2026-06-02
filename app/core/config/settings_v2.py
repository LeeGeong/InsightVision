"""
集中化配置管理模块 V2

统一管理所有配置项，包括：
- 路径配置
- 相机配置
- 模型配置
- OCR 配置
- 应用配置

开发者: JJH
"""
import os
from pathlib import Path
from configparser import ConfigParser
from typing import Dict, Any, Optional
from dataclasses import dataclass, field


BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent


@dataclass
class PathConfig:
    """路径配置"""
    BASE_DIR: Path = BASE_DIR
    
    @property
    def MODELS_DIR(self) -> Path:
        return self.BASE_DIR / "app" / "models"
    
    @property
    def YOLO_MODEL_PATH(self) -> Path:
        return self.MODELS_DIR / "yolo" / "best.pt"
    
    @property
    def PERSPECTIVE_CONFIG_PATH(self) -> Path:
        return self.BASE_DIR / "app" / "cache" / "perspective_config.json"
    
    @property
    def OUTPUT_DIR(self) -> Path:
        return self.BASE_DIR / "app" / "static" / "output"
    
    @property
    def YOLO_OUTPUT_DIR(self) -> Path:
        return self.OUTPUT_DIR / "yolo_results"
    
    @property
    def LOG_DIR(self) -> Path:
        return self.BASE_DIR / "logs"
    
    @property
    def DATABASE_PATH(self) -> Path:
        return self.BASE_DIR / "app" / "database.db"
    
    def ensure_dirs(self):
        """确保所有必要目录存在"""
        for dir_path in [self.OUTPUT_DIR, self.YOLO_OUTPUT_DIR, self.LOG_DIR]:
            dir_path.mkdir(parents=True, exist_ok=True)


@dataclass
class CameraConfig:
    """相机配置"""
    DEFAULT_WIDTH: int = 1920
    DEFAULT_HEIGHT: int = 1080
    DEFAULT_FPS: int = 25
    CONNECTION_TIMEOUT: int = 10
    READ_TIMEOUT: int = 5
    
    PERSPECTIVE_PARAMS: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "192.168.3.70": {"width": 500, "height": 40700, "crop": (40700, 42370, 500, 2600)},
        "192.168.3.69": {"width": 600, "height": 40700, "crop": (40700, 42800, 600, 2600)},
        "192.168.3.71": {"width": 500, "height": 40700, "crop": (40700, 42800, 500, 2600)},
        "192.168.3.65": {"width": 500, "height": 40700, "crop": (40700, 42800, 500, 2600)},
        "192.168.3.68": {"width": 500, "height": 40700, "crop": (40700, 42800, 500, 2600)},
    })
    
    def get_perspective_params(self, ip: str) -> Dict[str, Any]:
        """获取指定 IP 的透视变换参数"""
        return self.PERSPECTIVE_PARAMS.get(ip, {
            "width": self.DEFAULT_WIDTH,
            "height": self.DEFAULT_HEIGHT,
            "crop": None
        })


@dataclass
class YoloConfig:
    """YOLO 模型配置"""
    CONFIDENCE_THRESHOLD: float = 0.3
    IOU_THRESHOLD: float = 0.3
    IMAGE_SIZE: int = 1024
    MAX_DETECTIONS: int = 1000
    USE_HALF: bool = False
    DEVICE: Optional[str] = None
    

@dataclass
class OCRConfig:
    """OCR 配置"""
    USE_GPU: bool = True
    USE_ANGLE_CLS: bool = True
    LANGUAGE: str = "en"
    DET_DB_THRESH: float = 0.3
    REC_BATCH_NUM: int = 6
    
    SPRAY_CODE_MIN_LENGTH: int = 8
    SPRAY_CODE_MAX_LENGTH: int = 12
    MATCH_CONFIDENCE_THRESHOLD: float = 0.75


@dataclass
class OllamaConfig:
    """Ollama 配置"""
    ENABLED: bool = True
    MODEL_NAME: str = "qwen3.5:27b"
    TIMEOUT: int = 60
    KEEP_ALIVE: int = -1
    TEMPERATURE: float = 0.0


@dataclass
class AppConfig:
    """应用配置"""
    DEBUG: bool = False
    DATABASE_ECHO: bool = False
    IMAGE_SAVE: bool = False
    API_PREFIX: str = "/api"
    API_TITLE: str = "智能视觉平台接口文档"
    API_VERSION: str = "1.0.0"
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8001
    WORKERS: int = 1


class Settings:
    """
    统一配置管理类
    
    使用方式:
        from app.core.config.settings_v2 import settings
        
        # 获取 YOLO 模型路径
        model_path = settings.paths.YOLO_MODEL_PATH
        
        # 获取相机配置
        camera_params = settings.camera.get_perspective_params("192.168.3.70")
        
        # 获取 OCR 配置
        ocr_threshold = settings.ocr.MATCH_CONFIDENCE_THRESHOLD
    """
    
    _instance: Optional["Settings"] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.paths = PathConfig()
        self.camera = CameraConfig()
        self.yolo = YoloConfig()
        self.ocr = OCRConfig()
        self.ollama = OllamaConfig()
        self.app = AppConfig()
        
        self._load_from_env()
        self._load_from_file()
        
        self.paths.ensure_dirs()
        self._initialized = True
    
    def _load_from_env(self):
        """从环境变量加载配置"""
        self.app.DEBUG = os.getenv("DEBUG", "false").lower() == "true"
        self.app.DATABASE_ECHO = os.getenv("DATABASE_ECHO", "false").lower() == "true"
        self.app.IMAGE_SAVE = os.getenv("IMAGE_SAVE", "false").lower() == "true"
        
        if os.getenv("OLLAMA_ENABLED"):
            self.ollama.ENABLED = os.getenv("OLLAMA_ENABLED", "true").lower() == "true"
        if os.getenv("OLLAMA_MODEL"):
            self.ollama.MODEL_NAME = os.getenv("OLLAMA_MODEL", self.ollama.MODEL_NAME)
    
    def _load_from_file(self, config_path: Optional[str] = None):
        """从配置文件加载配置"""
        if config_path is None:
            config_path = self.paths.BASE_DIR / "app" / "core" / "config" / "config.ini"
        
        if not Path(config_path).exists():
            return
        
        config = ConfigParser()
        config.read(config_path, encoding='utf-8')
        
        if config.has_section("app"):
            self.app.DEBUG = config.getboolean("app", "debug", fallback=self.app.DEBUG)
        
        if config.has_section("database"):
            self.app.DATABASE_ECHO = config.getboolean("database", "echo", fallback=self.app.DATABASE_ECHO)
        
        if config.has_section("image"):
            self.app.IMAGE_SAVE = config.getboolean("image", "save", fallback=self.app.IMAGE_SAVE)
        
        if config.has_section("yolo"):
            self.yolo.CONFIDENCE_THRESHOLD = config.getfloat("yolo", "confidence", fallback=self.yolo.CONFIDENCE_THRESHOLD)
            self.yolo.IOU_THRESHOLD = config.getfloat("yolo", "iou", fallback=self.yolo.IOU_THRESHOLD)
        
        if config.has_section("ocr"):
            self.ocr.MATCH_CONFIDENCE_THRESHOLD = config.getfloat("ocr", "match_threshold", fallback=self.ocr.MATCH_CONFIDENCE_THRESHOLD)
        
        if config.has_section("ollama"):
            self.ollama.ENABLED = config.getboolean("ollama", "enabled", fallback=self.ollama.ENABLED)
            self.ollama.MODEL_NAME = config.get("ollama", "model", fallback=self.ollama.MODEL_NAME)
    
    def get_database_url(self) -> str:
        """获取数据库连接 URL"""
        return f"sqlite:///{self.paths.DATABASE_PATH}"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于调试）"""
        return {
            "paths": {
                "base_dir": str(self.paths.BASE_DIR),
                "yolo_model": str(self.paths.YOLO_MODEL_PATH),
                "output_dir": str(self.paths.OUTPUT_DIR),
            },
            "camera": {
                "default_width": self.camera.DEFAULT_WIDTH,
                "default_height": self.camera.DEFAULT_HEIGHT,
            },
            "yolo": {
                "confidence": self.yolo.CONFIDENCE_THRESHOLD,
                "iou": self.yolo.IOU_THRESHOLD,
            },
            "ocr": {
                "match_threshold": self.ocr.MATCH_CONFIDENCE_THRESHOLD,
            },
            "ollama": {
                "enabled": self.ollama.ENABLED,
                "model": self.ollama.MODEL_NAME,
            },
            "app": {
                "debug": self.app.DEBUG,
            }
        }


settings = Settings()


if __name__ == "__main__":
    print("配置信息:")
    print(f"BASE_DIR: {settings.paths.BASE_DIR}")
    print(f"YOLO 模型路径: {settings.paths.YOLO_MODEL_PATH}")
    print(f"透视变换配置: {settings.paths.PERSPECTIVE_CONFIG_PATH}")
    print(f"输出目录: {settings.paths.OUTPUT_DIR}")
    print(f"数据库 URL: {settings.get_database_url()}")
    print(f"相机配置 (192.168.3.70): {settings.camera.get_perspective_params('192.168.3.70')}")
    print(f"YOLO 置信度阈值: {settings.yolo.CONFIDENCE_THRESHOLD}")
    print(f"OCR 匹配阈值: {settings.ocr.MATCH_CONFIDENCE_THRESHOLD}")
    print(f"Ollama 启用: {settings.ollama.ENABLED}")
    print(f"Ollama 模型: {settings.ollama.MODEL_NAME}")
