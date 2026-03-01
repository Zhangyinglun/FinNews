"""
测试 DuckDuckGo Scraper
"""

import unittest
from unittest.mock import patch

from scrapers.ddg_scraper import DuckDuckGoScraper


class TestDuckDuckGoScraper(unittest.TestCase):
    def setUp(self):
        self.scraper = DuckDuckGoScraper()
        self.scraper.flash_queries = ["gold price news"]
        self.scraper.cycle_queries = []
        self.scraper.trend_queries = []

    def test_fetch(self):
        """mock DDG 搜索，验证返回格式"""
        class FakeDDGS:
            def news(self, **kwargs):
                return [
                    {
                        "title": "Gold prices steady",
                        "url": "http://example.com/gold",
                        "body": "Gold remains steady amid market uncertainty",
                        "date": "2026-03-01T10:00:00+00:00",
                        "source": "Reuters",
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

        self.assertIsInstance(results, list)
        self.assertTrue(len(results) > 0)
        first = results[0]
        self.assertEqual(first["source"], "duckduckgo")
        self.assertIn("title", first)
        self.assertIn("url", first)
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
