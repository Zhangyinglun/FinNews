"""
测试 StooqScraper（mock 版）
"""

import pytest

from scrapers.stooq_scraper import StooqScraper


@pytest.fixture
def mock_stooq(mocker):
    """mock requests.get 返回 Stooq CSV 数据"""
    csv_content = (
        "Symbol,Date,Time,Open,High,Low,Close,Volume\n"
        "GC.F,2026-03-01,16:00:00,2035.0,2055.0,2030.0,2050.12,150000\n"
    )
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.text = csv_content
    mocker.patch("scrapers.stooq_scraper.requests.get", return_value=mock_response)
    return mock_response


def test_stooq_fetch_returns_data(mock_stooq):
    """StooqScraper.fetch() 应返回非空数据"""
    scraper = StooqScraper()
    data = scraper.fetch()

    assert isinstance(data, list)
    assert len(data) > 0, "未能从 Stooq 获取任何数据"


def test_stooq_record_fields(mock_stooq):
    """记录应包含 ticker_name 和 price 字段"""
    scraper = StooqScraper()
    data = scraper.fetch()

    assert len(data) > 0
    first = data[0]
    assert "ticker_name" in first, "记录应包含 ticker_name"
    assert "price" in first, "记录应包含 price"
    assert first["price"] > 0, "价格应大于0"


def test_stooq_record_type(mock_stooq):
    """记录类型应为 price_data"""
    scraper = StooqScraper()
    data = scraper.fetch()

    for record in data:
        assert record.get("type") == "price_data", "所有记录应为 price_data 类型"
