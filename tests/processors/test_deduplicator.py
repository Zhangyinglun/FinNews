"""
测试 Deduplicator 去重模块
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path

from processors.deduplicator import Deduplicator


def _build_deduplicator(
    *,
    hours: int = 24,
    threshold: float = 0.75,
    state_file: Path,
) -> Deduplicator:
    return Deduplicator(
        time_window_hours=hours,
        similarity_threshold=threshold,
        state_file=state_file,
    )


def test_exact_and_stale_and_special_types(tmp_path) -> None:
    """测试精确去重、时效过滤和特殊类型保留"""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    state_file = tmp_path / "dedup_state.json"
    deduplicator = _build_deduplicator(state_file=state_file)

    test_records = [
        {
            "type": "news",
            "title": "Gold prices rise",
            "summary": "Gold futures increased on inflation concerns",
            "source": "Reuters",
            "timestamp": now - timedelta(hours=2),
        },
        {
            "type": "news",
            "title": "Gold prices rise",
            "summary": "Gold futures increased on inflation concerns",
            "source": "Bloomberg",
            "timestamp": now - timedelta(hours=1),
        },
        {
            "type": "news",
            "title": "Silver demand grows",
            "summary": "Industrial silver demand increases",
            "source": "Kitco",
            "timestamp": now - timedelta(hours=3),
        },
        {
            "type": "news",
            "title": "Old news article",
            "summary": "This is an old article",
            "source": "WSJ",
            "timestamp": now - timedelta(hours=30),
        },
        {
            "type": "price_data",
            "ticker": "GC=F",
            "price": 2050.12,
            "timestamp": now,
        },
        {
            "type": "economic_data",
            "indicator": "CPI",
            "value": 3.2,
            "timestamp": now,
        },
        {
            "type": "fx_data",
            "pair": "USD/CNY",
            "rate": 7.23,
            "timestamp": now,
        },
    ]

    unique_data = deduplicator.deduplicate(test_records)

    news = [r for r in unique_data if r.get("type") == "news"]
    assert len(news) == 2, "应保留2条新闻（去掉1条精确重复+1条过期）"
    assert all(r.get("title") != "Old news article" for r in news), "过期新闻应被过滤"

    price_records = [r for r in unique_data if r.get("type") == "price_data"]
    economic_records = [r for r in unique_data if r.get("type") == "economic_data"]
    fx_records = [r for r in unique_data if r.get("type") == "fx_data"]
    assert len(price_records) == 1, "价格数据应保留"
    assert len(economic_records) == 1, "经济数据应保留"
    assert len(fx_records) == 1, "外汇数据应保留"


def test_fuzzy_deduplication(tmp_path) -> None:
    """测试标题模糊匹配去重"""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    state_file = tmp_path / "dedup_state.json"
    deduplicator = _build_deduplicator(state_file=state_file, threshold=0.74)

    test_records = [
        {
            "type": "news",
            "title": "Gold prices jump as Fed signals rate cuts",
            "summary": "Gold climbs after dovish Fed comments",
            "source": "Reuters",
            "timestamp": now - timedelta(hours=1),
        },
        {
            "type": "news",
            "title": "Gold price jumps as Fed hints at cutting rates",
            "summary": "Investors moved to safe-haven assets",
            "source": "Bloomberg",
            "timestamp": now - timedelta(minutes=20),
        },
    ]

    unique_data = deduplicator.deduplicate(test_records)
    news = [r for r in unique_data if r.get("type") == "news"]
    assert len(news) == 1, "相似标题应被模糊去重"


def test_cross_run_persistence(tmp_path) -> None:
    """测试跨运行持久化去重"""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    state_file = tmp_path / "dedup_state.json"

    # 第一次运行
    deduplicator1 = _build_deduplicator(state_file=state_file)
    first_batch = [
        {
            "type": "news",
            "title": "Silver demand climbs on solar growth",
            "summary": "Industrial demand pushes silver higher",
            "source": "Reuters",
            "timestamp": now - timedelta(hours=2),
        }
    ]
    out1 = deduplicator1.deduplicate(first_batch)
    assert len(out1) == 1, "首次应保留新闻"
    assert state_file.exists(), "首次运行后应生成状态文件"

    # 第二次运行（新实例）
    deduplicator2 = _build_deduplicator(state_file=state_file)
    second_batch = [
        {
            "type": "news",
            "title": "Silver demand climbs on solar growth",
            "summary": "Industrial demand pushes silver higher",
            "source": "Bloomberg",
            "timestamp": now - timedelta(minutes=30),
        }
    ]
    out2 = deduplicator2.deduplicate(second_batch)
    assert len(out2) == 0, "跨运行重复新闻应被去重"


def test_timezone_and_invalid_timestamp_handling(tmp_path) -> None:
    """测试时区处理与异常时间戳兜底"""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    state_file = tmp_path / "dedup_state.json"
    deduplicator = _build_deduplicator(state_file=state_file)

    tz_aware_time = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    bad_time = "not-a-timestamp"

    records = [
        {
            "type": "news",
            "title": "Fed keeps rates unchanged",
            "summary": "Committee waits for more inflation data",
            "source": "WSJ",
            "timestamp": tz_aware_time,
        },
        {
            "type": "news",
            "title": "US dollar index moves slightly higher",
            "summary": "Traders await payrolls report",
            "source": "CNBC",
            "timestamp": bad_time,
        },
        {
            "type": "news",
            "title": "Very old event",
            "summary": "Out of window",
            "source": "Example",
            "timestamp": now - timedelta(hours=40),
        },
    ]

    output = deduplicator.deduplicate(records)
    titles = {item.get("title") for item in output}

    assert "Fed keeps rates unchanged" in titles, "带时区的时间应被正确解析"
    assert "US dollar index moves slightly higher" in titles, "异常时间戳应回退为当前时间"
    assert "Very old event" not in titles, "超时窗口的新闻应被过滤"


def test_reset(tmp_path) -> None:
    """测试 reset 会清空内存状态并删除状态文件"""
    state_file = tmp_path / "dedup_state.json"
    deduplicator = _build_deduplicator(state_file=state_file)

    deduplicator.deduplicate(
        [
            {
                "type": "news",
                "title": "Test article",
                "summary": "Test summary",
                "timestamp": datetime.now(timezone.utc).replace(tzinfo=None),
            }
        ]
    )

    assert len(deduplicator.seen_hashes) > 0, "重置前应有哈希"
    assert len(deduplicator.seen_titles) > 0, "重置前应有标题"
    assert state_file.exists(), "重置前状态文件应存在"

    deduplicator.reset()

    assert len(deduplicator.seen_hashes) == 0, "重置后哈希应清空"
    assert len(deduplicator.seen_titles) == 0, "重置后标题应清空"
    assert not state_file.exists(), "重置后状态文件应删除"
