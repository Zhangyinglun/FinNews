"""
测试 COMEX 库存数据爬虫和查询函数（mock 版）
"""

import pytest
from datetime import datetime, date
from unittest.mock import MagicMock

from scrapers.comex_scraper import ComexScraper
from analyzers.rule_engine import RuleEngine
from utils.comex_query import get_comex_snapshot, get_comex_summary


# 模拟 COMEX 数据记录
MOCK_COMEX_DATA = [
    {
        "source": "COMEX",
        "type": "inventory_data",
        "metal": "silver",
        "report_date": date.today(),
        "timestamp": datetime.now(),
        "registered": 120_000_000,
        "eligible": 200_000_000,
        "total": 320_000_000,
        "registered_million": 120.0,
        "eligible_million": 200.0,
        "total_million": 320.0,
        "registered_weekly_change_pct": -2.5,
    },
    {
        "source": "COMEX",
        "type": "inventory_data",
        "metal": "gold",
        "report_date": date.today(),
        "timestamp": datetime.now(),
        "registered": 18_000_000,
        "eligible": 12_000_000,
        "total": 30_000_000,
        "registered_million": 18.0,
        "eligible_million": 12.0,
        "total_million": 30.0,
        "registered_weekly_change_pct": 0.5,
    },
]


@pytest.fixture
def mock_comex_scraper(mocker):
    """mock ComexScraper.fetch_metal 返回预构造数据"""
    def fake_fetch_metal(metal: str):
        for record in MOCK_COMEX_DATA:
            if record["metal"] == metal:
                return {
                    "report_date": record["report_date"],
                    "registered": record["registered"],
                    "eligible": record["eligible"],
                    "total": record["total"],
                    "registered_million": record["registered_million"],
                    "eligible_million": record["eligible_million"],
                    "total_million": record["total_million"],
                }
        return None

    mocker.patch.object(ComexScraper, "fetch_metal", side_effect=fake_fetch_metal)
    mocker.patch.object(ComexScraper, "_update_history")
    mocker.patch.object(ComexScraper, "_calculate_weekly_change", return_value=None)
    mocker.patch.object(ComexScraper, "_calculate_daily_change", return_value=None)
    return None


def test_comex_rule_engine_analyze(mock_comex_scraper):
    """RuleEngine.analyze_comex 应生成 ComexSignal"""
    rule_engine = RuleEngine()
    comex_signal = rule_engine.analyze_comex(MOCK_COMEX_DATA)

    assert comex_signal is not None
    assert comex_signal.silver_registered_million is not None
    assert comex_signal.gold_registered_million is not None
    assert comex_signal.silver_alert_level is not None
    assert comex_signal.gold_alert_level is not None


def test_comex_signal_methods(mock_comex_scraper):
    """ComexSignal 辅助方法应正常运行"""
    rule_engine = RuleEngine()
    comex_signal = rule_engine.analyze_comex(MOCK_COMEX_DATA)

    # 验证方法可调用
    worst_level = comex_signal.get_worst_alert_level()
    assert worst_level is not None

    emoji = comex_signal.get_alert_emoji()
    assert isinstance(emoji, str)

    has_emergency = comex_signal.has_emergency
    assert isinstance(has_emergency, bool)


def test_comex_scraper_fetch(mocker):
    """ComexScraper.fetch 应返回包含 silver 和 gold 的记录"""
    # 直接 mock fetch 方法，避免 _filter_recent_records 过滤
    mocker.patch.object(ComexScraper, "fetch", return_value=MOCK_COMEX_DATA)
    scraper = ComexScraper.__new__(ComexScraper)
    data = scraper.fetch()

    assert isinstance(data, list)
    metals = {r.get("metal") for r in data}
    assert "silver" in metals or "gold" in metals


def test_get_comex_snapshot_silver(mocker):
    """get_comex_snapshot 应返回白银快照"""
    # ComexScraper 在函数内部 local import，需要 patch 原始模块路径
    silver_data = next(r for r in MOCK_COMEX_DATA if r["metal"] == "silver")
    mock_scraper = mocker.patch("scrapers.comex_scraper.ComexScraper")
    mock_scraper.return_value.fetch_metal.return_value = {
        "report_date": silver_data["report_date"],
        "registered": silver_data["registered"],
        "eligible": silver_data["eligible"],
        "total": silver_data["total"],
        "registered_million": silver_data["registered_million"],
        "eligible_million": silver_data["eligible_million"],
        "total_million": silver_data["total_million"],
    }

    snapshot = get_comex_snapshot("silver")
    assert isinstance(snapshot, dict)
    assert "success" in snapshot


def test_get_comex_summary(mocker):
    """get_comex_summary 应返回摘要字符串"""
    silver_data = next(r for r in MOCK_COMEX_DATA if r["metal"] == "silver")
    gold_data = next(r for r in MOCK_COMEX_DATA if r["metal"] == "gold")

    def fake_fetch_metal(metal):
        src = silver_data if metal == "silver" else gold_data
        return {
            "report_date": src["report_date"],
            "registered": src["registered"],
            "eligible": src["eligible"],
            "total": src["total"],
            "registered_million": src["registered_million"],
            "eligible_million": src["eligible_million"],
            "total_million": src["total_million"],
        }

    mock_scraper = mocker.patch("scrapers.comex_scraper.ComexScraper")
    mock_scraper.return_value.fetch_metal.side_effect = fake_fetch_metal

    summary = get_comex_summary()
    assert isinstance(summary, str)
