"""
市场分析器
整合多时间窗口数据，组织LLM输入
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from config.config import Config
from models.market_data import (
    FlashWindowData,
    CycleWindowData,
    TrendWindowData,
    MultiWindowData,
    NewsItem,
)
from models.analysis import MarketSignal, ComexSignal, ComexAlertLevel

logger = logging.getLogger("analyzers.market_analyzer")


class MarketAnalyzer:
    """
    市场分析器

    职责:
    1. 将原始数据按时间窗口分组
    2. 构建结构化的多窗口数据
    3. 生成LLM友好的输入格式
    """

    def __init__(self):
        """初始化市场分析器"""
        self.flash_hours = Config.FLASH_WINDOW_HOURS
        self.cycle_days = Config.CYCLE_WINDOW_DAYS
        self.trend_days = Config.TREND_WINDOW_DAYS

        logger.info(
            f"市场分析器初始化 | Flash={self.flash_hours}h "
            f"Cycle={self.cycle_days}d Trend={self.trend_days}d"
        )

    def organize_data(
        self, all_records: List[Dict[str, Any]], signal: MarketSignal
    ) -> MultiWindowData:
        """
        组织多窗口数据

        Args:
            all_records: 所有原始记录
            signal: 规则引擎生成的市场信号

        Returns:
            MultiWindowData 对象
        """
        # 分离不同类型数据
        price_records = [r for r in all_records if r.get("type") == "price_data"]
        economic_records = [r for r in all_records if r.get("type") == "economic_data"]
        news_records = [
            r
            for r in all_records
            if r.get("type") not in ("price_data", "economic_data", "fx_data")
        ]

        # 按窗口类型分组新闻
        flash_news = [r for r in news_records if r.get("window_type") == "flash"]
        cycle_news = [r for r in news_records if r.get("window_type") == "cycle"]
        trend_news = [r for r in news_records if r.get("window_type") == "trend"]

        # 未标记窗口类型的新闻默认归入flash
        untagged_news = [r for r in news_records if r.get("window_type") is None]
        flash_news.extend(untagged_news)

        # 构建Flash窗口数据
        flash_data = FlashWindowData(
            vix_value=signal.vix_value,
            vix_prev_close=signal.vix_prev_close,
            vix_change_percent=signal.vix_change_percent,
            dxy_value=signal.dxy_value,
            dxy_change_percent=signal.dxy_change_percent,
            us10y_value=signal.us10y_value,
            us10y_change_percent=signal.us10y_change_percent,
            gold_price=signal.gold_price,
            gold_change_percent=signal.gold_change_percent,
            silver_price=signal.silver_price,
            silver_change_percent=signal.silver_change_percent,
            news=[self._to_news_item(r, "flash") for r in flash_news],
            price_records=price_records,
        )

        # 构建Cycle窗口数据
        cycle_data = CycleWindowData(
            news=[self._to_news_item(r, "cycle") for r in cycle_news],
            economic_records=economic_records,
        )

        # 从经济数据中提取关键指标
        for record in economic_records:
            indicator = record.get("indicator", "").lower()
            if "cpi" in indicator:
                cycle_data.cpi_actual = record.get("value")
            elif "pce" in indicator:
                cycle_data.pce_actual = record.get("value")
            elif "nonfarm" in indicator or "payroll" in indicator:
                cycle_data.nfp_actual = record.get("value")
            elif "fed_funds" in indicator:
                cycle_data.fed_rate = record.get("value")

        # 构建Trend窗口数据
        trend_data = TrendWindowData(
            news=[self._to_news_item(r, "trend") for r in trend_news],
        )

        # 汇总
        multi_window = MultiWindowData(
            flash=flash_data,
            cycle=cycle_data,
            trend=trend_data,
            all_records=all_records,
        )

        logger.info(
            f"数据组织完成 | Flash新闻={len(flash_data.news)} "
            f"Cycle新闻={len(cycle_data.news)} Trend新闻={len(trend_data.news)} "
            f"价格记录={len(price_records)} 经济记录={len(economic_records)}"
        )

        return multi_window

    def _to_news_item(self, record: Dict[str, Any], window_type: str) -> NewsItem:
        """
        将原始记录转换为NewsItem

        Args:
            record: 原始记录字典
            window_type: 时间窗口类型

        Returns:
            NewsItem对象
        """
        timestamp = record.get("timestamp")
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp)
            except:
                timestamp = datetime.now()
        elif not isinstance(timestamp, datetime):
            timestamp = datetime.now()

        return NewsItem(
            title=record.get("title", ""),
            summary=record.get("summary", ""),
            url=record.get("url", ""),
            source=record.get("source", "Unknown"),
            timestamp=timestamp,
            impact_tag=record.get("impact_tag"),
            relevance_score=record.get("relevance_score"),
            full_content=record.get("full_content"),
            window_type=window_type,
        )

    def build_llm_prompt(self, data: MultiWindowData, signal: MarketSignal) -> str:
        """
        构建LLM输入提示

        Args:
            data: 多窗口数据
            signal: 市场信号

        Returns:
            LLM用户提示字符串
        """
        lines = []
        now = datetime.now()

        # 元数据
        lines.append(f"数据生成时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # === 规则引擎预处理标记 ===
        lines.append("=" * 50)
        lines.append("【规则引擎预处理结果】")
        lines.append("=" * 50)
        lines.append(f"VIX警报级别: {signal.vix_alert_level.value}")
        lines.append(f"宏观倾向: {signal.macro_bias.value}")
        lines.append(f"情感评分: {signal.sentiment_score:.2f} (-1利空, +1利多)")
        lines.append(f"紧急警报: {'是' if signal.is_urgent else '否'}")
        if signal.alert_messages:
            lines.append("警报消息:")
            for msg in signal.alert_messages:
                lines.append(f"  - {msg}")
        lines.append("")

        # === Flash Window (12小时) ===
        lines.append("=" * 50)
        lines.append("【Flash Window - 12小时即时数据】")
        lines.append("=" * 50)

        # 市场指标
        lines.append("## 市场指标")
        if signal.vix_value:
            vix_emoji = (
                "🔴"
                if signal.is_urgent
                else ("⚠️" if signal.vix_alert_level.value == "warning" else "🟢")
            )
            change_str = (
                f" ({signal.vix_change_percent:+.2f}%)"
                if signal.vix_change_percent
                else ""
            )
            lines.append(
                f"- VIX恐慌指数: {signal.vix_value:.2f}{change_str} {vix_emoji}"
            )

        if signal.dxy_value:
            change_str = (
                f" ({signal.dxy_change_percent:+.2f}%)"
                if signal.dxy_change_percent
                else ""
            )
            lines.append(f"- 美元指数(DXY): {signal.dxy_value:.2f}{change_str}")

        if signal.us10y_value:
            change_str = (
                f" ({signal.us10y_change_percent:+.2f}%)"
                if signal.us10y_change_percent
                else ""
            )
            lines.append(f"- 10年期国债收益率: {signal.us10y_value:.2f}%{change_str}")

        if signal.gold_price:
            change_str = (
                f" ({signal.gold_change_percent:+.2f}%)"
                if signal.gold_change_percent
                else ""
            )
            lines.append(f"- 黄金(GC=F): ${signal.gold_price:.2f}{change_str}")

        if signal.silver_price:
            change_str = (
                f" ({signal.silver_change_percent:+.2f}%)"
                if signal.silver_change_percent
                else ""
            )
            lines.append(f"- 白银(SI=F): ${signal.silver_price:.2f}{change_str}")

        lines.append("")

        # Flash新闻
        lines.append("## 突发新闻 (12小时内)")
        if data.flash.news:
            for i, news in enumerate(data.flash.news[:15], 1):
                lines.append(f"{i}. [{news.source}] {news.title}")
                if news.summary:
                    summary = (
                        news.summary[:200] + "..."
                        if len(news.summary) > 200
                        else news.summary
                    )
                    lines.append(f"   摘要: {summary}")
                if news.impact_tag:
                    lines.append(f"   影响: {news.impact_tag}")
        else:
            lines.append("- 暂无突发新闻")
        lines.append("")

        # === Cycle Window (7天) ===
        lines.append("=" * 50)
        lines.append("【Cycle Window - 本周焦点数据】")
        lines.append("=" * 50)

        # 经济指标
        lines.append("## 宏观经济数据")
        if data.cycle.cpi_actual:
            lines.append(f"- CPI: {data.cycle.cpi_actual}")
        if data.cycle.pce_actual:
            lines.append(f"- PCE: {data.cycle.pce_actual}")
        if data.cycle.nfp_actual:
            lines.append(f"- 非农就业: {data.cycle.nfp_actual}")
        if data.cycle.fed_rate:
            lines.append(f"- 联邦基金利率: {data.cycle.fed_rate}%")

        # FRED原始数据
        if data.cycle.economic_records:
            lines.append("")
            lines.append("## FRED经济指标详情")
            for record in data.cycle.economic_records:
                indicator = record.get("indicator", "Unknown")
                value = record.get("value", "N/A")
                change_pct = record.get("change_pct")
                change_str = f" ({change_pct:+.2f}%)" if change_pct else ""
                lines.append(f"- {indicator}: {value}{change_str}")

        lines.append("")

        # Cycle新闻
        lines.append("## 本周重要新闻")
        if data.cycle.news:
            for i, news in enumerate(data.cycle.news[:10], 1):
                lines.append(f"{i}. [{news.source}] {news.title}")
                if news.summary:
                    summary = (
                        news.summary[:150] + "..."
                        if len(news.summary) > 150
                        else news.summary
                    )
                    lines.append(f"   摘要: {summary}")
        else:
            lines.append("- 暂无本周重要新闻")
        lines.append("")

        # === Trend Window (30天) ===
        lines.append("=" * 50)
        lines.append("【Trend Window - 月度趋势数据】")
        lines.append("=" * 50)

        # Trend新闻
        lines.append("## 长期趋势新闻")
        if data.trend.news:
            for i, news in enumerate(data.trend.news[:10], 1):
                lines.append(f"{i}. [{news.source}] {news.title}")
                if news.summary:
                    summary = (
                        news.summary[:150] + "..."
                        if len(news.summary) > 150
                        else news.summary
                    )
                    lines.append(f"   摘要: {summary}")
        else:
            lines.append("- 暂无长期趋势新闻")
        lines.append("")

        # === 统计 ===
        lines.append("=" * 50)
        lines.append("【数据统计】")
        lines.append("=" * 50)
        lines.append(f"- Flash窗口新闻: {len(data.flash.news)} 条")
        lines.append(f"- Cycle窗口新闻: {len(data.cycle.news)} 条")
        lines.append(f"- Trend窗口新闻: {len(data.trend.news)} 条")
        lines.append(f"- 价格数据记录: {len(data.flash.price_records)} 条")
        lines.append(f"- 经济指标记录: {len(data.cycle.economic_records)} 条")
        lines.append(f"- 总记录数: {len(data.all_records)} 条")

        return "\n".join(lines)

    def build_email_prompt(
        self,
        data: MultiWindowData,
        signal: MarketSignal,
        comex_signal: Optional[ComexSignal] = None,
        mode: str = "full",
    ) -> str:
        """
        构建邮件友好的市场分析报告

        Args:
            data: 多窗口数据
            signal: 市场信号
            comex_signal: COMEX 库存信号（可选）
            mode: "brief"=极简头条(30行) | "full"=头条+详细附录

        Returns:
            邮件格式的文本（纯文本 + 基础格式化）
        """
        lines = []
        now = datetime.now()

        # === 头条区：快速扫描关键信息 ===
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"📊 市场分析速报 | {now.strftime('%Y-%m-%d %H:%M')}")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append("")

        # VIX 和关键指标
        if signal.vix_value:
            vix_emoji = (
                "🔴"
                if signal.is_urgent
                else ("⚠️" if signal.vix_alert_level.value == "warning" else "🟢")
            )
            change_str = (
                f" ({signal.vix_change_percent:+.2f}%)"
                if signal.vix_change_percent
                else ""
            )
            alert_str = " ⚠️ 紧急预警" if signal.is_urgent else ""
            lines.append(
                f"{vix_emoji} VIX恐慌指数: {signal.vix_value:.2f}{change_str}{alert_str}"
            )

        if signal.dxy_value:
            change_str = (
                f" ({signal.dxy_change_percent:+.2f}%)"
                if signal.dxy_change_percent
                else ""
            )
            lines.append(f"💵 美元指数(DXY): {signal.dxy_value:.2f}{change_str}")

        if signal.us10y_value:
            change_str = (
                f" ({signal.us10y_change_percent:+.2f}%)"
                if signal.us10y_change_percent
                else ""
            )
            lines.append(f"📈 10年期国债: {signal.us10y_value:.2f}%{change_str}")

        if signal.gold_price:
            change_str = (
                f" ({signal.gold_change_percent:+.2f}%)"
                if signal.gold_change_percent
                else ""
            )
            lines.append(f"💰 黄金(GC=F): ${signal.gold_price:,.2f}{change_str}")

        if signal.silver_price:
            change_str = (
                f" ({signal.silver_change_percent:+.2f}%)"
                if signal.silver_change_percent
                else ""
            )
            lines.append(f"💎 白银(SI=F): ${signal.silver_price:.2f}{change_str}")

        lines.append("")

        # 情绪评分条
        score = signal.sentiment_score
        bar_length = 10
        filled = int((score + 1) / 2 * bar_length)  # -1到1映射到0到10
        bar = "█" * filled + "░" * (bar_length - filled)
        sentiment_text = (
            "偏利多" if score > 0.3 else ("偏利空" if score < -0.3 else "中性")
        )
        lines.append(f"📊 情绪评分: [{bar}] {score:+.2f} ({sentiment_text})")
        lines.append(f"📌 宏观倾向: {signal.macro_bias.value}")
        lines.append("")

        # 警报消息
        if signal.alert_messages:
            lines.append("⚠️ 警报消息:")
            for msg in signal.alert_messages:
                lines.append(f"  • {msg}")
            lines.append("")

        # === COMEX 库存监控（ASCII 表格版）===
        if comex_signal:
            comex_text = self._render_comex_text(comex_signal)
            if comex_text:
                lines.append(comex_text)
                lines.append("")

        # === Top 5 新闻 ===
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append("📰 今日必读 Top 5")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append("")

        # 合并所有新闻并选择 Top 5
        all_news = data.flash.news + data.cycle.news + data.trend.news
        top_news = self._select_top_news(all_news, count=5)

        if top_news:
            for i, news in enumerate(top_news, 1):
                timestamp_str = (
                    news.timestamp.strftime("%H:%M") if news.timestamp else "N/A"
                )
                impact_emoji = (
                    "📈"
                    if news.impact_tag == "Bullish"
                    else ("📉" if news.impact_tag == "Bearish" else "⚖️")
                )

                lines.append(
                    f"{i}. [{timestamp_str} | {news.source}] {impact_emoji} {news.title}"
                )

                # 摘要（限制长度）
                if news.summary:
                    max_len = getattr(Config, "EMAIL_MAX_SUMMARY_LENGTH", 80)
                    summary = (
                        news.summary[:max_len] + "..."
                        if len(news.summary) > max_len
                        else news.summary
                    )
                    lines.append(f"   摘要：{summary}")

                # 链接
                if news.url:
                    lines.append(f"   🔗 {news.url}")

                lines.append("")
        else:
            lines.append("- 暂无重点新闻")
            lines.append("")

        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append("📎 查看完整数据（下方附录）")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append("")

        # === 详细附录 (仅在 full 模式下) ===
        if mode == "full":
            lines.append("")
            lines.append("=" * 60)
            lines.append("详细数据附录")
            lines.append("=" * 60)
            lines.append("")

            # 调用原有的 build_llm_prompt 生成详细数据
            detailed_prompt = self.build_llm_prompt(data, signal)
            lines.append(detailed_prompt)

        return "\n".join(lines)

    def _render_comex_text(self, comex_signal: ComexSignal) -> str:
        """
        渲染 COMEX 库存监控文本（ASCII 表格版）

        Args:
            comex_signal: COMEX 库存信号

        Returns:
            格式化的 COMEX 文本块
        """
        if not comex_signal:
            return ""

        lines = []
        report_date_str = ""
        if comex_signal.report_date:
            report_date_str = f" ({comex_signal.report_date.strftime('%Y-%m-%d')})"

        lines.append("┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓")
        lines.append(f"┃  🏦 COMEX 库存监控{report_date_str}      ┃")
        lines.append("┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫")

        # 白银数据
        if comex_signal.silver_registered_million is not None:
            lines.append("┃                                       ┃")
            lines.append("┃  💎 白银 (Registered)                 ┃")
            lines.append(
                f"┃     库存: {comex_signal.silver_registered_million:.2f}M oz                    ┃"
            )

            # 日变化和周变化
            daily_str = ""
            weekly_str = ""
            if comex_signal.silver_daily_change_pct is not None:
                emoji = "📈" if comex_signal.silver_daily_change_pct >= 0 else "📉"
                daily_str = f"{emoji} {comex_signal.silver_daily_change_pct:+.1f}% (日)"

            if comex_signal.silver_weekly_change_pct is not None:
                emoji = "📈" if comex_signal.silver_weekly_change_pct >= 0 else "📉"
                weekly_str = (
                    f"{emoji} {comex_signal.silver_weekly_change_pct:+.1f}% (周)"
                )

            if daily_str or weekly_str:
                change_line = f"     变化: {daily_str}  {weekly_str}"
                lines.append(f"┃{change_line:<39}┃")

            # 状态
            status_emoji = {
                ComexAlertLevel.SYSTEM_FAILURE: "⚫",
                ComexAlertLevel.RED: "🔴",
                ComexAlertLevel.YELLOW: "🟡",
                ComexAlertLevel.SAFE: "🟢",
            }.get(comex_signal.silver_alert_level, "")

            status_text = {
                ComexAlertLevel.SYSTEM_FAILURE: "系统风险",
                ComexAlertLevel.RED: "生死线",
                ComexAlertLevel.YELLOW: "警戒线",
                ComexAlertLevel.SAFE: "安全",
            }.get(comex_signal.silver_alert_level, "未知")

            lines.append(
                f"┃     状态: {status_emoji} {status_text}                   ┃"
            )

            # 建议
            if (
                comex_signal.silver_recommendation
                and comex_signal.silver_alert_level != ComexAlertLevel.SAFE
            ):
                rec = comex_signal.silver_recommendation
                if len(rec) > 30:
                    rec = rec[:30] + "..."
                lines.append(f"┃     💡 {rec:<33}┃")

        # 黄金数据
        if comex_signal.gold_registered_million is not None:
            lines.append("┃                                       ┃")
            lines.append("┃  ───────────────────────────────      ┃")
            lines.append("┃                                       ┃")
            lines.append("┃  💰 黄金 (Registered)                 ┃")
            lines.append(
                f"┃     库存: {comex_signal.gold_registered_million:.2f}M oz                     ┃"
            )

            # 日变化和周变化
            daily_str = ""
            weekly_str = ""
            if comex_signal.gold_daily_change_pct is not None:
                emoji = "📈" if comex_signal.gold_daily_change_pct >= 0 else "📉"
                daily_str = f"{emoji} {comex_signal.gold_daily_change_pct:+.1f}% (日)"

            if comex_signal.gold_weekly_change_pct is not None:
                emoji = "📈" if comex_signal.gold_weekly_change_pct >= 0 else "📉"
                weekly_str = f"{emoji} {comex_signal.gold_weekly_change_pct:+.1f}% (周)"

            if daily_str or weekly_str:
                change_line = f"     变化: {daily_str}  {weekly_str}"
                lines.append(f"┃{change_line:<39}┃")

            # 状态
            status_emoji = {
                ComexAlertLevel.SYSTEM_FAILURE: "⚫",
                ComexAlertLevel.RED: "🔴",
                ComexAlertLevel.YELLOW: "🟡",
                ComexAlertLevel.SAFE: "🟢",
            }.get(comex_signal.gold_alert_level, "")

            status_text = {
                ComexAlertLevel.SYSTEM_FAILURE: "系统风险",
                ComexAlertLevel.RED: "生死线",
                ComexAlertLevel.YELLOW: "警戒线",
                ComexAlertLevel.SAFE: "安全",
            }.get(comex_signal.gold_alert_level, "未知")

            lines.append(
                f"┃     状态: {status_emoji} {status_text}                     ┃"
            )

            # 建议
            if (
                comex_signal.gold_recommendation
                and comex_signal.gold_alert_level != ComexAlertLevel.SAFE
            ):
                rec = comex_signal.gold_recommendation
                if len(rec) > 30:
                    rec = rec[:30] + "..."
                lines.append(f"┃     💡 {rec:<33}┃")

        lines.append("┃                                       ┃")
        lines.append("┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛")

        return "\n".join(lines)

    def _select_top_news(
        self, news_list: List[NewsItem], count: int = 5
    ) -> List[NewsItem]:
        """
        选择优先级最高的 Top N 新闻

        优先级规则:
        1. impact_tag = "Bullish" 或 "Bearish" > "Neutral"
        2. relevance_score 高 > 低
        3. 时间新 > 旧

        Args:
            news_list: 新闻列表
            count: 返回数量

        Returns:
            排序后的新闻列表（最多 count 条）
        """
        if not news_list:
            return []

        def priority_score(news: NewsItem) -> tuple:
            # 优先级1: impact_tag 权重
            impact_weight = 0
            if news.impact_tag in ("Bullish", "Bearish"):
                impact_weight = 2
            elif news.impact_tag == "Neutral":
                impact_weight = 1

            # 优先级2: relevance_score
            relevance = news.relevance_score if news.relevance_score else 0.5

            # 优先级3: 时间戳（越新越好）
            # 转换为 Unix 时间戳以避免 naive/aware datetime 比较问题
            if news.timestamp:
                try:
                    timestamp_value = news.timestamp.timestamp()
                except:
                    timestamp_value = 0.0
            else:
                timestamp_value = 0.0

            return (impact_weight, relevance, timestamp_value)

        # 排序并选择 Top N
        sorted_news = sorted(news_list, key=priority_score, reverse=True)
        return sorted_news[:count]
