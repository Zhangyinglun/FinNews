"""
DuckDuckGo Scraper - 免费新闻搜索替代方案
使用 ddgs 库
"""

import time
from typing import Any, Dict, List, Literal, Optional, Type
from datetime import datetime

DDGSClass: Optional[Type[Any]] = None

try:
    from ddgs import DDGS as DDGSClass

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
            raise ImportError("ddgs未安装")

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
        if not DDG_AVAILABLE or DDGSClass is None:
            raise ImportError("ddgs未安装")
        ddgs = DDGSClass()
        region = Config.DDG_REGION
        backend = Config.DDG_BACKEND
        max_results = Config.DDG_MAX_RESULTS

        for query in queries:
            try:
                self.logger.debug(f"[{window_type}] DDG搜索: {query[:30]}...")

                # 使用 news() 方法获取新闻
                # timelimit: d (day), w (week), m (month)
                search_results = self._search_news(
                    ddgs=ddgs,
                    query=query,
                    region=region,
                    timelimit=timelimit,
                    max_results=max_results,
                    backend=backend,
                )

                if not search_results:
                    search_results = self._search_text(
                        ddgs=ddgs,
                        query=query,
                        region=region,
                        timelimit=timelimit,
                        max_results=max_results,
                        backend=backend,
                    )

                for res in search_results:
                    date_value: Optional[str] = None
                    raw_date = res.get("date")
                    if isinstance(raw_date, str):
                        date_value = raw_date

                    record = self._create_base_record(
                        title=res.get("title", ""),
                        summary=res.get("body", ""),
                        url=self._get_result_url(res),
                        timestamp=self._parse_date(date_value),
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

    @staticmethod
    def _get_result_url(result: Dict[str, Any]) -> str:
        for key in ("url", "href", "link"):
            value = result.get(key)
            if isinstance(value, str):
                return value
        return ""

    def _parse_date(self, date_str: Optional[str]) -> datetime:
        """解析DDG日期"""
        if not date_str:
            return datetime.now()
        try:
            # 尝试 ISO 格式 (DDG通常返回ISO)
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except Exception:
            return datetime.now()

    def _search_news(
        self,
        *,
        ddgs: Any,
        query: str,
        region: str,
        timelimit: str,
        max_results: int,
        backend: str,
    ) -> List[Dict[str, Any]]:
        return self._call_ddgs(
            func=ddgs.news,
            query=query,
            region=region,
            timelimit=timelimit,
            max_results=max_results,
            backend=backend,
        )

    def _search_text(
        self,
        *,
        ddgs: Any,
        query: str,
        region: str,
        timelimit: str,
        max_results: int,
        backend: str,
    ) -> List[Dict[str, Any]]:
        return self._call_ddgs(
            func=ddgs.text,
            query=query,
            region=region,
            timelimit=timelimit,
            max_results=max_results,
            backend=backend,
        )

    @staticmethod
    def _call_ddgs(
        *,
        func: Any,
        query: str,
        region: str,
        timelimit: str,
        max_results: int,
        backend: str,
    ) -> List[Dict[str, Any]]:
        common_args = {
            "region": region,
            "safesearch": "off",
            "timelimit": timelimit,
            "max_results": max_results,
        }
        attempts = [
            {"query": query, "backend": backend},
            {"query": query},
            {"keywords": query, "backend": backend},
            {"keywords": query},
        ]
        last_exc: Optional[TypeError] = None
        for attempt in attempts:
            try:
                result = func(**common_args, **attempt)
                return result or []
            except TypeError as exc:
                message = str(exc)
                if "query" in message or "backend" in message:
                    last_exc = exc
                    continue
                raise
        if last_exc is not None:
            raise last_exc
        return []
