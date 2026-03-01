"""
测试 PriceCacheManager
"""

from datetime import datetime

from utils.price_cache_manager import PriceCacheManager


def test_cache_manager(tmp_path):
    """测试缓存更新、加载与回退功能"""
    test_cache = tmp_path / "test_price_cache.json"

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
