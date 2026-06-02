import os
from pathlib import Path
from configparser import ConfigParser

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings:
    DATABASE_ECHO: bool = False
    DEBUG: bool = False
    IMAGE_SAVE: bool = False

    @classmethod
    def from_env(cls):
        settings = cls()
        settings.DATABASE_ECHO = os.getenv("DATABASE_ECHO", "false").lower() == "true"
        settings.DEBUG = os.getenv("DEBUG", "false").lower() == "true"
        settings.IMAGE_SAVE = os.getenv("IMAGE_SAVE", "false").lower() == "true"
        return settings

    @classmethod
    def from_file(cls, config_path: str = None):
        if config_path is None:
            config_path = os.path.join(BASE_DIR, "app", "core", "config", "config.ini")
        
        settings = cls()
        
        if os.path.exists(config_path):
            config = ConfigParser()
            config.read(config_path, encoding='utf-8')
            
            settings.DATABASE_ECHO = config.getboolean("database", "echo", fallback=False)
            settings.DEBUG = config.getboolean("app", "debug", fallback=False)
            settings.IMAGE_SAVE = config.getboolean("image", "save", fallback=False)
        
        return settings


settings = Settings.from_file(r"E:\JJH\dhhi-insightcore\app\core\config\config.ini")
