"""
Tavily API - 多时间窗口新闻搜索
支持: Flash(12h) / Cycle(7d) / Trend(30d) 三种时间窗口
"""

import time
from typing import Any, Dict, List, Literal, Optional
from datetime import datetime


try:
    from tavily import TavilyClient

    TAVILY_AVAILABLE = True
except ImportError:
    TavilyClient = None  # type: ignore
    TAVILY_AVAILABLE = False

from .base_scraper import BaseScraper
from config.config import Config


# 时间窗口类型
WindowType = Literal["flash", "cycle", "trend"]


class TavilyScraper(BaseScraper):
    """Tavily API新闻爬虫 - 支持多时间窗口"""

    def __init__(self):
        super().__init__("Tavily")

        if not TAVILY_AVAILABLE or TavilyClient is None:
            raise ImportError("tavily-python未安装。请运行: pip install tavily-python")

        if not Config.TAVILY_API_KEY:
            raise ValueError("TAVILY_API_KEY未配置,请在.env文件中设置")

        self.client = TavilyClient(api_key=Config.TAVILY_API_KEY)
        self.trusted_domains = Config.TRUSTED_DOMAINS

        self.quota_exceeded = False
        self.error_messages: List[str] = []

        # 各时间窗口的查询关键词
        self.flash_queries = Config.TAVILY_FLASH_QUERIES
        self.cycle_queries = Config.TAVILY_CYCLE_QUERIES
        self.trend_queries = Config.TAVILY_TREND_QUERIES

    def fetch(self) -> List[Dict[str, Any]]:
        """
        执行所有时间窗口的查询并聚合结果

        Returns:
            新闻数据列表(带window_type标记)
        """
        all_results: List[Dict[str, Any]] = []

        # Flash Window (12小时 / day)
        flash_results = self._fetch_window(
            queries=self.flash_queries, time_range="day", window_type="flash"
        )
        all_results.extend(flash_results)

        # Cycle Window (7天 / week)
        cycle_results = self._fetch_window(
            queries=self.cycle_queries, time_range="week", window_type="cycle"
        )
        all_results.extend(cycle_results)

        # Trend Window (30天 / month)
        trend_results = self._fetch_window(
            queries=self.trend_queries, time_range="month", window_type="trend"
        )
        all_results.extend(trend_results)

        all_results = self._filter_recent_records(
            all_results,
            Config.FLASH_WINDOW_HOURS,
            allow_fallback=True,
            fallback_note="使用最近一次数据",
        )

        self.logger.info(
            f"Tavily采集完成 | Flash={len(flash_results)} "
            f"Cycle={len(cycle_results)} Trend={len(trend_results)}"
        )

        return all_results

    def _fetch_window(
        self,
        queries: List[str],
        time_range: Literal["day", "week", "month", "year"],
        window_type: WindowType,
    ) -> List[Dict[str, Any]]:
        """
        执行单个时间窗口的查询

        Args:
            queries: 查询关键词列表
            time_range: 时间范围 ("day", "week", "month")
            window_type: 窗口类型标记 ("flash", "cycle", "trend")

        Returns:
            新闻数据列表
        """
        results: List[Dict[str, Any]] = []

        for query in queries:
            try:
                self.logger.debug(f"[{window_type}] 查询: {query[:50]}...")

                response = self.client.search(
                    query=query,
                    topic="news",  # 包含published_date
                    search_depth="advanced",  # 高相关性
                    max_results=10,
                    time_range=time_range,  # type: ignore[arg-type]
                    include_domains=self.trusted_domains,
                )

                # 解析结果
                for result in response.get("results", []):
                    score = result.get("score", 0)
                    if score > 0.7:  # 仅高分结果
                        record = self._create_base_record(
                            title=str(result.get("title", "")),
                            summary=str(result.get("content", "")),
                            url=str(result.get("url", "")),
                            timestamp=self._parse_date(result.get("published_date")),
                            fallback_allowed=True,
                        )
                        record["relevance_score"] = score
                        record["window_type"] = window_type  # 标记时间窗口
                        record["query"] = query  # 记录查询词
                        results.append(record)

                # 避免速率限制
                time.sleep(0.5)

            except Exception as e:
                message = str(e)
                self.error_messages.append(message)
                if "usage limit" in message.lower():
                    self.quota_exceeded = True
                self.logger.warning(f"[{window_type}] 查询失败 '{query[:30]}...': {e}")
                continue

        return results

    def fetch_by_window(self, window_type: WindowType) -> List[Dict[str, Any]]:
        """
        仅获取指定时间窗口的数据

        Args:
            window_type: 窗口类型 ("flash", "cycle", "trend")

        Returns:
            新闻数据列表
        """
        if window_type == "flash":
            return self._fetch_window(self.flash_queries, "day", "flash")
        elif window_type == "cycle":
            return self._fetch_window(self.cycle_queries, "week", "cycle")
        elif window_type == "trend":
            return self._fetch_window(self.trend_queries, "month", "trend")
        else:
            self.logger.error(f"未知窗口类型: {window_type}")
            return []

    @staticmethod
    def _parse_date(date_str: Optional[str]) -> datetime:
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
        except Exception:
            return datetime.now()
