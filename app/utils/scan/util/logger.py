import logging
import os
from logging.handlers import TimedRotatingFileHandler

def set_logger():
    logger = logging.getLogger("scan")
    logger.setLevel(logging.INFO)

    consoleHandler = logging.StreamHandler()
    consoleHandler.setLevel(logging.INFO)

    # 日志文件路径
    log_file = os.path.join("./logs", "app.log")         # 路径需要修改
    fileHandler = TimedRotatingFileHandler(filename=log_file,
                                           when="midnight",  # 设置在每天午夜时创建新的日志文件
                                           interval=1,       # 表示每 1 个时间单位（在这里是天）创建一个新文件
                                           backupCount=5,
                                           encoding = 'utf-8')    # 保留最近5天的日志
    fileHandler.suffix = "%Y-%m-%d.log"  # 设置备份文件的后缀
    fileHandler.setLevel(logging.INFO)

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")

    consoleHandler.setFormatter(formatter)
    fileHandler.setFormatter(formatter)

    logger.addHandler(consoleHandler)
    logger.addHandler(fileHandler)

    return logger

scan_logger = set_logger()