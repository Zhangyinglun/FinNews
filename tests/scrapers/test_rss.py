"""
测试 RSS 数据源
"""

import sys

sys.path.insert(0, "D:\\Projects\\FinNews")

from scrapers.rss_scraper import RSSFeedScraper
from utils.logger import setup_logger
import json


def test_rss_scraper():
    """测试 RSS Scraper 数据抓取"""
    # 初始化
    setup_logger()
    scraper = RSSFeedScraper()

    # 抓取数据
    print("=" * 80)
    print("正在抓取 RSS 数据...")
    print("=" * 80)

    data = scraper.run()

    print(f"\n✅ 抓取完成！共获取 {len(data)} 条记录\n")

    # 统计每个源的数量
    feed_stats = {}
    for item in data:
        feed_name = item.get("feed_name", "Unknown")
        feed_stats[feed_name] = feed_stats.get(feed_name, 0) + 1

    print("📊 各数据源统计:")
    for feed_name, count in feed_stats.items():
        print(f"  - {feed_name}: {count} 条")
    print()

    # 显示前5条详细数据
    print("📰 前5条新闻详情:")
    for idx, item in enumerate(data[:5], 1):
        print(f"\n【记录 {idx}】")
        print(f"标题: {item.get('title', 'N/A')}")
        print(f"摘要: {item.get('summary', 'N/A')[:200]}...")
        print(f"URL: {item.get('url', 'N/A')}")
        print(f"时间: {item.get('timestamp', 'N/A')}")
        print(f"来源: {item.get('feed_name', 'N/A')}")
        print("-" * 80)

    # 保存为 JSON 方便查看
    output_file = "D:\\Projects\\FinNews\\tests\\scrapers\\output_rss.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n💾 详细数据已保存到: {output_file}")

    # 断言基本验证
    assert len(data) > 0, "应该获取到至少一条数据"
    assert "feed_name" in data[0], "记录应该包含feed_name字段"


if __name__ == "__main__":
    test_rss_scraper()
