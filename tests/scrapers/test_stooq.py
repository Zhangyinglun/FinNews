"""
测试 StooqScraper 是否能正常获取行情
"""

import sys

sys.path.insert(0, "D:\\Projects\\FinNews")

from scrapers.stooq_scraper import StooqScraper
from config.config import Config


def test_stooq_fetch():
    scraper = StooqScraper()
    print(f"正在测试 Stooq 抓取: {list(scraper.tickers.keys())}")
    data = scraper.fetch()

    for item in data:
        print(
            f"✅ {item['ticker_name']} ({item['ticker']}): {item['price']} (Change: {item.get('change_percent', 'N/A')}%)"
        )

    assert len(data) > 0, "未能从 Stooq 获取任何数据"
    print(f"\n成功获取 {len(data)} 条 Stooq 记录")


if __name__ == "__main__":
    test_stooq_fetch()
