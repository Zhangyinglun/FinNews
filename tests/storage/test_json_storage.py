"""
测试 JSONStorage 存储模块
"""

import json
from datetime import datetime
from pathlib import Path

import pytest

from storage.json_storage import JSONStorage


@pytest.fixture
def storage(tmp_path, monkeypatch):
    """使用 tmp_path 替代真实 outputs 目录"""
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    raw_dir.mkdir()
    processed_dir.mkdir()

    s = JSONStorage.__new__(JSONStorage)
    s.raw_dir = raw_dir
    s.processed_dir = processed_dir
    return s


@pytest.fixture
def test_data():
    return [
        {
            "type": "economic_data",
            "indicator": "CPI",
            "value": 3.2,
            "change_pct": 0.5,
            "timestamp": datetime(2026, 1, 20, 10, 0, 0),
            "source": "FRED",
        },
        {
            "type": "price_data",
            "ticker": "GC=F",
            "ticker_name": "Gold Futures",
            "price": 2050.12,
            "change": 15.30,
            "change_percent": 0.75,
            "week_change_percent": 2.5,
            "open": 2035.00,
            "high": 2055.00,
            "low": 2030.00,
            "volume": 150000,
            "ma5": 2040.50,
            "timestamp": datetime(2026, 1, 20, 15, 0, 0),
            "source": "YFinance",
        },
        {
            "type": "price_data",
            "ticker": "SI=F",
            "ticker_name": "Silver Futures",
            "price": 24.50,
            "change": -0.25,
            "change_percent": -1.0,
            "timestamp": datetime(2026, 1, 20, 15, 0, 0),
            "source": "YFinance",
        },
        {
            "type": "fx_data",
            "pair": "USD/EUR",
            "close": 0.92,
            "timestamp": datetime(2026, 1, 20, 14, 0, 0),
            "source": "AlphaVantage",
        },
        {
            "type": "news",
            "title": "Gold prices surge on inflation concerns",
            "summary": "Gold futures rose sharply as inflation data exceeded expectations...",
            "full_content": "Gold futures rose sharply as inflation data exceeded expectations.",
            "url": "https://example.com/news/1",
            "timestamp": datetime(2026, 1, 20, 12, 30, 0),
            "source": "Reuters",
            "impact_tag": "#Bullish",
        },
        {
            "type": "news",
            "title": "Silver demand increases in industrial sector",
            "summary": "Industrial demand for silver continues to grow...",
            "url": "https://example.com/news/2",
            "timestamp": datetime(2026, 1, 20, 11, 0, 0),
            "source": "Kitco",
            "impact_tag": "#Bullish",
        },
        {
            "type": "news",
            "title": "Fed signals potential rate hold",
            "summary": "Federal Reserve officials suggest interest rates may remain steady...",
            "url": "https://example.com/news/3",
            "timestamp": datetime(2026, 1, 20, 10, 30, 0),
            "source": "Bloomberg",
            "impact_tag": "#Neutral",
        },
    ]


def test_save_raw(storage, test_data):
    """测试 save_raw() 保存原始数据"""
    raw_filename = "test_raw.json"
    storage.save_raw(test_data, filename=raw_filename)

    raw_filepath = storage.raw_dir / raw_filename
    assert raw_filepath.exists(), "原始数据文件应该存在"

    with open(raw_filepath, "r", encoding="utf-8") as f:
        loaded_data = json.load(f)
    assert len(loaded_data) == len(test_data), "加载的数据条数应该匹配"


def test_save_processed_markdown(storage, test_data):
    """测试 save_processed() 生成 Markdown 文件"""
    processed_filename = "test_processed.md"
    storage.save_processed(test_data, filename=processed_filename)

    processed_filepath = storage.processed_dir / processed_filename
    assert processed_filepath.exists(), "处理后数据文件应该存在"

    with open(processed_filepath, "r", encoding="utf-8") as f:
        markdown_content = f.read()

    assert "宏观经济指标" in markdown_content, "应该包含经济指标section"
    assert "最新市场价格" in markdown_content, "应该包含价格section"
    assert "外汇数据" in markdown_content, "应该包含外汇section"
    assert "相关新闻" in markdown_content, "应该包含新闻section"
    assert "数据统计" in markdown_content, "应该包含统计section"

    assert "CPI" in markdown_content, "应该包含CPI数据"
    assert "Gold Futures" in markdown_content, "应该包含黄金价格"
    assert "Silver Futures" in markdown_content, "应该包含白银价格"
    assert "USD/EUR" in markdown_content, "应该包含外汇数据"
    assert "inflation concerns" in markdown_content, "应该包含新闻标题"
    assert "#Bullish" in markdown_content, "应该包含影响标签"
    assert "5日均线" in markdown_content, "应该包含移动平均线"


def test_markdown_empty_data(storage):
    """测试空数据的 Markdown 转换"""
    empty_md = storage._to_markdown([])
    assert "总计**: 0 条" in empty_md, "空数据应该显示0条记录"


def test_markdown_news_only(storage):
    """测试只有新闻数据时的 Markdown 转换"""
    news_only = [
        {
            "type": "news",
            "title": "Test News",
            "summary": "Test summary",
            "timestamp": datetime.now(),
            "source": "TestSource",
            "impact_tag": "#Neutral",
        }
    ]
    news_md = storage._to_markdown(news_only)
    assert "相关新闻" in news_md, "应该包含新闻section"
    assert "TestSource" in news_md, "应该包含来源"


def test_markdown_price_only(storage):
    """测试只有价格数据时的 Markdown 转换"""
    price_only = [
        {
            "type": "price_data",
            "ticker": "GC=F",
            "ticker_name": "Gold",
            "price": 2000.0,
            "timestamp": datetime.now(),
        }
    ]
    price_md = storage._to_markdown(price_only)
    assert "最新市场价格" in price_md, "应该包含价格section"
    assert "Gold" in price_md, "应该包含商品名称"
