"""
DuckDuckGo Scraper - 免费新闻搜索替代方案
使用 duckduckgo_search 库
"""

import time
from typing import Any, Dict, List, Literal
from datetime import datetime

try:
    from duckduckgo_search import DDGS

    DDG_AVAILABLE = True
except ImportError:
    DDG_AVAILABLE = False

from .base_scraper import BaseScraper
from config.config import Config

WindowType = Literal["flash", "cycle", "trend"]


class DuckDuckGoScraper(BaseScraper):
    """DuckDuckGo新闻爬虫"""

    def __init__(self):
        super().__init__("DuckDuckGo")

        if not DDG_AVAILABLE:
            raise ImportError("duckduckgo_search未安装")

        self.flash_queries = Config.TAVILY_FLASH_QUERIES
        self.cycle_queries = Config.TAVILY_CYCLE_QUERIES
        self.trend_queries = Config.TAVILY_TREND_QUERIES

    def fetch(self) -> List[Dict[str, Any]]:
        """
        执行所有时间窗口的查询

        Returns:
            新闻数据列表
        """
        all_results = []

        # Flash (Day)
        all_results.extend(self._fetch_window(self.flash_queries, "d", "flash"))

        # Cycle (Week)
        all_results.extend(self._fetch_window(self.cycle_queries, "w", "cycle"))

        # Trend (Month)
        all_results.extend(self._fetch_window(self.trend_queries, "m", "trend"))

        return all_results

    def _fetch_window(
        self, queries: List[str], timelimit: str, window_type: WindowType
    ) -> List[Dict[str, Any]]:
        """执行单个窗口查询"""
        results: List[Dict[str, Any]] = []
        ddgs = DDGS()

        for query in queries:
            try:
                self.logger.debug(f"[{window_type}] DDG搜索: {query[:30]}...")

                # 使用 news() 方法获取新闻
                # timelimit: d (day), w (week), m (month)
                search_results = ddgs.news(
                    keywords=query,
                    region="wt-wt",
                    safesearch="off",
                    timelimit=timelimit,
                    max_results=5,
                )

                for res in search_results:
                    record = self._create_base_record(
                        title=res.get("title", ""),
                        summary=res.get("body", ""),
                        url=res.get("url", ""),
                        timestamp=self._parse_date(res.get("date")),
                        record_type="news",
                    )
                    record["window_type"] = window_type
                    record["query"] = query
                    record["source"] = "duckduckgo"  # 显式覆盖
                    results.append(record)

                time.sleep(1.0)  # 避免限流

            except Exception as e:
                self.logger.warning(
                    f"[{window_type}] DDG搜索失败 '{query[:10]}...': {e}"
                )
                time.sleep(2.0)

        return results

    def _parse_date(self, date_str: str) -> datetime:
        """解析DDG日期"""
        if not date_str:
            return datetime.now()
        try:
            # 尝试 ISO 格式 (DDG通常返回ISO)
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except Exception:
            return datetime.now()
