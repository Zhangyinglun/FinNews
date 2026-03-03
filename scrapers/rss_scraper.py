"""
RSS Feed Parser - Kitco, FXStreet等垂直行业源
特点: 免费、稳定、专业分析师观点
"""

import time
import warnings
from typing import List, Dict, Any
from datetime import datetime


try:
    import feedparser
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    FEEDPARSER_AVAILABLE = True
except ImportError:
    feedparser = None  # type: ignore
    requests = None  # type: ignore
    HTTPAdapter = None  # type: ignore
    Retry = None  # type: ignore
    FEEDPARSER_AVAILABLE = False

from .base_scraper import BaseScraper
from config.config import Config


class RSSFeedScraper(BaseScraper):
    """RSS订阅源爬虫"""

    def __init__(self):
        super().__init__("RSS")

        if not FEEDPARSER_AVAILABLE:
            raise ImportError(
                "feedparser或requests未安装。请运行: pip install feedparser requests"
            )

        self.feeds = Config.RSS_FEEDS
        self.session = self._create_session()

    def _create_session(self):
        """创建带重试机制的Session"""
        if not FEEDPARSER_AVAILABLE:
            raise ImportError(
                "feedparser或requests未安装。请运行: pip install feedparser requests"
            )
        session = requests.Session()  # type: ignore[union-attr]
        retry = Retry(
            total=3, backoff_factor=0.3, status_forcelist=(500, 502, 503, 504)
        )  # type: ignore[operator]
        adapter = HTTPAdapter(max_retries=retry)  # type: ignore[operator]
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def fetch(self) -> List[Dict[str, Any]]:
        """
        解析所有RSS订阅源

        Returns:
            新闻数据列表
        """
        all_articles = []

        for feed_name, feed_url in self.feeds.items():
            try:
                self.logger.debug(f"解析RSS: {feed_name}")

                # 使用session下载feed
                response = self.session.get(feed_url, timeout=10)
                response.raise_for_status()

                # 解析RSS（抑制 feedparser issue#310 的临时向后兼容警告）
                with warnings.catch_warnings():
                    warnings.filterwarnings(
                        "ignore",
                        message=".*temporary mapping.*updated_parsed.*",
                        category=DeprecationWarning,
                        module="feedparser",
                    )
                    feed = feedparser.parse(response.content)  # type: ignore[union-attr]

                if feed.bozo:
                    self.logger.warning(
                        f"RSS解析警告 {feed_name}: {feed.bozo_exception}"
                    )

                # 提取条目
                feed_articles = []
                for entry in feed.entries[:10]:  # 限制每个源最多10条
                    record = self._create_base_record(
                        title=str(entry.get("title", "")),
                        summary=str(entry.get("summary", entry.get("description", ""))),
                        url=str(entry.get("link", "")),
                        timestamp=self._parse_entry_date(entry),
                        fallback_allowed=True,
                    )
                    record["feed_name"] = feed_name
                    feed_meta = getattr(feed, "feed", None)
                    feed_title = (
                        feed_meta.get("title") if isinstance(feed_meta, dict) else None
                    )
                    record["feed_source"] = str(feed_title or feed_name)
                    feed_articles.append(record)

                feed_articles = self._filter_recent_records(
                    feed_articles,
                    Config.FLASH_WINDOW_HOURS,
                    allow_fallback=True,
                    fallback_note="使用最近一次数据",
                )
                all_articles.extend(feed_articles)

                time.sleep(0.5)  # 礼貌延迟

            except Exception as e:
                self.logger.error(f"RSS抓取失败 {feed_name}: {e}")
                continue

        return all_articles

    @staticmethod
    def _parse_entry_date(entry) -> datetime:
        """
        解析RSS条目的发布日期

        Args:
            entry: feedparser entry对象

        Returns:
            datetime对象
        """
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                return datetime(*entry.published_parsed[:6])
            except:
                pass
        elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
            try:
                return datetime(*entry.updated_parsed[:6])
            except:
                pass
        return datetime.now()
