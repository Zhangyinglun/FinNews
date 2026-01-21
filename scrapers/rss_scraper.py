"""
RSS Feed Parser - Kitco, FXStreet等垂直行业源
特点: 免费、稳定、专业分析师观点
"""

import time
from typing import List, Dict, Any
from datetime import datetime

try:
    import feedparser
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    FEEDPARSER_AVAILABLE = True
except ImportError:
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
        session = requests.Session()
        retry = Retry(
            total=3, backoff_factor=0.3, status_forcelist=(500, 502, 503, 504)
        )
        adapter = HTTPAdapter(max_retries=retry)
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

                # 解析RSS
                feed = feedparser.parse(response.content)

                if feed.bozo:
                    self.logger.warning(
                        f"RSS解析警告 {feed_name}: {feed.bozo_exception}"
                    )

                # 提取条目
                for entry in feed.entries[:10]:  # 限制每个源最多10条
                    record = self._create_base_record(
                        title=entry.get("title", ""),
                        summary=entry.get("summary", entry.get("description", "")),
                        url=entry.get("link", ""),
                        timestamp=self._parse_entry_date(entry),
                    )
                    record["feed_name"] = feed_name
                    record["feed_source"] = feed.feed.get("title", feed_name)
                    all_articles.append(record)

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
