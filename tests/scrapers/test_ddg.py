"""
测试 DuckDuckGo Scraper
"""

import sys
import unittest
from unittest.mock import patch
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

    def test_fetch_fallback_to_text_when_news_empty(self):
        class FakeDDGS:
            def __init__(self):
                self.news_calls = []
                self.text_calls = []

            def news(self, **kwargs):
                self.news_calls.append(kwargs)
                return []

            def text(self, **kwargs):
                self.text_calls.append(kwargs)
                return [
                    {
                        "title": "示例标题",
                        "href": "http://example.com",
                        "body": "示例摘要",
                        "date": "2024-01-01T00:00:00+00:00",
                    }
                ]

        fake = FakeDDGS()
        with (
            patch("scrapers.ddg_scraper.DDGSClass", return_value=fake),
            patch("scrapers.ddg_scraper.DDG_AVAILABLE", True),
        ):
            scraper = DuckDuckGoScraper()
            scraper.flash_queries = ["gold price news"]
            scraper.cycle_queries = []
            scraper.trend_queries = []

            results = scraper.fetch()

        self.assertEqual(len(fake.news_calls), 1)
        self.assertEqual(len(fake.text_calls), 1)
        self.assertTrue(results)
        first = results[0]
        self.assertEqual(first["url"], "http://example.com")

    def test_fetch_uses_keywords_when_query_unsupported(self):
        class FakeDDGS:
            def __init__(self):
                self.news_calls = []

            def news(self, **kwargs):
                if "query" in kwargs:
                    raise TypeError("unexpected keyword argument 'query'")
                self.news_calls.append(kwargs)
                return [
                    {
                        "title": "示例标题",
                        "url": "http://example.com",
                        "body": "示例摘要",
                        "date": "2024-01-01T00:00:00+00:00",
                    }
                ]

        fake = FakeDDGS()
        with (
            patch("scrapers.ddg_scraper.DDGSClass", return_value=fake),
            patch("scrapers.ddg_scraper.DDG_AVAILABLE", True),
        ):
            scraper = DuckDuckGoScraper()
            scraper.flash_queries = ["gold price news"]
            scraper.cycle_queries = []
            scraper.trend_queries = []

            results = scraper.fetch()

        self.assertTrue(results)
        self.assertEqual(len(fake.news_calls), 1)
        self.assertIn("keywords", fake.news_calls[0])

    def test_fetch_omits_backend_when_unsupported(self):
        class FakeDDGS:
            def __init__(self):
                self.news_calls = []

            def news(self, **kwargs):
                if "backend" in kwargs:
                    raise TypeError("unexpected keyword argument 'backend'")
                self.news_calls.append(kwargs)
                return [
                    {
                        "title": "示例标题",
                        "url": "http://example.com",
                        "body": "示例摘要",
                        "date": "2024-01-01T00:00:00+00:00",
                    }
                ]

        fake = FakeDDGS()
        with (
            patch("scrapers.ddg_scraper.DDGSClass", return_value=fake),
            patch("scrapers.ddg_scraper.DDG_AVAILABLE", True),
        ):
            scraper = DuckDuckGoScraper()
            scraper.flash_queries = ["gold price news"]
            scraper.cycle_queries = []
            scraper.trend_queries = []

            results = scraper.fetch()

        self.assertTrue(results)
        self.assertEqual(len(fake.news_calls), 1)
        self.assertNotIn("backend", fake.news_calls[0])


if __name__ == "__main__":
    unittest.main()
