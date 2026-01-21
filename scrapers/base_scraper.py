"""
基础爬虫抽象类
所有爬虫继承此类,实现统一接口
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Any


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
        self, title: str, summary: str, url: str, timestamp: datetime = None
    ) -> Dict[str, Any]:
        """
        创建标准化数据记录

        Args:
            title: 标题
            summary: 摘要
            url: 链接
            timestamp: 发布时间

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
        }

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
