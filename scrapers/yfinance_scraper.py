"""
yfinance - 美元指数、国债收益率、VIX、金银期货
功能: 实时价格 + 相关新闻 + 历史数据对比
"""

from typing import Any, Dict, List, Optional
from datetime import datetime


try:
    import yfinance as yf

    YFINANCE_AVAILABLE = True
except ImportError:
    yf = None  # type: ignore
    YFINANCE_AVAILABLE = False

from .base_scraper import BaseScraper
from config.config import Config


class YFinanceScraper(BaseScraper):
    """yfinance数据爬虫 - 支持VIX和历史数据对比"""

    def __init__(self):
        super().__init__("YFinance")

        if not YFINANCE_AVAILABLE or yf is None:
            raise ImportError("yfinance未安装。请运行: pip install yfinance")

        self.tickers = Config.YFINANCE_TICKERS

    def fetch(self) -> List[Dict[str, Any]]:
        """
        获取各ticker的新闻和价格（含历史数据用于变化率计算）

        Returns:
            数据记录列表
        """
        all_data: List[Dict[str, Any]] = []

        # 创建Session复用(提高性能)
        session = None
        try:
            from curl_cffi import requests as curl_requests

            session = curl_requests.Session(impersonate="chrome")
        except ImportError:
            self.logger.warning("curl_cffi未安装,使用默认session(性能可能较低)")

        for name, symbol in self.tickers.items():
            try:
                if yf is None:
                    continue

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
                            title=str(content.get("title", "")),
                            summary=str(
                                content.get("summary", content.get("description", ""))
                            ),
                            url=str(content.get("link", content.get("url", ""))),
                            timestamp=self._parse_timestamp(
                                article.get("providerPublishTime")
                            ),
                            fallback_allowed=True,
                        )
                        record["ticker"] = symbol
                        record["ticker_name"] = name
                        all_data.append(record)

                except Exception as e:
                    self.logger.debug(f"{symbol}新闻获取失败: {e}")

                # 2. 获取详细价格和技术指标（含历史数据）
                try:
                    # 获取历史数据（最近5天用于计算涨跌幅）
                    hist = ticker.history(period="5d")

                    price_record: Dict[str, Any] = {
                        "source": "YFinance_Price",
                        "ticker": symbol,
                        "ticker_name": name,
                        "timestamp": datetime.now(),
                        "fetched_at": datetime.now(),
                        "type": "price_data",
                    }

                    # 获取最新价格
                    price: Optional[float] = None
                    try:
                        raw_price = ticker.fast_info.last_price
                        if raw_price is not None:
                            price = float(raw_price)  # type: ignore[arg-type]
                    except Exception:
                        try:
                            info = ticker.info
                            raw_price = info.get("regularMarketPrice") or info.get(
                                "currentPrice"
                            )
                            if raw_price is not None:
                                price = float(raw_price)
                        except Exception:
                            pass

                    if price is not None:
                        price_record["price"] = price
                    else:
                        price_record["price"] = 0.0

                    # 计算涨跌幅
                    if not hist.empty and len(hist) >= 2:
                        current_price = float(hist["Close"].iloc[-1])
                        prev_close = float(hist["Close"].iloc[-2])

                        price_record["current_price"] = current_price
                        price_record["prev_close"] = prev_close
                        price_record["change"] = current_price - prev_close

                        if prev_close != 0:
                            price_record["change_percent"] = (
                                (current_price - prev_close) / prev_close * 100
                            )
                        else:
                            price_record["change_percent"] = 0.0

                        # 计算周涨跌幅（如果有足够数据）
                        if len(hist) >= 5:
                            week_ago_price = float(hist["Close"].iloc[0])
                            if week_ago_price != 0:
                                price_record["week_change_percent"] = (
                                    (current_price - week_ago_price)
                                    / week_ago_price
                                    * 100
                                )

                        # 添加其他关键数据
                        if "Volume" in hist.columns:
                            vol = hist["Volume"].iloc[-1]
                            price_record["volume"] = int(vol) if vol else 0
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
            except Exception:
                pass
        return datetime.now()
