"""
测试 SonarScraper 引用过滤与元数据字段
"""

import pytest
from typing import List

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


def test_sonar_scraper_trusted_domain_filter_and_fields(monkeypatch):
    """仅保留可信域引用并附加元数据字段"""
    monkeypatch.setenv("OPENROUTER_API_KEY", "dummy")
    monkeypatch.setattr(Config, "SONAR_USE_TRUSTED_DOMAINS", True)
    monkeypatch.setattr(Config, "TRUSTED_DOMAINS", ["reuters.com"])

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


def test_sonar_scraper_trusted_domain_allows_subdomain_and_port(monkeypatch):
    """可信域应允许子域名与端口"""
    monkeypatch.setenv("OPENROUTER_API_KEY", "dummy")
    monkeypatch.setattr(Config, "SONAR_USE_TRUSTED_DOMAINS", True)
    monkeypatch.setattr(Config, "TRUSTED_DOMAINS", ["reuters.com"])

    citations = [
        Citation(url="https://news.reuters.com/article/abc", title="Reuters"),
        Citation(url="https://reuters.com:8080/market", title="Reuters"),
    ]

    scraper = SonarScraper()
    scraper.client = FakeClient(citations)

    results = scraper._fetch_window(["gold"], "flash")
    assert len(results) == 2, "可信域应保留子域名与带端口链接"


def test_sonar_scraper_trusted_domain_case_insensitive(monkeypatch):
    """可信域比较应不区分大小写"""
    monkeypatch.setenv("OPENROUTER_API_KEY", "dummy")
    monkeypatch.setattr(Config, "SONAR_USE_TRUSTED_DOMAINS", True)
    monkeypatch.setattr(Config, "TRUSTED_DOMAINS", ["ReuTeRs.CoM"])

    citations = [
        Citation(url="https://REUTERS.com/article/abc", title="Reuters"),
    ]

    scraper = SonarScraper()
    scraper.client = FakeClient(citations)

    results = scraper._fetch_window(["gold"], "flash")
    assert len(results) == 1, "可信域比较应忽略大小写"


def test_sonar_scraper_trusted_domain_accepts_url_without_scheme(monkeypatch):
    """可信域应支持无 scheme 的 URL"""
    monkeypatch.setenv("OPENROUTER_API_KEY", "dummy")
    monkeypatch.setattr(Config, "SONAR_USE_TRUSTED_DOMAINS", True)
    monkeypatch.setattr(Config, "TRUSTED_DOMAINS", ["reuters.com"])

    citations = [
        Citation(url="reuters.com/article/abc", title="Reuters"),
        Citation(url="example.com/x", title="Example"),
    ]

    scraper = SonarScraper()
    scraper.client = FakeClient(citations)

    results = scraper._fetch_window(["gold"], "flash")
    assert len(results) == 1, "无 scheme URL 应按可信域过滤"


def test_sonar_scraper_filter_disabled_keeps_all(monkeypatch):
    """关闭过滤时应保留所有引用"""
    monkeypatch.setenv("OPENROUTER_API_KEY", "dummy")
    monkeypatch.setattr(Config, "SONAR_USE_TRUSTED_DOMAINS", False)
    monkeypatch.setattr(Config, "TRUSTED_DOMAINS", ["reuters.com"])

    citations = [
        Citation(url="https://reuters.com/article/abc", title="Reuters"),
        Citation(url="https://example.com/x", title="Example"),
    ]

    scraper = SonarScraper()
    scraper.client = FakeClient(citations)

    results = scraper._fetch_window(["gold"], "flash")
    assert len(results) == 2, "关闭过滤时应保留全部引用"
