"""
FRED API - 圣路易斯联储经济数据
数据: CPI, PCE, NFP, GDP等宏观指标
"""

from typing import List, Dict, Any
from datetime import datetime, timedelta

try:
    from fredapi import Fred

    FREDAPI_AVAILABLE = True
except ImportError:
    FREDAPI_AVAILABLE = False

from .base_scraper import BaseScraper
from config.config import Config

# 每日/低频发布的指标 (用于标记)
DAILY_RELEASE_INDICATORS = {
    "cpi",
    "core_cpi",
    "pce",
    "core_pce",
    "nonfarm_payroll",
    "unemployment",
    "fed_funds",
    "gdp",
    "m1",
    "m2",
}


class FREDScraper(BaseScraper):
    """FRED经济数据爬虫"""

    def __init__(self):
        super().__init__("FRED")

        if not FREDAPI_AVAILABLE:
            raise ImportError("fredapi未安装。请运行: pip install fredapi")

        if not Config.FRED_API_KEY:
            raise ValueError("FRED_API_KEY未配置,请在.env文件中设置")

        self.client = Fred(api_key=Config.FRED_API_KEY)
        self.series_ids = Config.FRED_SERIES

    def fetch(self) -> List[Dict[str, Any]]:
        """
        获取最新经济指标

        Returns:
            经济数据列表
        """
        all_data = []

        for indicator_name, series_id in self.series_ids.items():
            try:
                # 获取最近3个月数据(原始值)
                end_date = datetime.now()
                start_date = end_date - timedelta(days=90)

                # 获取原始数据,不使用同比变化
                data_series = self.client.get_series(
                    series_id,
                    observation_start=start_date.strftime("%Y-%m-%d"),
                    observation_end=end_date.strftime("%Y-%m-%d"),
                )

                if data_series.empty:
                    self.logger.debug(f"{indicator_name}暂无数据")
                    continue

                # 获取最新值
                latest_value = data_series.iloc[-1]
                latest_date = data_series.index[-1]

                # 计算变化(与前一期比较)
                change = None
                change_pct = None
                if len(data_series) > 1:
                    prev_value = data_series.iloc[-2]
                    change = latest_value - prev_value
                    if prev_value != 0:
                        change_pct = (change / prev_value) * 100

                record = {
                    "source": "FRED",
                    "indicator": indicator_name,
                    "series_id": series_id,
                    "value": round(float(latest_value), 4),
                    "change": round(float(change), 4) if change is not None else None,
                    "change_pct": round(float(change_pct), 2)
                    if change_pct is not None
                    else None,
                    "timestamp": latest_date.to_pydatetime(),
                    "fetched_at": datetime.now(),
                    "type": "economic_data",
                }

                # 标记每日发布数据
                if indicator_name in DAILY_RELEASE_INDICATORS:
                    record["daily_label"] = "每日发布数据"

                all_data.append(record)

            except Exception as e:
                self.logger.error(f"FRED抓取失败 {indicator_name} ({series_id}): {e}")
                continue

        # 应用时间窗口过滤 (12小时)，允许回退到最新数据
        filtered_data = self._filter_recent_records(
            all_data,
            window_hours=Config.FLASH_WINDOW_HOURS,
            allow_fallback=True,
            fallback_note="FRED数据为低频发布，显示最近一次更新",
            daily_label="每日发布数据",
        )

        return filtered_data
