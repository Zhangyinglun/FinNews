"""
集成测试：验证 main.py 中的价格补全 (Failover) 逻辑
"""

import sys
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime

sys.path.insert(0, "D:\\Projects\\FinNews")

from scrapers import YFinanceScraper, StooqScraper
from utils.price_cache_manager import PriceCacheManager
from config.config import Config


class TestMainFailoverLogic(unittest.TestCase):
    def setUp(self):
        self.cache_file = Config.STORAGE_DIR / "integration_test_cache.json"
        if self.cache_file.exists():
            self.cache_file.unlink()
        self.cache_manager = PriceCacheManager(cache_file=self.cache_file)

    def tearDown(self):
        if self.cache_file.exists():
            self.cache_file.unlink()

    def test_failover_flow(self):
        # 模拟初始数据：全部缺失
        all_data = [{"type": "news", "title": "Some news"}]
        required_tickers = list(Config.YFINANCE_TICKERS.keys())

        # 模拟 Stooq 返回部分数据
        stooq_mock_data = [
            {
                "type": "price_data",
                "ticker_name": "gold_futures",
                "price": 2000.0,
                "source": "Stooq_Price",
            }
        ]

        # 模拟 Cache 包含 VIX
        self.cache_manager.update(
            [
                {
                    "type": "price_data",
                    "ticker_name": "vix",
                    "price": 15.0,
                    "source": "YFinance",
                    "timestamp": datetime.now(),
                }
            ]
        )

        # --- 开始模拟 main.py 3.5 节的逻辑 ---
        existing_prices = {
            r.get("ticker_name")
            for r in all_data
            if r.get("type") == "price_data" and r.get("price", 0) > 0
        }
        missing_tickers = [t for t in required_tickers if t not in existing_prices]

        # 验证缺失 5 个
        self.assertEqual(len(missing_tickers), 5)

        # 尝试 Stooq (模拟)
        all_data.extend(stooq_mock_data)
        existing_prices.update(
            {
                r.get("ticker_name")
                for r in stooq_mock_data
                if r.get("type") == "price_data" and r.get("price", 0) > 0
            }
        )
        missing_tickers = [t for t in required_tickers if t not in existing_prices]

        # 验证缺失 4 个 (黄金已找到)
        self.assertEqual(len(missing_tickers), 4)
        self.assertIn("vix", missing_tickers)

        # 尝试 Cache
        fallback_data = self.cache_manager.get_fallback_records(missing_tickers)
        all_data.extend(fallback_data)

        # 最终验证
        final_prices = {
            r.get("ticker_name") for r in all_data if r.get("type") == "price_data"
        }
        self.assertIn("gold_futures", final_prices)
        self.assertIn("vix", final_prices)

        # 验证 VIX 来自 Cache
        vix_record = next(r for r in all_data if r.get("ticker_name") == "vix")
        self.assertTrue(vix_record.get("is_fallback"))
        self.assertEqual(vix_record.get("source"), "YFinance (Cache)")

        print("✅ main.py Failover 逻辑模拟测试通过")


if __name__ == "__main__":
    unittest.main()
