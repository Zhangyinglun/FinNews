"""
测试 DataCleaner 数据清洗模块
"""

from processors.cleaner import DataCleaner


def test_data_cleaner():
    """测试 DataCleaner 数据清洗"""
    cleaner = DataCleaner()

    test_records = [
        {
            "type": "news",
            "title": "Gold prices surge as inflation concerns grow",
            "summary": "Gold futures rose sharply amid rising inflation expectations...",
            "source": "Reuters",
            "timestamp": "2026-01-20T10:00:00",
        },
        {
            "type": "news",
            "title": "<p>Silver demand increases</p>",  # 包含HTML标签
            "summary": "<b>Industrial demand</b> for silver is rising...",
            "source": "Bloomberg",
            "timestamp": "2026-01-20T11:00:00",
        },
        {
            "type": "news",
            "title": "Bitcoin hits new high",  # 黑名单关键词
            "summary": "Cryptocurrency markets rally as bitcoin reaches new record...",
            "source": "CoinDesk",
            "timestamp": "2026-01-20T12:00:00",
        },
        {
            "type": "price_data",  # 价格数据，应该保留
            "ticker": "GC=F",
            "price": 2050.12,
            "timestamp": "2026-01-20T13:00:00",
        },
        {
            "type": "economic_data",  # 经济数据，应该保留
            "indicator": "CPI",
            "value": 3.2,
            "timestamp": "2026-01-20T14:00:00",
        },
        {
            "type": "news",
            "title": "Market outlook uncertain",  # 既无白名单也无黑名单
            "summary": "Trading volumes remain low...",
            "source": "WSJ",
            "timestamp": "2026-01-20T15:00:00",
        },
    ]

    cleaned_data = cleaner.clean(test_records)

    assert len(cleaned_data) < len(test_records), "应该过滤掉一些记录"
    assert all(
        r.get("type") in ["price_data", "economic_data", "fx_data"] or "impact_tag" in r
        for r in cleaned_data
    ), "新闻记录应该有impact_tag"

    # 验证HTML清理
    html_record = next(
        (r for r in cleaned_data if "silver" in r.get("title", "").lower()), None
    )
    if html_record:
        assert "<p>" not in html_record["title"], "HTML标签应该被清除"
        assert "<b>" not in html_record["summary"], "HTML标签应该被清除"

    # 验证黑名单过滤
    bitcoin_record = next(
        (r for r in cleaned_data if "bitcoin" in r.get("title", "").lower()), None
    )
    assert bitcoin_record is None, "黑名单关键词记录应该被过滤"


def test_impact_tagging():
    """测试影响标签功能"""
    cleaner = DataCleaner()

    test_cases = [
        {
            "type": "news",
            "title": "Gold rally continues",
            "summary": "Strong demand and safe-haven buying push prices higher",
            "expected_tag": "#Bullish",
        },
        {
            "type": "news",
            "title": "Gold falls on strong dollar",
            "summary": "Dollar strength and yield rise pressure precious metals",
            "expected_tag": "#Bearish",
        },
        {
            "type": "news",
            "title": "Gold holds steady",
            "summary": "Prices remain unchanged in quiet trading",
            "expected_tag": "#Neutral",
        },
    ]

    for test_case in test_cases:
        expected = test_case.pop("expected_tag")
        cleaned = cleaner.clean([test_case])
        if cleaned:
            actual = cleaned[0].get("impact_tag")
            assert actual == expected, f"标题 '{test_case['title']}' 期望 {expected}，实际 {actual}"
