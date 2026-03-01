"""
测试 Tavily 数据源（mock 版）
"""

import pytest

from scrapers.tavily_scraper import TavilyScraper


@pytest.fixture
def mock_tavily(mocker, monkeypatch):
    """mock TavilyClient"""
    monkeypatch.setenv("TAVILY_API_KEY", "dummy_key")

    mock_client = mocker.MagicMock()
    from datetime import datetime
    # 使用 naive datetime（无时区）避免 aware vs naive 比较异常
    now_str = datetime.now().isoformat()
    mock_client.search.return_value = {
        "results": [
            {
                "title": "Gold prices surge on Fed rate cut hopes",
                "url": "https://reuters.com/gold-1",
                "content": "Gold futures rose sharply as investors bet on rate cuts.",
                "score": 0.95,
                "published_date": now_str,
                "source": "reuters.com",
            },
            {
                "title": "Silver demand rises in industrial sector",
                "url": "https://bloomberg.com/silver-1",
                "content": "Silver prices gain as industrial demand improves.",
                "score": 0.88,
                "published_date": now_str,
                "source": "bloomberg.com",
            },
        ]
    }
    mocker.patch("scrapers.tavily_scraper.TavilyClient", return_value=mock_client)
    return mock_client


def test_tavily_scraper_returns_data(mock_tavily):
    """TavilyScraper.fetch() 应返回非空数据"""
    scraper = TavilyScraper()
    data = scraper.run()

    assert isinstance(data, list)
    assert len(data) > 0


def test_tavily_record_has_required_fields(mock_tavily):
    """每条记录应包含 title 和 source"""
    scraper = TavilyScraper()
    data = scraper.run()

    assert len(data) > 0
    first = data[0]
    assert "title" in first, "记录应该包含title字段"
    assert "source" in first, "记录应该包含source字段"


def test_tavily_record_type(mock_tavily):
    """记录类型应为 news"""
    scraper = TavilyScraper()
    data = scraper.run()

    for record in data:
        assert record.get("type") == "news", "所有记录应为 news 类型"
