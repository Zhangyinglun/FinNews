"""
测试 Alpha Vantage 数据源（mock 版）
"""

import pytest
import pandas as pd

from scrapers.alpha_vantage_scraper import AlphaVantageScraper


@pytest.fixture
def mock_alpha_vantage(mocker, monkeypatch):
    """mock alpha_vantage ForeignExchange"""
    monkeypatch.setenv("ALPHA_VANTAGE_API_KEY", "dummy_key")

    fx_data = pd.DataFrame(
        {
            "4. close": [0.9215],
            "1. open": [0.9200],
            "2. high": [0.9230],
            "3. low": [0.9190],
        },
        index=pd.to_datetime(["2026-03-01"]),
    )
    fx_data.index.name = "date"

    mock_fx = mocker.MagicMock()
    mock_fx.get_currency_exchange_daily.return_value = (fx_data, {})

    mock_ts = mocker.MagicMock()

    mocker.patch("scrapers.alpha_vantage_scraper.ForeignExchange", return_value=mock_fx)
    mocker.patch("scrapers.alpha_vantage_scraper.TimeSeries", return_value=mock_ts)
    return mock_fx


def test_alpha_vantage_scraper_returns_data(mock_alpha_vantage):
    """AlphaVantageScraper.fetch() 应返回数据"""
    scraper = AlphaVantageScraper()
    data = scraper.run()

    assert isinstance(data, list)
    assert len(data) > 0


def test_alpha_vantage_record_fields(mock_alpha_vantage):
    """记录应包含 pair 和 type 字段"""
    scraper = AlphaVantageScraper()
    data = scraper.run()

    assert len(data) > 0
    first = data[0]
    assert "pair" in first, "记录应该包含pair字段"
    assert "type" in first, "记录应该包含type字段"


def test_alpha_vantage_record_type(mock_alpha_vantage):
    """记录类型应为 fx_data"""
    scraper = AlphaVantageScraper()
    data = scraper.run()

    for record in data:
        assert record.get("type") == "fx_data", "所有记录应为 fx_data 类型"
