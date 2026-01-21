"""
yfinance - 美元指数、国债收益率、金银期货
功能: 实时价格 + 相关新闻
"""

from typing import List, Dict, Any
from datetime import datetime

try:
    import yfinance as yf

    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

from .base_scraper import BaseScraper
from config.config import Config


class YFinanceScraper(BaseScraper):
    """yfinance数据爬虫"""

    def __init__(self):
        super().__init__("YFinance")

        if not YFINANCE_AVAILABLE:
            raise ImportError("yfinance未安装。请运行: pip install yfinance")

        self.tickers = Config.YFINANCE_TICKERS

    def fetch(self) -> List[Dict[str, Any]]:
        """
        获取各ticker的新闻和价格

        Returns:
            数据记录列表
        """
        all_data = []

        # 创建Session复用(提高性能)
        try:
            from curl_cffi import requests

            session = requests.Session(impersonate="chrome")
        except ImportError:
            session = None
            self.logger.warning("curl_cffi未安装,使用默认session(性能可能较低)")

        for name, symbol in self.tickers.items():
            try:
                ticker = (
                    yf.Ticker(symbol, session=session) if session else yf.Ticker(symbol)
                )

                # 1. 获取新闻
                try:
                    news = ticker.news
                    for article in news[:5]:  # 限制每个ticker最多5条新闻
                        # 处理嵌套content结构(新版本兼容)
                        content = article.get("content", article)

                        record = self._create_base_record(
                            title=content.get("title", ""),
                            summary=content.get(
                                "summary", content.get("description", "")
                            ),
                            url=content.get("link", content.get("url", "")),
                            timestamp=self._parse_timestamp(
                                article.get("providerPublishTime")
                            ),
                        )
                        record["ticker"] = symbol
                        record["ticker_name"] = name
                        all_data.append(record)

                except Exception as e:
                    self.logger.debug(f"{symbol}新闻获取失败: {e}")

                # 2. 获取详细价格和技术指标
                try:
                    # 获取历史数据（最近5天用于计算涨跌幅）
                    hist = ticker.history(period="5d")

                    price_record = {
                        "source": "YFinance_Price",
                        "ticker": symbol,
                        "ticker_name": name,
                        "timestamp": datetime.now(),
                        "fetched_at": datetime.now(),
                        "type": "price_data",
                    }

                    # 获取最新价格
                    try:
                        price_record["price"] = float(ticker.fast_info.last_price)
                    except:
                        try:
                            info = ticker.info
                            price_record["price"] = float(
                                info.get("regularMarketPrice")
                                or info.get("currentPrice", 0)
                            )
                        except:
                            price_record["price"] = 0

                    # 计算涨跌幅
                    if not hist.empty and len(hist) >= 2:
                        current_price = hist["Close"].iloc[-1]
                        prev_close = hist["Close"].iloc[-2]

                        price_record["current_price"] = float(current_price)
                        price_record["prev_close"] = float(prev_close)
                        price_record["change"] = float(current_price - prev_close)
                        price_record["change_percent"] = float(
                            (current_price - prev_close) / prev_close * 100
                        )

                        # 计算周涨跌幅（如果有足够数据）
                        if len(hist) >= 5:
                            week_ago_price = hist["Close"].iloc[0]
                            price_record["week_change_percent"] = float(
                                (current_price - week_ago_price) / week_ago_price * 100
                            )

                        # 添加其他关键数据
                        price_record["volume"] = (
                            int(hist["Volume"].iloc[-1])
                            if "Volume" in hist.columns
                            else 0
                        )
                        price_record["high"] = float(hist["High"].iloc[-1])
                        price_record["low"] = float(hist["Low"].iloc[-1])
                        price_record["open"] = float(hist["Open"].iloc[-1])

                        # 计算简单移动平均线（5日）
                        if len(hist) >= 5:
                            price_record["ma5"] = float(hist["Close"].tail(5).mean())

                    if price_record.get("price", 0) > 0:
                        all_data.append(price_record)

                except Exception as e:
                    self.logger.warning(f"无法获取{symbol}详细数据: {e}")

            except Exception as e:
                self.logger.error(f"抓取{symbol}失败: {e}")
                continue

        return all_data

    @staticmethod
    def _parse_timestamp(ts: Any) -> datetime:
        """
        将Unix时间戳转为datetime

        Args:
            ts: Unix时间戳或其他格式

        Returns:
            datetime对象
        """
        if ts:
            try:
                return datetime.fromtimestamp(ts)
            except:
                pass
        return datetime.now()
