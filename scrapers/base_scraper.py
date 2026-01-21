"""
基础爬虫抽象类
所有爬虫继承此类,实现统一接口
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional


class BaseScraper(ABC):
    """
    所有爬虫的基类

    提供:
    - 统一的日志接口
    - 标准化的数据记录格式
    - 统一的错误处理
    """

    def __init__(self, name: str):
        """
        初始化爬虫

        Args:
            name: 爬虫名称,用于日志标识
        """
        self.name = name
        self.logger = logging.getLogger(f"scrapers.{name}")

    @abstractmethod
    def fetch(self) -> List[Dict[str, Any]]:
        """
        抓取数据的抽象方法(必须由子类实现)

        Returns:
            新闻/数据字典列表
        """
        pass

    def _create_base_record(
        self,
        title: str,
        summary: str,
        url: str,
        timestamp: Optional[datetime] = None,
        *,
        record_type: str = "news",
        fallback_allowed: bool = False,
    ) -> Dict[str, Any]:
        """
        创建标准化数据记录

        Args:
            title: 标题
            summary: 摘要
            url: 链接
            timestamp: 发布时间
            record_type: 记录类型
            fallback_allowed: 是否允许窗口外回退

        Returns:
            标准化数据字典
        """
        return {
            "source": self.name,
            "title": title,
            "summary": summary,
            "url": url,
            "timestamp": timestamp or datetime.now(),
            "fetched_at": datetime.now(),
            "impact_tag": None,  # 后续由processor填充
            "type": record_type,
            "fallback_allowed": fallback_allowed,
        }

    @staticmethod
    def _parse_record_timestamp(value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except Exception:
                return datetime.now()
        return datetime.now()

    def _filter_recent_records(
        self,
        records: List[Dict[str, Any]],
        window_hours: int,
        *,
        allow_fallback: bool = False,
        fallback_note: Optional[str] = None,
        daily_label: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if not records:
            return []

        if daily_label:
            for record in records:
                record["daily_label"] = daily_label

        cutoff_time = datetime.now() - timedelta(hours=window_hours)
        recent_records = [
            record
            for record in records
            if self._parse_record_timestamp(record.get("timestamp")) >= cutoff_time
        ]
        if recent_records:
            return recent_records

        if allow_fallback:
            latest = max(
                records,
                key=lambda record: self._parse_record_timestamp(
                    record.get("timestamp")
                ),
            )
            latest["fallback_allowed"] = True
            if fallback_note:
                latest["fallback_note"] = fallback_note
            return [latest]

        return []

    def run(self) -> List[Dict[str, Any]]:
        """
        执行抓取流程(带错误处理)

        Returns:
            数据记录列表
        """
        try:
            self.logger.info(f"开始抓取...")
            data = self.fetch()
            self.logger.info(f"成功抓取 {len(data)} 条记录")
            return data
        except Exception as e:
            self.logger.error(f"抓取失败: {e}", exc_info=True)
            return []
