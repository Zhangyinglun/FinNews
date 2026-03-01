"""
测试 FRED 数据源（mock 版）
"""

import pytest
import pandas as pd

from scrapers.fred_scraper import FREDScraper


@pytest.fixture
def mock_fred(mocker, monkeypatch):
    """mock fredapi.Fred"""
    monkeypatch.setenv("FRED_API_KEY", "dummy_key")

    def fake_get_series(series_id, **kwargs):
        data = {
            "CPIAUCSL": [310.0, 311.5],
            "PCEPILFE": [170.0, 170.5],
            "PAYEMS": [158000, 158200],
            "UNRATE": [4.1, 4.0],
            "FEDFUNDS": [5.25, 5.25],
            "GDP": [28000, 28500],
            "M1SL": [18000, 18100],
            "M2SL": [21000, 21100],
        }
        values = data.get(series_id, [1.0, 1.1])
        return pd.Series(
            values,
            index=pd.to_datetime(["2026-01-01", "2026-02-01"]),
        )

    mock_f = mocker.MagicMock()
    mock_f.get_series.side_effect = fake_get_series
    mocker.patch("fredapi.Fred", return_value=mock_f)
    return mock_f


def test_fred_scraper_returns_data(mock_fred):
    """FREDScraper.fetch() 应返回非空数据"""
    scraper = FREDScraper()
    data = scraper.run()

    assert isinstance(data, list)
    assert len(data) > 0


def test_fred_record_has_required_fields(mock_fred):
    """每条记录应包含 indicator 和 value"""
    scraper = FREDScraper()
    data = scraper.run()

    assert len(data) > 0
    first = data[0]
    assert "indicator" in first, "记录应该包含indicator字段"
    assert "value" in first, "记录应该包含value字段"
    assert "source" in first, "记录应该包含source字段"


def test_fred_record_type(mock_fred):
    """记录类型应为 economic_data"""
    scraper = FREDScraper()
    data = scraper.run()

    for record in data:
        assert record.get("type") == "economic_data", "所有记录应为 economic_data 类型"
