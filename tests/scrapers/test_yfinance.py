"""
测试 yfinance 数据源（mock 版）
"""

import pytest
import pandas as pd
from unittest.mock import MagicMock, patch

from scrapers.yfinance_scraper import YFinanceScraper


@pytest.fixture
def mock_ticker(mocker):
    """mock yfinance.Ticker"""
    hist_data = pd.DataFrame(
        {
            "Close": [2000.0, 2010.0, 2020.0, 2030.0, 2050.12],
            "Open": [1990.0, 2005.0, 2015.0, 2025.0, 2035.0],
            "High": [2005.0, 2015.0, 2025.0, 2040.0, 2055.0],
            "Low": [1985.0, 2000.0, 2010.0, 2020.0, 2030.0],
            "Volume": [100000, 110000, 120000, 130000, 150000],
        }
    )

    mock_t = mocker.MagicMock()
    mock_t.info = {
        "regularMarketPrice": 2050.12,
        "regularMarketPreviousClose": 2035.00,
        "regularMarketOpen": 2035.00,
        "regularMarketDayHigh": 2055.00,
        "regularMarketDayLow": 2030.00,
        "regularMarketVolume": 150000,
        "shortName": "Gold Futures",
    }
    mock_t.news = [
        {
            "title": "Gold rises on inflation",
            "link": "https://example.com/1",
            "summary": "Gold climbs as CPI beats estimates",
            "providerPublishTime": 1700000000,
            "publisher": "Reuters",
        }
    ]
    mock_t.history.return_value = hist_data
    mocker.patch("yfinance.Ticker", return_value=mock_t)
    return mock_t


def test_yfinance_scraper_returns_data(mock_ticker):
    """YFinanceScraper.fetch() 应返回非空数据列表"""
    scraper = YFinanceScraper()
    data = scraper.run()

    assert isinstance(data, list)
    assert len(data) > 0


def test_yfinance_scraper_has_price_records(mock_ticker):
    """应至少有一条价格记录"""
    scraper = YFinanceScraper()
    data = scraper.run()

    price_items = [d for d in data if d.get("type") == "price_data"]
    assert len(price_items) > 0


def test_yfinance_price_record_fields(mock_ticker):
    """价格记录应包含必要字段"""
    scraper = YFinanceScraper()
    data = scraper.run()

    price_items = [d for d in data if d.get("type") == "price_data"]
    assert len(price_items) > 0

    first = price_items[0]
    assert "ticker" in first
    assert "price" in first
    assert first["price"] > 0
    assert "source" in first
