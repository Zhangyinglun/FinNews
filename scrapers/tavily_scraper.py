"""
Tavily API - 地缘政治与宏观新闻搜索
适用: 突发事件、政策变化、市场情绪
"""

import time
from typing import List, Dict, Any
from datetime import datetime

try:
    from tavily import TavilyClient

    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False

from .base_scraper import BaseScraper
from config.config import Config


class TavilyScraper(BaseScraper):
    """Tavily API新闻爬虫"""

    def __init__(self):
        super().__init__("Tavily")

        if not TAVILY_AVAILABLE:
            raise ImportError("tavily-python未安装。请运行: pip install tavily-python")

        if not Config.TAVILY_API_KEY:
            raise ValueError("TAVILY_API_KEY未配置,请在.env文件中设置")

        self.client = TavilyClient(api_key=Config.TAVILY_API_KEY)
        self.queries = Config.TAVILY_QUERIES
        self.trusted_domains = Config.TRUSTED_DOMAINS

    def fetch(self) -> List[Dict[str, Any]]:
        """
        执行多个查询并聚合结果

        Returns:
            新闻数据列表
        """
        all_results = []

        for query in self.queries:
            try:
                self.logger.debug(f"查询: {query[:50]}...")

                response = self.client.search(
                    query=query,
                    topic="news",  # 包含published_date
                    search_depth="advanced",  # 高相关性
                    max_results=10,
                    time_range="week",  # 最近一周
                    include_domains=self.trusted_domains,
                )

                # 解析结果
                for result in response.get("results", []):
                    if result.get("score", 0) > 0.7:  # 仅高分结果
                        record = self._create_base_record(
                            title=result.get("title", ""),
                            summary=result.get("content", ""),
                            url=result.get("url", ""),
                            timestamp=self._parse_date(result.get("published_date")),
                        )
                        record["relevance_score"] = result.get("score", 0)
                        all_results.append(record)

                # 避免速率限制
                time.sleep(0.5)

            except Exception as e:
                self.logger.warning(f"查询失败 '{query[:30]}...': {e}")
                continue

        return all_results

    @staticmethod
    def _parse_date(date_str: str) -> datetime:
        """
        解析Tavily返回的日期字符串

        Args:
            date_str: ISO格式日期字符串

        Returns:
            datetime对象
        """
        if not date_str:
            return datetime.now()
        try:
            # Tavily日期格式: "2026-01-20T10:30:00Z"
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except:
            return datetime.now()
