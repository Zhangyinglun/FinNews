"""
价格缓存管理器
功能: 持久化存储最新的价格数据，在所有实时数据源失效时提供回退
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

from config.config import Config

logger = logging.getLogger("utils.price_cache")


class PriceCacheManager:
    """管理价格数据的本地缓存"""

    def __init__(self, cache_file: Optional[Path] = None):
        self.cache_file = cache_file or Config.STORAGE_DIR / "price_cache.json"
        # 确保目录存在
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)

    def update(self, price_records: List[Dict[str, Any]]):
        """
        使用新的价格记录更新缓存

        Args:
            price_records: 包含 type="price_data" 的记录列表
        """
        if not price_records:
            return

        cache = self.load_all()

        updated = False
        for record in price_records:
            if record.get("type") != "price_data":
                continue

            ticker_name = record.get("ticker_name")
            if not ticker_name:
                continue

            # 更新该 ticker 的缓存
            cache[ticker_name] = {
                "price": record.get("price"),
                "change_percent": record.get("change_percent"),
                "ticker": record.get("ticker"),
                "source": record.get("source"),
                "timestamp": record.get("timestamp"),
                "is_cache": True,  # 标记这是缓存数据
                "cached_at": datetime.now().isoformat(),
            }
            updated = True

        if updated:
            self._save(cache)
            logger.debug(f"价格缓存已更新: {list(cache.keys())}")

    def load_all(self) -> Dict[str, Any]:
        """加载所有缓存的价格数据"""
        if not self.cache_file.exists():
            return {}

        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data
        except Exception as e:
            logger.error(f"加载价格缓存失败: {e}")
            return {}

    def get_fallback_records(
        self, missing_ticker_names: List[str]
    ) -> List[Dict[str, Any]]:
        """
        获取缺失 ticker 的回退记录

        Args:
            missing_ticker_names: 缺失的 ticker 名称列表 (如 ["gold_futures", "vix"])

        Returns:
            price_data 格式的记录列表
        """
        cache = self.load_all()
        fallback_records = []

        for name in missing_ticker_names:
            if name in cache:
                data = cache[name]
                record = {
                    "type": "price_data",
                    "ticker_name": name,
                    "ticker": data.get("ticker"),
                    "price": data.get("price"),
                    "change_percent": data.get("change_percent"),
                    "source": f"{data.get('source', 'Unknown')} (Cache)",
                    "timestamp": data.get("timestamp"),
                    "is_fallback": True,
                    "fallback_note": f"实时数据获取失败，显示缓存于 {data.get('cached_at', '未知时间')} 的数据",
                }
                fallback_records.append(record)
                logger.info(f"使用缓存回退数据: {name}")

        return fallback_records

    def _save(self, cache: Dict[str, Any]):
        """保存缓存到文件"""
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(cache, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            logger.error(f"保存价格缓存失败: {e}")
