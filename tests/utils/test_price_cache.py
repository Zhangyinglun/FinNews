"""
测试 PriceCacheManager
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, "D:\\Projects\\FinNews")

from utils.price_cache_manager import PriceCacheManager
from config.config import Config


def test_cache_manager():
    # 使用临时缓存文件
    test_cache = Config.STORAGE_DIR / "test_price_cache.json"
    if test_cache.exists():
        test_cache.unlink()

    manager = PriceCacheManager(cache_file=test_cache)

    # 1. 测试更新
    sample_records = [
        {
            "type": "price_data",
            "ticker_name": "gold_futures",
            "ticker": "GC=F",
            "price": 2000.5,
            "change_percent": 0.5,
            "source": "Test",
            "timestamp": datetime.now(),
        }
    ]
    manager.update(sample_records)

    # 2. 测试加载
    cache = manager.load_all()
    assert "gold_futures" in cache
    assert cache["gold_futures"]["price"] == 2000.5

    # 3. 测试回退
    fallback = manager.get_fallback_records(["gold_futures", "vix"])
    assert len(fallback) == 1
    assert fallback[0]["ticker_name"] == "gold_futures"
    assert fallback[0]["is_fallback"] is True
    assert "Cache" in fallback[0]["source"]

    print("✅ PriceCacheManager 测试通过")

    # 清理
    if test_cache.exists():
        test_cache.unlink()


if __name__ == "__main__":
    test_cache_manager()
