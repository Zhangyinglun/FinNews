"""
测试 DuckDuckGo Scraper
"""

import sys
import unittest
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scrapers.ddg_scraper import DuckDuckGoScraper
from config.config import Config


class TestDuckDuckGoScraper(unittest.TestCase):
    def setUp(self):
        self.scraper = DuckDuckGoScraper()
        # 使用少量查询以加快测试
        self.scraper.flash_queries = ["gold price news"]
        self.scraper.cycle_queries = []
        self.scraper.trend_queries = []

    def test_fetch(self):
        print("\n正在测试 DDG 抓取 (可能需要几秒钟)...")
        results = self.scraper.fetch()

        self.assertIsInstance(results, list)
        if not results:
            print("警告: DDG 未返回任何结果 (可能是网络问题或没有任何匹配)")
            return

        print(f"抓取到 {len(results)} 条结果")
        first = results[0]
        print(f"示例: {first.get('title')} ({first.get('url')})")

        self.assertEqual(first["source"], "duckduckgo")
        self.assertTrue("title" in first)
        self.assertTrue("url" in first)
        self.assertEqual(first["type"], "news")


if __name__ == "__main__":
    unittest.main()
