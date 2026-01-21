"""
测试 Deduplicator 去重模块
"""

import sys

sys.path.insert(0, "D:\\Projects\\FinNews")

from processors.deduplicator import Deduplicator
from utils.logger import setup_logger
from datetime import datetime, timedelta
import json


def test_deduplicator():
    """测试 Deduplicator 去重功能"""
    # 初始化
    setup_logger()
    deduplicator = Deduplicator(time_window_hours=24)

    print("=" * 80)
    print("正在测试 Deduplicator...")
    print("=" * 80)

    # 测试数据
    now = datetime.now()

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
            "title": "Gold prices rise",  # 重复内容
            "summary": "Gold futures increased on inflation concerns",
            "source": "Bloomberg",  # 不同来源，但内容相同
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
            "title": "Old news article",  # 时间窗口外
            "summary": "This is an old article",
            "source": "WSJ",
            "timestamp": now - timedelta(hours=30),  # 超过12小时窗口
        },
        {
            "type": "price_data",  # 价格数据，应该保留
            "ticker": "GC=F",
            "price": 2050.12,
            "timestamp": now,
        },
        {
            "type": "price_data",  # 价格数据，即使重复也应该保留
            "ticker": "GC=F",
            "price": 2050.12,
            "timestamp": now - timedelta(minutes=30),
        },
        {
            "type": "economic_data",  # 经济数据，应该保留
            "indicator": "CPI",
            "value": 3.2,
            "timestamp": now,
        },
    ]

    print(f"\n输入记录: {len(test_records)} 条\n")

    # 执行去重
    unique_data = deduplicator.deduplicate(test_records)

    print(f"\n✅ 去重完成！输出记录: {len(unique_data)} 条\n")

    # 显示详细结果
    print("=" * 80)
    print("去重后的数据:")
    print("=" * 80)

    for idx, record in enumerate(unique_data, 1):
        print(f"\n【记录 {idx}】")
        print(f"类型: {record.get('type', 'N/A')}")
        print(f"标题: {record.get('title', 'N/A')}")
        print(
            f"摘要: {record.get('summary', 'N/A')[:100]}..."
            if record.get("summary")
            else f"数据: {record.get('ticker') or record.get('indicator', 'N/A')}"
        )
        print(f"时间: {record.get('timestamp', 'N/A')}")
        print(f"来源: {record.get('source', 'N/A')}")
        print("-" * 80)

    # 保存结果
    output_file = "D:\\Projects\\FinNews\\tests\\processors\\output_deduplicator.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "input_count": len(test_records),
                "output_count": len(unique_data),
                "duplicates_removed": len(test_records) - len(unique_data),
                "time_window_hours": 24,
                "unique_data": unique_data,
            },
            f,
            ensure_ascii=False,
            indent=2,
            default=str,
        )

    print(f"\n💾 详细数据已保存到: {output_file}")

    # 断言验证
    assert len(unique_data) < len(test_records), "应该移除一些重复记录"

    # 验证内容去重
    news_records = [r for r in unique_data if r.get("type") == "news"]
    titles = [r.get("title") for r in news_records]
    assert len(titles) == len(set(titles)), "新闻标题不应该有重复"

    # 验证时间窗口过滤
    old_news = next(
        (r for r in unique_data if r.get("title") == "Old news article"), None
    )
    assert old_news is None, "时间窗口外的记录应该被过滤"

    # 验证价格/经济数据保留
    price_records = [r for r in unique_data if r.get("type") == "price_data"]
    economic_records = [r for r in unique_data if r.get("type") == "economic_data"]
    assert len(price_records) == 2, "价格数据应该全部保留"
    assert len(economic_records) == 1, "经济数据应该保留"

    print("\n✅ 所有断言测试通过！")


def test_reset():
    """测试重置功能"""
    print("\n" + "=" * 80)
    print("测试重置功能...")
    print("=" * 80)

    deduplicator = Deduplicator()

    # 添加一些记录
    test_records = [
        {
            "type": "news",
            "title": "Test article",
            "summary": "Test summary",
            "timestamp": datetime.now(),
        }
    ]

    deduplicator.deduplicate(test_records)
    hash_count_before = len(deduplicator.seen_hashes)
    print(f"重置前哈希数: {hash_count_before}")

    # 重置
    deduplicator.reset()
    hash_count_after = len(deduplicator.seen_hashes)
    print(f"重置后哈希数: {hash_count_after}")

    assert hash_count_before > 0, "重置前应该有哈希"
    assert hash_count_after == 0, "重置后哈希应该清空"

    print("✅ 重置功能测试通过！")
    print("=" * 80)


if __name__ == "__main__":
    test_deduplicator()
    test_reset()
