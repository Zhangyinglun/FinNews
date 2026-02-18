"""
测试 yfinance 数据源
"""

import os
from pathlib import Path
import sys
import json

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scrapers.yfinance_scraper import YFinanceScraper
from utils.logger import setup_logger


def test_yfinance_scraper():
    """测试 YFinance Scraper 数据抓取"""
    # 初始化
    setup_logger()
    scraper = YFinanceScraper()

    # 抓取数据
    print("=" * 80)
    print("正在抓取 yfinance 数据...")
    print("=" * 80)

    data = scraper.run()

    print(f"\n✅ 抓取完成！共获取 {len(data)} 条记录\n")

    # 按类型分组
    news_items = [d for d in data if d.get("type") != "price_data"]
    price_items = [d for d in data if d.get("type") == "price_data"]

    print(f"📰 新闻数据: {len(news_items)} 条")
    print(f"💰 价格数据: {len(price_items)} 条")
    print("=" * 80)

    # 显示价格数据
    if price_items:
        print("\n【价格与技术指标数据】")
        print("=" * 80)
        for idx, item in enumerate(price_items, 1):
            print(
                f"\n{idx}. {item.get('ticker_name', 'N/A')} ({item.get('ticker', 'N/A')})"
            )
            print(f"   当前价格: ${item.get('price', 0):.2f}")

            if "change" in item:
                print(
                    f"   日涨跌: {item['change']:+.2f} ({item.get('change_percent', 0):+.2f}%)"
                )

            if "week_change_percent" in item:
                print(f"   周涨跌: {item['week_change_percent']:+.2f}%")

            if "high" in item and "low" in item:
                print(f"   今日区间: ${item['low']:.2f} - ${item['high']:.2f}")

            if "volume" in item and item["volume"] > 0:
                print(f"   成交量: {item['volume']:,}")

            if "ma5" in item:
                print(f"   5日均线: ${item['ma5']:.2f}")

            print("-" * 80)

    # 显示新闻数据
    if news_items:
        print("\n【新闻数据】")
        print("=" * 80)
        for idx, item in enumerate(news_items, 1):
            print(f"\n{idx}. [{item.get('ticker_name', 'N/A')}]")
            print(f"   标题: {item.get('title', 'N/A')}")
            print(f"   摘要: {item.get('summary', 'N/A')[:150]}...")
            print(f"   URL: {item.get('url', 'N/A')}")
            print(f"   时间: {item.get('timestamp', 'N/A')}")
            print("-" * 80)

    # 保存为 JSON
    output_file = str(Path(__file__).resolve().parent / "output_yfinance.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n💾 详细数据已保存到: {output_file}")

    # 断言基本验证
    if os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"):
        if len(data) == 0 or len(price_items) == 0:
            print("⚠️ CI 环境下数据为空，跳过断言")
            return

    assert len(data) > 0, "应该获取到至少一条数据"
    assert len(price_items) > 0, "应该至少有一条价格数据"


if __name__ == "__main__":
    test_yfinance_scraper()
