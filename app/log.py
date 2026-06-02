from loguru import logger
import sys
import os
from pathlib import Path


def setup_logger():
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    logger.remove()
    
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO",
        colorize=True
    )
    
    logger.add(
        log_dir / "app_main.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="INFO",
        rotation="10 MB",
        retention="7 days",
        compression="zip",
        encoding="utf-8"
    )
    
    return logger


logger = setup_logger()


if __name__ == "__main__":
    try:
        logger.debug("This is a debug message")
        logger.info("This is an info message")
        logger.warning("This is a warning message")
        logger.error("This is an error message")
        logger.critical("This is a critical message")
    except Exception as e:
        logger.exception(f"Error occurred: {e}")