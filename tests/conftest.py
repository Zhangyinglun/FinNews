"""
全局 pytest 配置与共享 fixture
"""

import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

# 确保项目根目录在 sys.path 中
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# 排除 debug_chart.py（无测试函数，直接执行绘图）
collect_ignore = ["debug_chart.py"]


@pytest.fixture(autouse=True)
def _suppress_logger(caplog):
    """自动静音项目 logger，防止测试输出污染"""
    with caplog.at_level(logging.CRITICAL, logger="root"):
        yield


@pytest.fixture
def make_news_record():
    """新闻记录工厂 fixture"""
    def _factory(
        title: str = "Gold prices rise",
        summary: str = "Gold futures increased",
        source: str = "Reuters",
        hours_ago: float = 1.0,
        record_type: str = "news",
        **kwargs,
    ) -> dict:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        record = {
            "type": record_type,
            "title": title,
            "summary": summary,
            "source": source,
            "timestamp": now - timedelta(hours=hours_ago),
        }
        record.update(kwargs)
        return record

    return _factory


@pytest.fixture
def make_price_record():
    """价格记录工厂 fixture"""
    def _factory(
        ticker: str = "GC=F",
        ticker_name: str = "gold_futures",
        price: float = 2050.0,
        source: str = "YFinance",
        **kwargs,
    ) -> dict:
        record = {
            "type": "price_data",
            "ticker": ticker,
            "ticker_name": ticker_name,
            "price": price,
            "source": source,
            "timestamp": datetime.now(timezone.utc).replace(tzinfo=None),
        }
        record.update(kwargs)
        return record

    return _factory


@pytest.fixture
def env_override(monkeypatch):
    """环境变量临时覆盖 fixture"""
    def _apply(overrides: dict, unset: list | None = None):
        if unset:
            for key in unset:
                monkeypatch.delenv(key, raising=False)
        for key, value in overrides.items():
            monkeypatch.setenv(key, value)

    return _apply
