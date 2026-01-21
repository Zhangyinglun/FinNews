"""
Alpha Vantage API - 备选数据源
功能: 经济日历、外汇数据、技术指标
注意: 免费版限制较多(25 requests/天),仅作备用
"""

from typing import List, Dict, Any
from datetime import datetime

try:
    from alpha_vantage.timeseries import TimeSeries
    from alpha_vantage.foreignexchange import ForeignExchange

    ALPHAVANTAGE_AVAILABLE = True
except ImportError:
    ALPHAVANTAGE_AVAILABLE = False

from .base_scraper import BaseScraper
from config.config import Config


class AlphaVantageScraper(BaseScraper):
    """Alpha Vantage数据爬虫(可选)"""

    def __init__(self):
        super().__init__("AlphaVantage")

        if not ALPHAVANTAGE_AVAILABLE:
            raise ImportError("alpha-vantage未安装。请运行: pip install alpha-vantage")

        if not Config.ALPHA_VANTAGE_API_KEY:
            raise ValueError("ALPHA_VANTAGE_API_KEY未配置,请在.env文件中设置")

        self.api_key = Config.ALPHA_VANTAGE_API_KEY
        self.ts = TimeSeries(key=self.api_key, output_format="pandas")
        self.fx = ForeignExchange(key=self.api_key, output_format="pandas")

    def fetch(self) -> List[Dict[str, Any]]:
        """
        获取外汇和黄金数据

        Returns:
            数据记录列表

        注意: 免费版每天25次请求,谨慎使用
        """
        all_data = []

        try:
            # 美元指数(通过USD/EUR等货币对间接)
            self.logger.debug("获取USD/EUR汇率...")
            data, meta = self.fx.get_currency_exchange_daily(
                from_symbol="USD", to_symbol="EUR", outputsize="compact"
            )

            if not data.empty:
                latest = data.iloc[0]
                record = {
                    "source": "AlphaVantage",
                    "pair": "USD/EUR",
                    "close": float(latest["4. close"]),
                    "timestamp": data.index[0].to_pydatetime(),
                    "fetched_at": datetime.now(),
                    "type": "fx_data",
                }
                all_data.append(record)

            # 注意: 更多数据获取会快速消耗配额
            # 免费版建议仅在必要时启用

        except Exception as e:
            self.logger.error(f"Alpha Vantage抓取失败: {e}")

        # 应用时间窗口过滤 (12小时)，允许回退到最新数据
        filtered_data = self._filter_recent_records(
            all_data,
            window_hours=Config.FLASH_WINDOW_HOURS,
            allow_fallback=True,
            fallback_note="Alpha Vantage数据为每日发布，显示最近一次更新",
            daily_label="每日发布数据",
        )

        return filtered_data
