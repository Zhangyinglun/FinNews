"""
测试 RSS 数据源（mock 版）
"""

import pytest
from unittest.mock import MagicMock

from scrapers.rss_scraper import RSSFeedScraper


@pytest.fixture
def mock_rss(mocker):
    """mock session.get 和 feedparser.parse"""
    # mock HTTP response
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.content = b"<rss/>"
    mock_response.raise_for_status = mocker.MagicMock()

    # mock session
    mock_session = mocker.MagicMock()
    mock_session.get.return_value = mock_response
    mocker.patch("scrapers.rss_scraper.requests.Session", return_value=mock_session)
    mocker.patch("requests.adapters.HTTPAdapter")

    # mock feedparser.parse
    mock_entry_1 = mocker.MagicMock()
    mock_entry_1.get = lambda k, default="": {
        "title": "Gold hits two-month high",
        "summary": "Gold reached its highest level in two months.",
        "link": "https://kitco.com/news/1",
    }.get(k, default)
    # 添加 published_parsed
    mock_entry_1.published_parsed = (2026, 3, 1, 10, 0, 0, 5, 60, 0)

    mock_entry_2 = mocker.MagicMock()
    mock_entry_2.get = lambda k, default="": {
        "title": "Silver industrial demand strong",
        "summary": "Industrial silver demand continues to grow.",
        "link": "https://kitco.com/news/2",
    }.get(k, default)
    mock_entry_2.published_parsed = (2026, 3, 1, 9, 0, 0, 5, 60, 0)

    mock_feed = mocker.MagicMock()
    mock_feed.entries = [mock_entry_1, mock_entry_2]
    mock_feed.bozo = False

    mocker.patch("scrapers.rss_scraper.feedparser.parse", return_value=mock_feed)
    return mock_feed


def test_rss_scraper_returns_data(mock_rss):
    """RSSFeedScraper.fetch() 应返回非空数据"""
    scraper = RSSFeedScraper()
    data = scraper.run()

    assert isinstance(data, list)
    assert len(data) > 0


def test_rss_record_has_feed_name(mock_rss):
    """每条记录应包含 feed_name 字段"""
    scraper = RSSFeedScraper()
    data = scraper.run()

    assert len(data) > 0
    for record in data:
        assert "feed_name" in record, "记录应该包含feed_name字段"


def test_rss_record_type(mock_rss):
    """记录类型应为 news"""
    scraper = RSSFeedScraper()
    data = scraper.run()

    for record in data:
        assert record.get("type") == "news", "所有记录应为 news 类型"
