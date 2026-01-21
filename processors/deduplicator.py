"""
去重模块
策略: 内容哈希 + 时间窗口
"""

import hashlib
from typing import List, Dict, Any, Set
from datetime import datetime, timedelta
import logging

from config.config import Config

logger = logging.getLogger("processors.deduplicator")


class Deduplicator:
    """去重处理器"""

    def __init__(self, time_window_hours: int = None):
        """
        初始化去重器

        Args:
            time_window_hours: 时间窗口(小时),默认使用配置值
        """
        if time_window_hours is None:
            time_window_hours = Config.DEDUPLICATION_WINDOW_HOURS

        self.time_window = timedelta(hours=time_window_hours)
        self.seen_hashes: Set[str] = set()

    def deduplicate(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        去除重复记录

        Args:
            records: 数据记录列表

        Returns:
            去重后的记录列表
        """
        unique_records = []
        cutoff_time = datetime.now() - self.time_window

        for record in records:
            # 跳过数据类型(价格、指标)
            if record.get("type") in ["price_data", "economic_data", "fx_data"]:
                unique_records.append(record)
                continue

            # 生成内容哈希
            content = f"{record.get('title', '')}{record.get('summary', '')}"
            content_hash = hashlib.md5(content.encode("utf-8")).hexdigest()

            # 检查时间和哈希
            timestamp = record.get("timestamp", datetime.now())
            if isinstance(timestamp, str):
                try:
                    timestamp = datetime.fromisoformat(timestamp)
                except:
                    timestamp = datetime.now()

            if content_hash not in self.seen_hashes and timestamp > cutoff_time:
                self.seen_hashes.add(content_hash)
                unique_records.append(record)

        logger.info(f"去重完成: {len(records)} -> {len(unique_records)} 条")
        return unique_records

    def reset(self):
        """重置已见哈希(定期清理)"""
        self.seen_hashes.clear()
        logger.info("已重置去重缓存")
