"""
日志配置模块
支持: 彩色输出、文件记录、日志轮转
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from config.config import Config


def setup_logger():
    """
    配置全局日志系统

    特性:
    - 彩色控制台输出
    - 每日日志文件
    - 统一格式化
    """
    # 日志文件路径
    log_file = Config.LOG_DIR / f"finnews_{datetime.now().strftime('%Y%m%d')}.log"

    # 创建格式化器
    file_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)-8s] %(name)-20s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s", datefmt="%H:%M:%S"
    )

    # 文件处理器
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)

    # 配置根日志
    root_logger = logging.getLogger()
    root_logger.setLevel(Config.LOG_LEVEL)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # 创建主日志
    logger = logging.getLogger("FinNews")
    logger.info("=" * 60)
    logger.info("FinNews 日志系统已初始化")
    logger.info(f"日志文件: {log_file}")
    logger.info(f"日志级别: {Config.LOG_LEVEL}")
    logger.info("=" * 60)

    return logger


def get_logger(name: str):
    """获取指定名称的日志器"""
    return logging.getLogger(name)
