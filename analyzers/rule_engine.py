"""
规则引擎
根据预设阈值判断市场状态，生成预处理标记
"""

import logging
from typing import Any, Dict, List, Optional

from config.config import Config
from models.analysis import (
    AlertLevel,
    ComexAlertLevel,
    ComexSignal,
    MacroBias,
    MarketSignal,
)

logger = logging.getLogger("analyzers.rule_engine")


class RuleEngine:
    """
    规则引擎

    职责:
    1. VIX绝对值阈值判断 (VIX > 20 → 警戒)
    2. VIX暴涨检测 (日变化 > 5% → 紧急)
    3. DXY + US10Y 组合判断 (同涨 → 利空黄金)
    4. 生成 sentiment_score
    """

    def __init__(self):
        """初始化规则引擎，加载配置阈值"""
        self.vix_threshold = Config.VIX_ALERT_THRESHOLD
        self.vix_spike_pct = Config.VIX_SPIKE_PERCENT
        self.dxy_threshold = Config.DXY_CHANGE_THRESHOLD
        self.us10y_threshold = Config.US10Y_CHANGE_THRESHOLD

        logger.info(
            f"规则引擎初始化 | VIX阈值={self.vix_threshold} "
            f"VIX暴涨={self.vix_spike_pct}% DXY阈值={self.dxy_threshold}%"
        )

    def analyze(self, price_data: List[Dict[str, Any]]) -> MarketSignal:
        """
        分析价格数据，生成市场信号

        Args:
            price_data: yfinance抓取的价格数据列表

        Returns:
            MarketSignal 对象
        """
        signal = MarketSignal()
        alerts: List[str] = []

        # 提取各资产数据
        vix_data = self._find_ticker_data(price_data, "vix", "^VIX")
        dxy_data = self._find_ticker_data(price_data, "dollar_index", "DX-Y.NYB")
        us10y_data = self._find_ticker_data(price_data, "treasury_10y", "^TNX")
        gold_data = self._find_ticker_data(price_data, "gold_futures", "GC=F")
        silver_data = self._find_ticker_data(price_data, "silver_futures", "SI=F")

        # === VIX 分析 ===
        if vix_data:
            signal.vix_value = vix_data.get("price") or vix_data.get("current_price")
            signal.vix_prev_close = vix_data.get("prev_close")
            signal.vix_change_percent = vix_data.get("change_percent")

            # VIX 绝对值警戒
            if signal.vix_value and signal.vix_value > self.vix_threshold:
                signal.vix_alert_level = AlertLevel.WARNING
                alerts.append(
                    f"⚠️ VIX={signal.vix_value:.1f} 超过警戒线{self.vix_threshold}"
                )
                logger.warning(
                    f"VIX警戒触发: {signal.vix_value:.1f} > {self.vix_threshold}"
                )

            # VIX 暴涨检测
            if (
                signal.vix_change_percent
                and signal.vix_change_percent > self.vix_spike_pct
            ):
                signal.vix_alert_level = AlertLevel.CRITICAL
                signal.is_urgent = True
                alerts.append(
                    f"🔴 VIX暴涨 {signal.vix_change_percent:.1f}% 触发紧急警报"
                )
                logger.critical(f"VIX暴涨警报: {signal.vix_change_percent:.1f}%")

        # === DXY 分析 ===
        if dxy_data:
            signal.dxy_value = dxy_data.get("price") or dxy_data.get("current_price")
            signal.dxy_change_percent = dxy_data.get("change_percent")

        # === US10Y 分析 ===
        if us10y_data:
            signal.us10y_value = us10y_data.get("price") or us10y_data.get(
                "current_price"
            )
            signal.us10y_change_percent = us10y_data.get("change_percent")

        # === 贵金属价格 ===
        if gold_data:
            signal.gold_price = gold_data.get("price") or gold_data.get("current_price")
            signal.gold_change_percent = gold_data.get("change_percent")

        if silver_data:
            signal.silver_price = silver_data.get("price") or silver_data.get(
                "current_price"
            )
            signal.silver_change_percent = silver_data.get("change_percent")

        # === 宏观倾向判断 ===
        signal.macro_bias = self._determine_macro_bias(
            dxy_change=signal.dxy_change_percent,
            us10y_change=signal.us10y_change_percent,
            alerts=alerts,
        )

        # === 情感评分计算 ===
        signal.sentiment_score = self._calculate_sentiment_score(signal)

        signal.alert_messages = alerts

        logger.info(
            f"规则引擎分析完成 | VIX={signal.vix_value} "
            f"Alert={signal.vix_alert_level.value} "
            f"Bias={signal.macro_bias.value} "
            f"Score={signal.sentiment_score:.2f} "
            f"Urgent={signal.is_urgent}"
        )

        return signal

    def _find_ticker_data(
        self, price_data: List[Dict[str, Any]], ticker_name: str, ticker_symbol: str
    ) -> Optional[Dict[str, Any]]:
        """
        从价格数据列表中查找指定ticker的数据

        Args:
            price_data: 价格数据列表
            ticker_name: ticker名称 (如 "vix")
            ticker_symbol: ticker代码 (如 "^VIX")

        Returns:
            找到的数据字典，或None
        """
        for record in price_data:
            if record.get("type") != "price_data":
                continue
            if (
                record.get("ticker_name") == ticker_name
                or record.get("ticker") == ticker_symbol
            ):
                return record
        return None

    def _determine_macro_bias(
        self,
        dxy_change: Optional[float],
        us10y_change: Optional[float],
        alerts: List[str],
    ) -> MacroBias:
        """
        判断宏观倾向

        规则:
        - DXY↑ + US10Y↑ → 利空黄金 (美元强+利率升=黄金承压)
        - DXY↓ + US10Y↓ → 利多黄金 (美元弱+利率降=黄金受益)
        - 其他情况 → 中性

        Args:
            dxy_change: 美元指数变化百分比
            us10y_change: 10年期收益率变化百分比
            alerts: 警报消息列表(用于添加判断说明)

        Returns:
            MacroBias枚举值
        """
        if dxy_change is None or us10y_change is None:
            return MacroBias.NEUTRAL

        dxy_up = dxy_change > self.dxy_threshold
        dxy_down = dxy_change < -self.dxy_threshold
        us10y_up = us10y_change > self.us10y_threshold
        us10y_down = us10y_change < -self.us10y_threshold

        if dxy_up and us10y_up:
            alerts.append(
                f"📉 美元指数({dxy_change:+.2f}%)与10Y收益率({us10y_change:+.2f}%)同涨 → 宏观利空黄金"
            )
            return MacroBias.BEARISH

        if dxy_down and us10y_down:
            alerts.append(
                f"📈 美元指数({dxy_change:+.2f}%)与10Y收益率({us10y_change:+.2f}%)同跌 → 宏观利多黄金"
            )
            return MacroBias.BULLISH

        return MacroBias.NEUTRAL

    def _calculate_sentiment_score(self, signal: MarketSignal) -> float:
        """
        计算情感评分 (-1.0 到 1.0)

        评分规则:
        - 基础分 0
        - VIX高 → +分 (避险情绪利多黄金)
        - VIX暴涨 → +分
        - DXY涨 → -分
        - US10Y涨 → -分
        - 黄金涨 → +分

        Args:
            signal: MarketSignal对象

        Returns:
            -1.0 到 1.0 的情感评分
        """
        score = 0.0

        # VIX 因子 (高VIX利多黄金)
        if signal.vix_value:
            if signal.vix_value > 30:
                score += 0.3
            elif signal.vix_value > 25:
                score += 0.2
            elif signal.vix_value > 20:
                score += 0.1

        # VIX变化因子
        if signal.vix_change_percent:
            if signal.vix_change_percent > 10:
                score += 0.2
            elif signal.vix_change_percent > 5:
                score += 0.1

        # DXY因子 (美元强利空黄金)
        if signal.dxy_change_percent:
            if signal.dxy_change_percent > 0.5:
                score -= 0.15
            elif signal.dxy_change_percent < -0.5:
                score += 0.15

        # US10Y因子 (收益率升利空黄金)
        if signal.us10y_change_percent:
            if signal.us10y_change_percent > 2:
                score -= 0.15
            elif signal.us10y_change_percent < -2:
                score += 0.15

        # 黄金自身走势
        if signal.gold_change_percent:
            if signal.gold_change_percent > 1:
                score += 0.1
            elif signal.gold_change_percent < -1:
                score -= 0.1

        # 限制范围
        return max(-1.0, min(1.0, score))

    def analyze_comex(self, comex_data: List[Dict[str, Any]]) -> ComexSignal:
        """
        分析COMEX库存数据，生成预警信号

        Args:
            comex_data: ComexScraper抓取的库存数据列表

        Returns:
            ComexSignal 对象
        """
        signal = ComexSignal()

        for record in comex_data:
            if record.get("type") != "inventory_data":
                continue

            metal = record.get("metal")
            registered = record.get("registered")
            registered_m = record.get("registered_million")
            total = record.get("total")
            weekly_change_pct = record.get("registered_weekly_change_pct")
            report_date = record.get("report_date")

            if report_date and signal.report_date is None:
                signal.report_date = report_date

            if metal == "silver":
                signal.silver_registered = registered
                signal.silver_registered_million = registered_m
                signal.silver_total = total
                signal.silver_weekly_change_pct = weekly_change_pct

                if registered is not None:
                    alert_info = self._calculate_comex_alert(registered, metal="silver")
                    signal.silver_alert_level = alert_info["level"]
                    signal.silver_alert_message = alert_info["message"]
                    signal.silver_recommendation = alert_info["recommendation"]
                    if alert_info["is_emergency"]:
                        signal.has_emergency = True

            elif metal == "gold":
                signal.gold_registered = registered
                signal.gold_registered_million = registered_m
                signal.gold_total = total
                signal.gold_weekly_change_pct = weekly_change_pct

                if registered is not None:
                    alert_info = self._calculate_comex_alert(registered, metal="gold")
                    signal.gold_alert_level = alert_info["level"]
                    signal.gold_alert_message = alert_info["message"]
                    signal.gold_recommendation = alert_info["recommendation"]
                    if alert_info["is_emergency"]:
                        signal.has_emergency = True

        # 记录日志
        worst_level = signal.get_worst_alert_level()
        logger.info(
            f"COMEX分析完成 | 白银={signal.silver_registered_million}M oz "
            f"({signal.silver_alert_level.value}) | "
            f"黄金={signal.gold_registered_million}M oz "
            f"({signal.gold_alert_level.value}) | "
            f"最高警报={worst_level.value}"
        )

        return signal

    def _calculate_comex_alert(self, registered: float, metal: str) -> Dict[str, Any]:
        """
        计算COMEX库存预警级别

        Args:
            registered: Registered库存量 (盎司)
            metal: 金属类型 ("silver" 或 "gold")

        Returns:
            包含预警信息的字典
        """
        registered_m = round(registered / 1_000_000, 2)

        # 获取阈值
        if metal == "silver":
            yellow = Config.COMEX_SILVER_YELLOW_THRESHOLD
            red = Config.COMEX_SILVER_RED_THRESHOLD
            failure = Config.COMEX_SILVER_FAILURE_THRESHOLD
            metal_cn = "白银"
            etf_paper = "SLV"
            etf_physical = "PSLV"
        else:  # gold
            yellow = Config.COMEX_GOLD_YELLOW_THRESHOLD
            red = Config.COMEX_GOLD_RED_THRESHOLD
            failure = Config.COMEX_GOLD_FAILURE_THRESHOLD
            metal_cn = "黄金"
            etf_paper = "GLD"
            etf_physical = "PHYS"

        yellow_m = round(yellow / 1_000_000, 1)
        red_m = round(red / 1_000_000, 1)
        failure_m = round(failure / 1_000_000, 1)

        if registered < failure:
            logger.critical(
                f"COMEX {metal} 熔断警报! {registered_m}M oz < {failure_m}M oz"
            )
            return {
                "level": ComexAlertLevel.SYSTEM_FAILURE,
                "message": (
                    f"⚫ {metal_cn}库存 {registered_m}M oz 跌破熔断线({failure_m}M)！"
                    f"纸{metal_cn}面临系统性脱钩风险"
                ),
                "recommendation": f"紧急撤离所有纸{metal_cn}资产，只持有实物",
                "is_emergency": True,
            }
        elif registered < red:
            logger.error(f"COMEX {metal} 红色警报! {registered_m}M oz < {red_m}M oz")
            return {
                "level": ComexAlertLevel.RED,
                "message": (
                    f"🔴 {metal_cn}库存 {registered_m}M oz 跌破生死线({red_m}M)！"
                    f"脱钩风险急剧上升"
                ),
                "recommendation": f"清仓 {etf_paper}，换成 {etf_physical} 或实物{metal_cn}",
                "is_emergency": False,
            }
        elif registered < yellow:
            logger.warning(
                f"COMEX {metal} 黄色警报! {registered_m}M oz < {yellow_m}M oz"
            )
            return {
                "level": ComexAlertLevel.YELLOW,
                "message": (
                    f"🟡 {metal_cn}库存 {registered_m}M oz 跌破警戒线({yellow_m}M)，"
                    f"市场趋紧"
                ),
                "recommendation": f"{etf_paper} 暂时安全，关注溢价变化，考虑部分换仓 {etf_physical}",
                "is_emergency": False,
            }
        else:
            return {
                "level": ComexAlertLevel.SAFE,
                "message": f"🟢 {metal_cn}库存 {registered_m}M oz 处于安全水平",
                "recommendation": f"{etf_paper} 正常持有，无需担忧",
                "is_emergency": False,
            }
