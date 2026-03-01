"""
集成测试 - 测试完整的数据管道（mock 外部 API）
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch


# 模拟爬虫返回数据
MOCK_YFINANCE_DATA = [
    {
        "type": "price_data",
        "ticker_name": "gold_futures",
        "ticker": "GC=F",
        "price": 2050.12,
        "change_percent": 0.8,
        "source": "YFinance",
        "timestamp": datetime.now(),
    },
    {
        "type": "price_data",
        "ticker_name": "silver_futures",
        "ticker": "SI=F",
        "price": 23.45,
        "change_percent": 0.5,
        "source": "YFinance",
        "timestamp": datetime.now(),
    },
    {
        "type": "price_data",
        "ticker_name": "vix",
        "ticker": "^VIX",
        "price": 18.5,
        "change_percent": -2.1,
        "source": "YFinance",
        "timestamp": datetime.now(),
    },
]

MOCK_FRED_DATA = [
    {
        "type": "economic_data",
        "indicator": "DXY",
        "value": 104.2,
        "change_pct": 0.1,
        "source": "FRED",
        "timestamp": datetime.now(),
    },
    {
        "type": "economic_data",
        "indicator": "US10Y",
        "value": 4.25,
        "change_pct": 0.02,
        "source": "FRED",
        "timestamp": datetime.now(),
    },
]


@pytest.mark.integration
@pytest.mark.slow
def test_full_pipeline(tmp_path, mocker):
    """测试完整的数据管道流程（mock 版）"""
    from scrapers import YFinanceScraper, FREDScraper
    from processors import DataCleaner, Deduplicator
    from storage import JSONStorage

    # mock 爬虫 run 方法
    mocker.patch.object(YFinanceScraper, "run", return_value=MOCK_YFINANCE_DATA)
    mocker.patch.object(FREDScraper, "run", return_value=MOCK_FRED_DATA)

    # mock JSONStorage 使用 tmp_path
    storage = JSONStorage.__new__(JSONStorage)
    storage.raw_dir = tmp_path / "raw"
    storage.processed_dir = tmp_path / "processed"
    storage.raw_dir.mkdir()
    storage.processed_dir.mkdir()

    # 1. 数据抓取
    scrapers = []
    try:
        scrapers.append(YFinanceScraper())
    except Exception:
        pass
    try:
        scrapers.append(FREDScraper())
    except Exception:
        pass

    assert scrapers, "应有可用的数据源"

    all_data = []
    for scraper in scrapers:
        data = scraper.run()
        all_data.extend(data)

    assert len(all_data) > 0, "应抓取到数据"

    # 2. 数据清洗
    cleaner = DataCleaner()
    cleaned_data = cleaner.clean(all_data)

    assert len(cleaned_data) <= len(all_data), "清洗后数据量不应增加"

    # 3. 数据去重
    deduplicator = Deduplicator()
    unique_data = deduplicator.deduplicate(cleaned_data)

    assert len(unique_data) <= len(cleaned_data), "去重后数据量不应增加"
    assert len(unique_data) > 0, "去重后应有数据"

    # 4. 数据存储
    raw_filename = f"integration_test_raw_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    storage.save_raw(all_data, filename=raw_filename)

    processed_filename = (
        f"integration_test_processed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    )
    storage.save_processed(unique_data, filename=processed_filename)

    # 5. 最终验证
    raw_file = storage.raw_dir / raw_filename
    processed_file = storage.processed_dir / processed_filename

    assert raw_file.exists(), "原始数据文件应存在"
    assert processed_file.exists(), "处理数据文件应存在"

    assert len(unique_data) <= len(all_data), "最终数据不应多于原始数据"

    for item in unique_data:
        assert "source" in item, "每条记录应有 source 字段"
        assert "timestamp" in item, "每条记录应有 timestamp 字段"
