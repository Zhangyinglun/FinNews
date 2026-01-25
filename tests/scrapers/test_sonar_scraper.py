"""
测试 SonarScraper 引用过滤与元数据字段
"""

import os
import sys
from typing import Dict, List

os.environ["OPENROUTER_API_KEY"] = "dummy"

sys.path.insert(0, "D:\\Projects\\FinNews\\.worktrees\\plan-sonar-scraper-review")

from config.config import Config
from scrapers.sonar_scraper import SonarScraper
from utils.sonar_client import SonarSearchResult, Citation


class FakeClient:
    def __init__(self, citations: List[Citation]) -> None:
        self._citations = citations

    def search(self, query: str) -> SonarSearchResult:
        return SonarSearchResult(
            answer="summary",
            citations=self._citations,
        )


def _backup_config() -> Dict[str, object]:
    return {
        "SONAR_USE_TRUSTED_DOMAINS": Config.SONAR_USE_TRUSTED_DOMAINS,
        "TRUSTED_DOMAINS": Config.TRUSTED_DOMAINS,
    }


def _restore_config(backup: Dict[str, object]) -> None:
    Config.SONAR_USE_TRUSTED_DOMAINS = backup["SONAR_USE_TRUSTED_DOMAINS"]
    Config.TRUSTED_DOMAINS = backup["TRUSTED_DOMAINS"]


def test_sonar_scraper_trusted_domain_filter_and_fields():
    """仅保留可信域引用并附加元数据字段"""
    backup = _backup_config()
    try:
        Config.SONAR_USE_TRUSTED_DOMAINS = True
        Config.TRUSTED_DOMAINS = ["reuters.com"]

        citations = [
            Citation(url="https://reuters.com/article/abc", title="Reuters"),
            Citation(url="https://example.com/x", title="Example"),
        ]

        scraper = SonarScraper()
        scraper.client = FakeClient(citations)

        results = scraper._fetch_window(["gold"], "flash")
        assert len(results) == 1, "可信域过滤应只保留 1 条"

        record = results[0]
        assert record.get("sonar_citations_count") == 2, "应记录原始引用数量"
        assert record.get("sonar_model"), "应记录 sonar_model"
        assert record.get("sonar_answer") == "summary", "应记录 sonar_answer"
        assert record.get("window_type") == "flash", "应记录 window_type"
        assert record.get("query") == "gold", "应记录 query"
    finally:
        _restore_config(backup)


def test_sonar_scraper_trusted_domain_allows_subdomain_and_port():
    """可信域应允许子域名与端口"""
    backup = _backup_config()
    try:
        Config.SONAR_USE_TRUSTED_DOMAINS = True
        Config.TRUSTED_DOMAINS = ["reuters.com"]

        citations = [
            Citation(url="https://news.reuters.com/article/abc", title="Reuters"),
            Citation(url="https://reuters.com:8080/market", title="Reuters"),
        ]

        scraper = SonarScraper()
        scraper.client = FakeClient(citations)

        results = scraper._fetch_window(["gold"], "flash")
        assert len(results) == 2, "可信域应保留子域名与带端口链接"
    finally:
        _restore_config(backup)


def test_sonar_scraper_trusted_domain_case_insensitive():
    """可信域比较应不区分大小写"""
    backup = _backup_config()
    try:
        Config.SONAR_USE_TRUSTED_DOMAINS = True
        Config.TRUSTED_DOMAINS = ["ReuTeRs.CoM"]

        citations = [
            Citation(url="https://REUTERS.com/article/abc", title="Reuters"),
        ]

        scraper = SonarScraper()
        scraper.client = FakeClient(citations)

        results = scraper._fetch_window(["gold"], "flash")
        assert len(results) == 1, "可信域比较应忽略大小写"
    finally:
        _restore_config(backup)


def test_sonar_scraper_filter_disabled_keeps_all():
    """关闭过滤时应保留所有引用"""
    backup = _backup_config()
    try:
        Config.SONAR_USE_TRUSTED_DOMAINS = False
        Config.TRUSTED_DOMAINS = ["reuters.com"]

        citations = [
            Citation(url="https://reuters.com/article/abc", title="Reuters"),
            Citation(url="https://example.com/x", title="Example"),
        ]

        scraper = SonarScraper()
        scraper.client = FakeClient(citations)

        results = scraper._fetch_window(["gold"], "flash")
        assert len(results) == 2, "关闭过滤时应保留全部引用"
    finally:
        _restore_config(backup)


if __name__ == "__main__":
    test_sonar_scraper_trusted_domain_filter_and_fields()
    test_sonar_scraper_trusted_domain_allows_subdomain_and_port()
    test_sonar_scraper_trusted_domain_case_insensitive()
    test_sonar_scraper_filter_disabled_keeps_all()
