"""
测试 DataCleaner 数据清洗模块
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from processors.cleaner import DataCleaner
from utils.logger import setup_logger
import json


def test_data_cleaner():
    """测试 DataCleaner 数据清洗"""
    # 初始化
    setup_logger()
    cleaner = DataCleaner()

    print("=" * 80)
    print("正在测试 DataCleaner...")
    print("=" * 80)

    # 测试数据
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

    print(f"\n输入记录: {len(test_records)} 条\n")

    # 执行清洗
    cleaned_data = cleaner.clean(test_records)

    print(f"\n✅ 清洗完成！输出记录: {len(cleaned_data)} 条\n")

    # 显示详细结果
    print("=" * 80)
    print("清洗后的数据:")
    print("=" * 80)

    for idx, record in enumerate(cleaned_data, 1):
        print(f"\n【记录 {idx}】")
        print(f"类型: {record.get('type', 'N/A')}")
        print(f"标题: {record.get('title', 'N/A')}")
        print(f"摘要: {record.get('summary', 'N/A')[:100]}...")
        print(f"影响标签: {record.get('impact_tag', 'N/A')}")
        print(f"来源: {record.get('source', 'N/A')}")
        print("-" * 80)

    # 保存结果
    output_file = "str(Path(__file__).resolve().parent / 'output_cleaner.json')"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "input_count": len(test_records),
                "output_count": len(cleaned_data),
                "filtered_count": len(test_records) - len(cleaned_data),
                "cleaned_data": cleaned_data,
            },
            f,
            ensure_ascii=False,
            indent=2,
            default=str,
        )

    print(f"\n💾 详细数据已保存到: {output_file}")

    # 断言验证
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

    print("\n✅ 所有断言测试通过！")


def test_impact_tagging():
    """测试影响标签功能"""
    print("\n" + "=" * 80)
    print("测试影响标签功能...")
    print("=" * 80)

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

    for idx, test_case in enumerate(test_cases, 1):
        expected = test_case.pop("expected_tag")
        cleaned = cleaner.clean([test_case])
        if cleaned:
            actual = cleaned[0].get("impact_tag")
            status = "✅" if actual == expected else "❌"
            print(f"{idx}. {status} 期望: {expected}, 实际: {actual}")
            print(f"   标题: {test_case['title']}")
        else:
            print(f"{idx}. ❌ 记录被过滤")

    print("=" * 80)


if __name__ == "__main__":
    test_data_cleaner()
    test_impact_tagging()
