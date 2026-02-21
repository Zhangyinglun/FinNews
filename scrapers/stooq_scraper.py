"""
Stooq 行情数据抓取器 - 备选数据源
功能: 提供黄金、白银、VIX、美元指数、10年期美债的价格数据
特点: 免费、无需 API Key，作为 yfinance 的兜底
"""

import logging
import pandas as pd
import requests
from io import StringIO
from datetime import datetime
from typing import List, Dict, Any, Optional

from .base_scraper import BaseScraper
from config.config import Config


class StooqScraper(BaseScraper):
    """Stooq 行情数据抓取器"""

    def __init__(self):
        super().__init__("Stooq")
        self.tickers = Config.STOOQ_TICKERS
        self.base_url = "https://stooq.com/q/l/?s={symbol}&f=sd2t2ohlcv&h&e=csv"

    def fetch(self) -> List[Dict[str, Any]]:
        """
        获取各 ticker 的最新价格数据

        Returns:
            数据记录列表
        """
        all_data: List[Dict[str, Any]] = []

        for name, symbol in self.tickers.items():
            try:
                url = self.base_url.format(symbol=symbol)
                self.logger.debug(f"正在从 Stooq 获取 {name} ({symbol}) 数据...")

                response = requests.get(url, timeout=15)
                if response.status_code != 200:
                    self.logger.warning(
                        f"Stooq 响应异常: {response.status_code} for {symbol}"
                    )
                    continue

                # 解析 CSV
                df = pd.read_csv(StringIO(response.text))
                if df.empty or "Close" not in df.columns:
                    self.logger.warning(f"Stooq 返回数据为空或格式错误: {symbol}")
                    continue

                row = df.iloc[0]

                # 检查日期，如果数据太旧可能不适用
                # Stooq 返回格式通常是 Date, Time, Open, High, Low, Close, Volume
                # 有时 Close 为 NaN (如果市场还没开或者没数据)
                if pd.isna(row["Close"]):
                    self.logger.warning(f"Stooq {symbol} 收盘价为 NaN")
                    continue

                price = float(row["Close"])

                price_record: Dict[str, Any] = {
                    "source": "Stooq_Price",
                    "ticker": symbol,
                    "ticker_name": name,
                    "price": price,
                    "timestamp": datetime.now(),
                    "fetched_at": datetime.now(),
                    "type": "price_data",
                }

                # 计算涨跌幅 (Stooq CSV 只有当前行，无法直接计算涨跌幅，除非请求历史)
                # 但为了作为紧急兜底，拿到现价是第一优先级
                # 如果能拿到 Open，可以粗略计算日内涨幅
                if not pd.isna(row.get("Open")) and row["Open"] != 0:
                    open_price = float(row["Open"])
                    price_record["open"] = open_price
                    price_record["change"] = price - open_price
                    price_record["change_percent"] = (
                        (price - open_price) / open_price * 100
                    )

                if "High" in row and not pd.isna(row["High"]):
                    price_record["high"] = float(row["High"])
                if "Low" in row and not pd.isna(row["Low"]):
                    price_record["low"] = float(row["Low"])
                if "Volume" in row and not pd.isna(row["Volume"]):
                    price_record["volume"] = int(row["Volume"])

                all_data.append(price_record)
                self.logger.info(f"Stooq 成功获取 {name}: {price}")

            except Exception as e:
                self.logger.error(f"Stooq 抓取 {symbol} 失败: {e}")
                continue

        return all_data
