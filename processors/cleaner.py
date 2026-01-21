"""
数据清洗模块
功能: 关键词过滤、HTML清理、文本规范化
"""

import re
from typing import List, Dict, Any
import logging

try:
    from bs4 import BeautifulSoup

    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

from config.config import Config

logger = logging.getLogger("processors.cleaner")


class DataCleaner:
    """数据清洗器"""

    def __init__(self):
        self.whitelist = [kw.lower() for kw in Config.WHITELIST_KEYWORDS]
        self.blacklist = [kw.lower() for kw in Config.BLACKLIST_KEYWORDS]

    def clean(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        清洗数据记录

        Args:
            records: 原始数据记录列表

        Returns:
            清洗后的数据记录列表
        """
        cleaned = []

        for record in records:
            # 跳过价格数据(不需要关键词过滤)
            if record.get("type") in ["price_data", "economic_data", "fx_data"]:
                cleaned.append(record)
                continue

            # 清理HTML
            if "title" in record:
                record["title"] = self._strip_html(record["title"])
            if "summary" in record:
                record["summary"] = self._strip_html(record["summary"])

            # 关键词过滤
            if self._should_keep(record):
                # 标记影响方向
                record["impact_tag"] = self._tag_impact(record)
                cleaned.append(record)

        logger.info(f"清洗完成: {len(records)} -> {len(cleaned)} 条记录")
        return cleaned

    def _strip_html(self, text: str) -> str:
        """
        去除HTML标签

        Args:
            text: 可能包含HTML的文本

        Returns:
            纯文本
        """
        if not text:
            return ""

        if BS4_AVAILABLE:
            soup = BeautifulSoup(text, "html.parser")
            return soup.get_text(separator=" ", strip=True)
        else:
            # 简单的正则替换
            text = re.sub(r"<[^>]+>", "", text)
            return text.strip()

    def _should_keep(self, record: Dict) -> bool:
        """
        判断是否保留记录(基于关键词)

        Args:
            record: 数据记录

        Returns:
            是否保留
        """
        text = f"{record.get('title', '')} {record.get('summary', '')}".lower()

        # 黑名单过滤
        for keyword in self.blacklist:
            if keyword in text:
                logger.debug(f"黑名单过滤: {keyword} in {record.get('title', '')[:50]}")
                return False

        # 白名单匹配
        for keyword in self.whitelist:
            if keyword in text:
                return True

        # 默认保留(可根据需求调整为False)
        return True

    def _tag_impact(self, record: Dict) -> str:
        """
        标记影响方向(简化版)

        Args:
            record: 数据记录

        Returns:
            影响标签
        """
        text = f"{record.get('title', '')} {record.get('summary', '')}".lower()

        bullish_signals = [
            "demand",
            "buying",
            "rally",
            "surge",
            "safe-haven",
            "purchase",
            "accumulation",
            "bullish",
            "rise",
            "gain",
        ]
        bearish_signals = [
            "sell",
            "drop",
            "decline",
            "yield rise",
            "dollar strength",
            "bearish",
            "fall",
            "loss",
            "weak",
            "pressure",
        ]

        bullish_count = sum(1 for s in bullish_signals if s in text)
        bearish_count = sum(1 for s in bearish_signals if s in text)

        if bullish_count > bearish_count:
            return "#Bullish"
        elif bearish_count > bullish_count:
            return "#Bearish"
        return "#Neutral"
