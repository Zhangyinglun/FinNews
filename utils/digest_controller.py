"""
4段式邮件摘要控制器
结构: 市场指数与数据 → 重点新闻 → 其他新闻 → 市场分析

架构:
- LLM 只返回结构化 JSON 数据 (新闻筛选 + 分析内容)
- Python 端负责 HTML 模板渲染 (价格/指标数据直接填充)
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from models.market_data import MultiWindowData
from models.analysis import (
    MarketSignal,
    AlertLevel,
    MacroBias,
    ComexSignal,
    ComexAlertLevel,
)


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime objects."""

    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)


class DigestController:
    """
    4段式邮件摘要控制器

    邮件结构:
    1. 市场指数与数据 - VIX信号灯 + 价格表 + 经济指标
    2. 重点新闻 - 5-8条最重要的新闻 (仅事实，不含分析)
    3. 其他新闻 - 剩余新闻 (仅事实，不含分析)
    4. 市场分析 - 深度分析 (所有分析集中在此)
    """

    def __init__(self):
        """初始化控制器"""
        pass

    def _normalize_title(self, title: str) -> List[str]:
        """标题归一化：小写化 + 分词 + 轻量词形还原。"""
        text = title.lower().strip()
        tokens = re.findall(r"[a-z]+|[\u4e00-\u9fff]", text)

        normalized: List[str] = []
        for token in tokens:
            if token.endswith("ing") and len(token) > 4:
                token = token[:-3]
            elif token.endswith("ies") and len(token) > 4:
                token = token[:-3] + "y"
            elif token.endswith("es") and len(token) > 3:
                token = token[:-2]
            elif token.endswith("s") and len(token) > 3:
                token = token[:-1]
            normalized.append(token)

        return normalized

    def _pre_deduplicate_news(self, news_list: List[Any]) -> List[Any]:
        """
        传给 LLM 前执行轻量标题去重。

        仅剔除高度重复标题，不做语义聚合。
        """
        if not news_list:
            return []

        threshold = 0.75
        kept: List[Any] = []
        kept_tokens: List[set[str]] = []

        for news in news_list:
            title = getattr(news, "title", "")
            tokens = set(self._normalize_title(title))

            is_duplicate = False
            for idx, existing_tokens in enumerate(kept_tokens):
                if not tokens or not existing_tokens:
                    continue

                intersection = tokens & existing_tokens
                union = tokens | existing_tokens
                jaccard = len(intersection) / len(union) if union else 0.0

                if jaccard >= threshold:
                    existing = kept[idx]
                    existing_score = getattr(existing, "relevance_score", None) or 0.0
                    new_score = getattr(news, "relevance_score", None) or 0.0

                    if new_score > existing_score:
                        kept[idx] = news
                        kept_tokens[idx] = tokens
                    elif (
                        new_score == existing_score
                        and getattr(news, "timestamp", None)
                        and getattr(existing, "timestamp", None)
                        and self._safe_timestamp(news.timestamp)
                        > self._safe_timestamp(existing.timestamp)
                    ):
                        kept[idx] = news
                        kept_tokens[idx] = tokens

                    is_duplicate = True
                    break

            if not is_duplicate:
                kept.append(news)
                kept_tokens.append(tokens)

        return kept

    def _safe_timestamp(self, dt: datetime) -> float:
        """将 datetime 安全转换为时间戳，兼容 naive/aware。"""
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc).timestamp()
        return dt.timestamp()

    def _get_vix_indicator(self, signal: MarketSignal) -> Tuple[str, str, str]:
        """
        获取VIX信号灯指示器

        Args:
            signal: 市场信号

        Returns:
            (emoji, css_class, status_text)
        """
        if signal.is_urgent or signal.vix_alert_level == AlertLevel.CRITICAL:
            return "!!", "vix-red", "紧急"
        elif signal.vix_alert_level == AlertLevel.WARNING:
            return "!", "vix-yellow", "警戒"
        else:
            return "OK", "vix-green", "正常"

    def build_llm_prompt(
        self, data: MultiWindowData, signal: MarketSignal
    ) -> Tuple[str, Dict[str, Any]]:
        """
        构建LLM输入提示 (只要求返回结构化数据，不生成HTML)

        Args:
            data: 多窗口数据
            signal: 规则引擎生成的市场信号

        Returns:
            (用户提示字符串, 统计信息字典)
        """
        lines: List[str] = []
        now = datetime.now()

        # 系统指令
        lines.append("你是一位专业的金融分析师，负责筛选新闻并撰写市场分析。")
        lines.append("请根据以下数据，返回结构化的JSON数据。")
        lines.append("")
        lines.append(f"数据生成时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # VIX信号灯信息 (供LLM参考)
        vix_emoji, vix_class, vix_status = self._get_vix_indicator(signal)
        lines.append("=" * 60)
        lines.append("【市场状态概览】")
        lines.append("=" * 60)
        lines.append(f"VIX信号灯: {vix_emoji} {vix_status}")
        lines.append(f"VIX当前值: {signal.vix_value or 'N/A'}")
        lines.append(f"VIX日变化: {signal.vix_change_percent or 'N/A'}%")
        lines.append(f"VIX警报级别: {signal.vix_alert_level.value}")
        lines.append(f"宏观倾向: {signal.macro_bias.value}")
        lines.append(f"情感评分: {signal.sentiment_score:.2f} (-1利空, +1利多)")
        lines.append(f"紧急警报: {'是' if signal.is_urgent else '否'}")

        if signal.alert_messages:
            lines.append("")
            lines.append("触发的警报:")
            for msg in signal.alert_messages:
                lines.append(f"  - {msg}")
        lines.append("")

        # 价格数据 (供LLM参考)
        lines.append("=" * 60)
        lines.append("【价格数据】")
        lines.append("=" * 60)
        if signal.gold_price:
            change_str = (
                f" ({signal.gold_change_percent:+.2f}%)"
                if signal.gold_change_percent
                else ""
            )
            lines.append(f"- 黄金: ${signal.gold_price:.2f}{change_str}")
        if signal.silver_price:
            change_str = (
                f" ({signal.silver_change_percent:+.2f}%)"
                if signal.silver_change_percent
                else ""
            )
            lines.append(f"- 白银: ${signal.silver_price:.2f}{change_str}")
        if signal.dxy_value:
            change_str = (
                f" ({signal.dxy_change_percent:+.2f}%)"
                if signal.dxy_change_percent
                else ""
            )
            lines.append(f"- 美元指数: {signal.dxy_value:.2f}{change_str}")
        if signal.us10y_value:
            change_str = (
                f" ({signal.us10y_change_percent:+.2f}%)"
                if signal.us10y_change_percent
                else ""
            )
            lines.append(f"- 10年期国债: {signal.us10y_value:.2f}%{change_str}")
        lines.append("")

        # === 新闻数据 ===
        flash_news = self._pre_deduplicate_news(data.flash.news[:15])
        cycle_news = self._pre_deduplicate_news(data.cycle.news[:10])
        trend_news = self._pre_deduplicate_news(data.trend.news[:8])

        lines.append("=" * 60)
        lines.append("【新闻数据 - 请从中聚合同一事件并生成综述】")
        lines.append("=" * 60)
        lines.append("")

        # Flash窗口新闻
        lines.append("## Flash窗口新闻 (12小时内)")
        if flash_news:
            for i, news in enumerate(flash_news, 1):
                # 附加元数据辅助LLM排序
                impact = f" [影响:{news.impact_tag}]" if news.impact_tag else ""
                relevance = (
                    f" [相关性:{news.relevance_score:.2f}]"
                    if news.relevance_score
                    else ""
                )
                url = f" URL:{news.url}" if news.url else ""
                timestamp_str = (
                    news.timestamp.strftime("%H:%M") if news.timestamp else ""
                )
                time_suffix = f" ({timestamp_str})" if timestamp_str else ""

                lines.append(
                    f"{i}. [{news.source}]{time_suffix} {news.title}{impact}{relevance}"
                )
                if news.summary:
                    summary = (
                        news.summary[:200] + "..."
                        if len(news.summary) > 200
                        else news.summary
                    )
                    lines.append(f"   摘要: {summary}")
                if url:
                    lines.append(f"   {url}")
        else:
            lines.append("- 暂无")
        lines.append("")

        # Cycle窗口新闻
        lines.append("## Cycle窗口新闻 (7天内)")
        if cycle_news:
            for i, news in enumerate(cycle_news, 1):
                impact = f" [影响:{news.impact_tag}]" if news.impact_tag else ""
                relevance = (
                    f" [相关性:{news.relevance_score:.2f}]"
                    if news.relevance_score
                    else ""
                )
                url = f" URL:{news.url}" if news.url else ""
                timestamp_str = (
                    news.timestamp.strftime("%H:%M") if news.timestamp else ""
                )
                time_suffix = f" ({timestamp_str})" if timestamp_str else ""

                lines.append(
                    f"{i}. [{news.source}]{time_suffix} {news.title}{impact}{relevance}"
                )
                if news.summary:
                    summary = (
                        news.summary[:150] + "..."
                        if len(news.summary) > 150
                        else news.summary
                    )
                    lines.append(f"   摘要: {summary}")
                if url:
                    lines.append(f"   {url}")
        else:
            lines.append("- 暂无")
        lines.append("")

        # Trend窗口新闻
        lines.append("## Trend窗口新闻 (30天内)")
        if trend_news:
            for i, news in enumerate(trend_news, 1):
                impact = f" [影响:{news.impact_tag}]" if news.impact_tag else ""
                relevance = (
                    f" [相关性:{news.relevance_score:.2f}]"
                    if news.relevance_score
                    else ""
                )
                url = f" URL:{news.url}" if news.url else ""
                timestamp_str = (
                    news.timestamp.strftime("%H:%M") if news.timestamp else ""
                )
                time_suffix = f" ({timestamp_str})" if timestamp_str else ""

                lines.append(
                    f"{i}. [{news.source}]{time_suffix} {news.title}{impact}{relevance}"
                )
                if news.summary:
                    summary = (
                        news.summary[:150] + "..."
                        if len(news.summary) > 150
                        else news.summary
                    )
                    lines.append(f"   摘要: {summary}")
                if url:
                    lines.append(f"   {url}")
        else:
            lines.append("- 暂无")
        lines.append("")

        # === 任务说明 ===
        lines.append("=" * 60)
        lines.append("【你的任务】")
        lines.append("=" * 60)
        lines.append("")
        lines.append("1. 生成邮件标题 (subject)")
        lines.append("   - 格式: YYYY-MM-DD 市场日报：[今日核心内容]")
        lines.append("   - 要求: 不要在标题中固定使用VIX警报词或符号")
        lines.append("   - 例如: 2026-01-20 市场日报：美联储表态偏鹰，金价高位震荡")
        lines.append("")
        lines.append("2. 新闻综述聚合 (news_clusters)")
        lines.append("   - 将所有新闻按事件/主题进行语义聚合")
        lines.append("   - 报道同一事件的不同角度新闻合并到同一个 cluster")
        lines.append("   - 独立新闻（无相关新闻）单独成为一个 cluster")
        lines.append("   - cluster 之间按重要性排序（最重要的事件排第一）")
        lines.append("   - 每个 cluster 内的 sources 也按重要性排序")
        lines.append("   - 重要性排序规则:")
        lines.append("     1) 影响标签: Bullish/Bearish > Neutral")
        lines.append("     2) 相关性评分: 越高越优先")
        lines.append("     3) 时效性: 越新越优先")
        lines.append("   - 每个 cluster 必须包含:")
        lines.append("     * cluster_title: 综述标题（中文），概括该组新闻核心事件")
        lines.append("     * cluster_summary: 整合摘要（中文，1-3句话）")
        lines.append(
            "     * impact_tag: 对贵金属整体影响方向 (Bullish/Bearish/Neutral)"
        )
        lines.append(
            "     * sources: 原始新闻列表，每条含 title, source, url, timestamp"
        )
        lines.append("   - 综述标题和摘要应整合多条新闻信息，不要复制单条新闻")
        lines.append("   - 所有英文标题和摘要必须翻译成中文")
        lines.append("   - 新闻综述只陈述事实，不添加分析判断")
        lines.append("")
        lines.append("3. 撰写精简的市场分析 (analysis)")
        lines.append("   - market_sentiment: 当前市场情绪判断 (基于VIX和宏观数据)")
        lines.append("   - price_outlook: 黄金白银短期走势预判")
        lines.append("   - risk_factors: 需要关注的风险点")
        lines.append("   - trading_suggestion: 操作建议")
        lines.append("   - 每项30-60字，用要点式写作，专业但易懂")
        lines.append("")

        # 统计信息
        stats = {
            "flash_news_count": len(data.flash.news),
            "cycle_news_count": len(data.cycle.news),
            "trend_news_count": len(data.trend.news),
            "price_records_count": len(data.flash.price_records),
            "economic_records_count": len(data.cycle.economic_records),
            "total_records_count": len(data.all_records),
            "generated_at": now.isoformat(),
        }

        user_prompt = "\n".join(lines)
        return user_prompt, stats

    def get_email_subject(self, signal: MarketSignal) -> str:
        """
        根据市场信号生成备用邮件主题

        Args:
            signal: 市场信号

        Returns:
            邮件主题字符串
        """
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        summary = signal.get_signal_summary()
        return f"{date_str} 市场日报：{summary}"

    def render_email_html(
        self,
        digest_data: Dict[str, Any],
        signal: MarketSignal,
        data: MultiWindowData,
        comex_signal: Optional[ComexSignal] = None,
    ) -> Tuple[str, Optional[Dict[str, str]]]:
        """
        将LLM返回的JSON数据 + Python端数据 渲染为HTML邮件

        Args:
            digest_data: LLM返回的结构化数据
            signal: 市场信号 (含价格数据)
            data: 多窗口数据 (含经济指标)
            comex_signal: COMEX库存信号 (可选)

        Returns:
            (完整的HTML邮件字符串, 嵌入图片字典 {cid: base64_data})
        """
        now = datetime.now()
        images = {}

        # VIX状态
        _, vix_class, vix_status = self._get_vix_indicator(signal)
        vix_value = f"{signal.vix_value:.2f}" if signal.vix_value else "N/A"

        # VIX状态胶囊 (Apple 系统配色)
        vix_badge_style_map = {
            "vix-red": ("#cc2d26", "#ffe8e7"),
            "vix-yellow": ("#975a00", "#fff4e0"),
            "vix-green": ("#1a7e34", "#e8f9ee"),
        }
        vix_badge_color, vix_badge_bg = vix_badge_style_map.get(
            vix_class, ("#86868b", "#f5f5f7")
        )
        vix_badge_html = self._build_badge_html(vix_status, vix_badge_color, vix_badge_bg)

        if signal.vix_change_percent is not None:
            vix_change_color = (
                "#34c759" if signal.vix_change_percent >= 0 else "#ff3b30"
            )
            vix_change_html = f'<span style="color: {vix_change_color}; font-weight: 600;">{signal.vix_change_percent:+.2f}%</span>'
        else:
            vix_change_html = '<span style="color: #86868b;">N/A</span>'

        vix_market_row_html = f"""<tr>
            <td style="padding: 11px 0; font-size: 15px; color: #1d1d1f; border-bottom: 1px solid #f2f2f7;">VIX 恐慌指数</td>
            <td style="padding: 11px 0; text-align: right; font-size: 15px; color: #1d1d1f; border-bottom: 1px solid #f2f2f7;">{vix_value}</td>
            <td style="padding: 11px 0; text-align: right; font-size: 14px; border-bottom: 1px solid #f2f2f7;">{vix_change_html}&nbsp;{vix_badge_html}</td>
        </tr>"""

        # 构建价格表行
        price_rows = []
        has_any_value = signal.vix_value is not None
        price_data = [
            ("黄金 (XAU)", signal.gold_price, signal.gold_change_percent, "$", ""),
            ("白银 (XAG)", signal.silver_price, signal.silver_change_percent, "$", ""),
            ("美元指数 (DXY)", signal.dxy_value, signal.dxy_change_percent, "", ""),
            ("10年期国债", signal.us10y_value, signal.us10y_change_percent, "", "%"),
        ]

        for name, value, change, prefix, suffix in price_data:
            if value is not None:
                value_str = f"{prefix}{value:.2f}{suffix}"
                has_any_value = True
            else:
                value_str = "N/A"

            if change is not None:
                change_color = "#34c759" if change >= 0 else "#ff3b30"
                change_str = f'<span style="color: {change_color}; font-weight: 500;">{change:+.2f}%</span>'
            else:
                change_str = "-"

            price_rows.append(f"""<tr>
                <td style="padding: 11px 0; font-size: 15px; color: #1d1d1f; border-bottom: 1px solid #f2f2f7;">{name}</td>
                <td style="padding: 11px 0; text-align: right; font-size: 15px; color: #1d1d1f; border-bottom: 1px solid #f2f2f7;">{value_str}</td>
                <td style="padding: 11px 0; text-align: right; font-size: 14px; border-bottom: 1px solid #f2f2f7;">{change_str}</td>
            </tr>""")

        # 防御性编程：如果所有价格数据都缺失，仅记录日志
        if not has_any_value:
            import logging

            logger = logging.getLogger(__name__)
            logger.warning("⚠️ 价格表数据全部缺失！signal对象中的价格字段都为None")

        price_table_html = "\n".join(price_rows)

        # 添加价格来源备注 (如果有)
        if signal.price_source_note:
            price_table_html += f"""<tr>
                <td colspan="3" style="padding: 8px 0; font-size: 12px; color: #86868b; font-style: italic;">
                    {signal.price_source_note}
                </td>
            </tr>"""

        # 构建经济指标独立板块

        econ_items = []
        if data.cycle.cpi_actual:
            econ_items.append(f"CPI: {data.cycle.cpi_actual}")
        if data.cycle.pce_actual:
            econ_items.append(f"PCE: {data.cycle.pce_actual}")
        if data.cycle.nfp_actual:
            econ_items.append(f"NFP: {data.cycle.nfp_actual}")
        if data.cycle.fed_rate:
            econ_items.append(f"联邦基金利率: {data.cycle.fed_rate}%")

        if econ_items:
            econ_content = " &nbsp;|&nbsp; ".join(econ_items)
            econ_section_html = f"""<tr>
        <td style="padding: 20px 28px 16px 28px; border-top: 1px solid #d2d2d7;">
            <p style="margin: 0 0 8px 0; font-size: 11px; font-weight: 600; letter-spacing: 0.1em; color: #86868b; text-transform: uppercase;">经济指标</p>
            <p style="margin: 0; font-size: 14px; color: #424245; line-height: 1.6;">{econ_content}</p>
        </td>
    </tr>"""
        else:
            econ_section_html = ""

        # 构建新闻综述组
        news_clusters_html = self._render_news_clusters(
            digest_data.get("news_clusters", [])
        )

        # 构建市场分析
        analysis = digest_data.get("analysis", {})
        analysis_html = self._render_analysis(analysis)

        # 构建COMEX库存区块
        comex_section_html, comex_images = self._render_comex_section(comex_signal)
        if comex_images:
            images.update(comex_images)

        # 邮件标题
        subject = digest_data.get("subject", self.get_email_subject(signal))

        # 宏观倾向
        macro_bias_text = {
            MacroBias.BULLISH: "利多黄金",
            MacroBias.BEARISH: "利空黄金",
            MacroBias.NEUTRAL: "中性",
        }.get(signal.macro_bias, "中性")

        # 情绪评分 (sentiment_score: -1 到 +1)
        sentiment_score = signal.sentiment_score

        # 根据评分确定颜色 (Apple 系统配色)
        if sentiment_score > 0.3:
            bar_color = "#34c759"  # Apple 绿 (利多)
            sentiment_label = "利多"
        elif sentiment_score < -0.3:
            bar_color = "#ff3b30"  # Apple 红 (利空)
            sentiment_label = "利空"
        else:
            bar_color = "#86868b"  # Apple 灰 (中性)
            sentiment_label = "中性"

        market_summary_row_html = f"""<tr>
            <td colspan="3" style="padding: 6px 0 12px 0; font-size: 13px; color: #86868b;">
                宏观倾向:&nbsp;<span style="color: #1d1d1f; font-weight: 600;">{macro_bias_text}</span>
                &nbsp;&nbsp;&middot;&nbsp;&nbsp;
                情绪评分:&nbsp;<span style="font-weight: 600; color: {bar_color};">{sentiment_score:+.2f}</span>&nbsp;({sentiment_label})
            </td>
        </tr>"""

        # Header 价格速览行已移除（信息在下方表格展示）
        price_summary_line = ""

        # 渲染完整HTML
        html = EMAIL_TEMPLATE.format(
            subject=subject,
            datetime=now.strftime("%Y-%m-%d %H:%M:%S"),
            price_summary_line=price_summary_line,
            vix_market_row=vix_market_row_html,
            market_summary_row=market_summary_row_html,
            price_table=price_table_html,
            econ_section=econ_section_html,
            comex_section=comex_section_html,
            news_clusters=news_clusters_html,
            analysis=analysis_html,
        )

        return html, images

    def _render_news_clusters(self, clusters: List[Dict[str, Any]]) -> str:
        """渲染新闻综述组 HTML (Apple 风格，内联样式，Gmail兼容)。"""
        if not clusters:
            return '<div style="padding: 14px 0; color: #86868b; font-size: 14px;">暂无相关新闻</div>'

        items = []
        for i, cluster in enumerate(clusters):
            cluster_title = cluster.get("cluster_title", "无标题")
            cluster_summary = cluster.get("cluster_summary", "")
            impact_tag = cluster.get("impact_tag", "Neutral")
            sources = cluster.get("sources", [])

            border_style = (
                "border-bottom: 1px solid #d2d2d7; margin-bottom: 16px; padding-bottom: 16px;"
                if i < len(clusters) - 1
                else ""
            )

            impact_tag_map = {
                "Bullish": ("利多", "#1a7e34", "#e8f9ee"),
                "Bearish": ("利空", "#cc2d26", "#ffe8e7"),
                "Neutral": ("中性", "#86868b", "#f5f5f7"),
            }
            tag_text, tag_color, tag_bg = impact_tag_map.get(
                impact_tag, ("中性", "#86868b", "#f5f5f7")
            )
            impact_tag_html = self._build_badge_html(
                tag_text, tag_color, tag_bg, extra_style="margin-right: 8px;"
            )

            cluster_title_html = (
                f'<span style="font-size: 16px; font-weight: 600; '
                f'color: #1d1d1f; line-height: 1.5;">{cluster_title}</span>'
            )

            summary_html = ""
            if cluster_summary:
                summary_html = (
                    '<div style="font-size: 14px; color: #424245; '
                    f'line-height: 1.7; margin: 8px 0 10px 0;">{cluster_summary}</div>'
                )

            source_items = []
            for source_item in sources:
                source_title = source_item.get("title", "")
                source_name = source_item.get("source", "")
                source_url = source_item.get("url", "")
                source_time = source_item.get("timestamp", "")

                meta_parts = [part for part in [source_name, source_time] if part]
                meta_str = " · ".join(meta_parts)

                if source_url:
                    source_title_html = (
                        f'<a href="{source_url}" style="color: #0071e3; '
                        f'text-decoration: none; font-size: 13px;" '
                        f'target="_blank">{source_title}</a>'
                    )
                else:
                    source_title_html = (
                        f'<span style="color: #424245; font-size: 13px;">'
                        f"{source_title}</span>"
                    )

                source_meta_html = ""
                if meta_str:
                    source_meta_html = (
                        '<span style="color: #86868b; font-size: 12px; '
                        f'margin-left: 6px;">({meta_str})</span>'
                    )

                source_items.append(
                    '<div style="padding: 3px 0 3px 12px;">'
                    '<span style="color: #86868b; margin-right: 6px;">·</span>'
                    f"{source_title_html}{source_meta_html}</div>"
                )

            sources_html = "\n".join(source_items)

            item_html = f"""<div style="padding: 14px 0; {border_style}">
                <div style="margin-bottom: 8px;">{impact_tag_html}{cluster_title_html}</div>
                {summary_html}
                {sources_html}
            </div>"""
            items.append(item_html)

        return "\n".join(items)

    def _render_analysis(self, analysis: Dict[str, str]) -> str:
        """渲染市场分析HTML (Apple 风格，扁平结构，内联样式)"""
        sections = [
            ("市场情绪", analysis.get("market_sentiment", "")),
            ("走势预判", analysis.get("price_outlook", "")),
            ("风险因素", analysis.get("risk_factors", "")),
            ("操作建议", analysis.get("trading_suggestion", "")),
        ]

        items = []
        valid_sections = [(t, c) for t, c in sections if c]

        for i, (title, content) in enumerate(valid_sections):
            # 最后一条不加底部边框
            border_style = (
                "border-bottom: 1px solid #d2d2d7;"
                if i < len(valid_sections) - 1
                else ""
            )

            item_html = f"""<div style="padding: 14px 0; {border_style}">
                <div style="margin-bottom: 7px;">
                    <span style="font-size: 16px; font-weight: 600; color: #1d1d1f;">{title}</span>
                </div>
                <div style="font-size: 14px; color: #424245; line-height: 1.7;">{content}</div>
            </div>"""
            items.append(item_html)

        if not items:
            return '<div style="padding: 14px 0; color: #86868b; font-size: 14px;">暂无分析内容</div>'

        return "\n".join(items)

    def _get_comex_badge_style(
        self, alert_level: Optional[ComexAlertLevel]
    ) -> Tuple[str, str, str]:
        """根据COMEX预警等级返回状态徽章样式 (Apple 系统配色)。"""
        badge_style_map: Dict[Optional[ComexAlertLevel], Tuple[str, str, str]] = {
            ComexAlertLevel.SAFE: ("正常", "#1a7e34", "#e8f9ee"),
            ComexAlertLevel.YELLOW: ("需关注", "#975a00", "#fff4e0"),
            ComexAlertLevel.RED: ("高风险", "#cc2d26", "#ffe8e7"),
            ComexAlertLevel.SYSTEM_FAILURE: ("系统风险", "#ffffff", "#1d1d1f"),
            None: ("数据缺失", "#86868b", "#f5f5f7"),
        }
        return badge_style_map.get(alert_level, badge_style_map[None])

    def _build_badge_html(
        self, text: str, text_color: str, bg_color: str, extra_style: str = ""
    ) -> str:
        """构建 Apple 风格胶囊徽章 HTML（通用）。"""
        extra = f" {extra_style}" if extra_style else ""
        return (
            f'<span style="display: inline-block; padding: 2px 8px; '
            f"border-radius: 20px; font-size: 11px; font-weight: 600; "
            f"color: {text_color}; background-color: {bg_color}; "
            f'vertical-align: middle; letter-spacing: 0.02em;{extra}">'
            f"{text}</span>"
        )

    def _render_comex_badge(self, alert_level: Optional[ComexAlertLevel]) -> str:
        """渲染COMEX状态胶囊徽章HTML (Apple 风格)。"""
        badge_text, text_color, bg_color = self._get_comex_badge_style(alert_level)
        return self._build_badge_html(badge_text, text_color, bg_color)

    def _get_comex_indicator(
        self, comex_signal: Optional[ComexSignal]
    ) -> Tuple[str, str, str, str]:
        """
        获取COMEX库存信号灯指示器

        Args:
            comex_signal: COMEX信号对象

        Returns:
            (indicator_text, css_class, status_text, bg_color)
        """
        if comex_signal is None:
            return "数据缺失", "comex-unknown", "数据缺失", "#e2e8f0"

        worst_level = comex_signal.get_worst_alert_level()

        if worst_level == ComexAlertLevel.SYSTEM_FAILURE:
            return "系统风险", "comex-black", "系统风险", "#1e293b"
        elif worst_level == ComexAlertLevel.RED:
            return "高风险", "comex-red", "高风险", "#fee2e2"
        elif worst_level == ComexAlertLevel.YELLOW:
            return "需关注", "comex-yellow", "需关注", "#fef9c3"
        else:
            return "正常", "comex-green", "正常", "#dcfce7"

    def _render_comex_section(
        self, comex_signal: Optional[ComexSignal]
    ) -> Tuple[str, Dict[str, str]]:
        """
        渲染COMEX库存监控区块HTML

        Args:
            comex_signal: COMEX信号对象 (可为None)

        Returns:
            (COMEX区块HTML字符串, 图片字典)
        """
        if comex_signal is None:
            return "", {}

        # 构建白银行
        silver_rows = []
        if comex_signal.silver_registered_million is not None:
            silver_badge = self._render_comex_badge(comex_signal.silver_alert_level)

            daily_str = ""
            weekly_str = ""
            if comex_signal.silver_daily_change_pct is not None:
                change_color = (
                    "#34c759"
                    if comex_signal.silver_daily_change_pct >= 0
                    else "#ff3b30"
                )
                daily_str = f'<span style="color: {change_color}; font-weight: 500;">({comex_signal.silver_daily_change_pct:+.1f}% 日)</span>'

            if comex_signal.silver_weekly_change_pct is not None:
                change_color = (
                    "#34c759"
                    if comex_signal.silver_weekly_change_pct >= 0
                    else "#ff3b30"
                )
                weekly_str = f'<span style="color: {change_color}; font-weight: 500;">({comex_signal.silver_weekly_change_pct:+.1f}% 周)</span>'

            change_str = " ".join(filter(None, [daily_str, weekly_str]))

            silver_rows.append(f"""<tr>
                <td style="padding: 11px 0; font-size: 15px; color: #1d1d1f; border-bottom: 1px solid #f2f2f7;">白银 (Registered)</td>
                <td style="padding: 11px 0; text-align: right; font-size: 15px; color: #1d1d1f; border-bottom: 1px solid #f2f2f7;">{comex_signal.silver_registered_million:.2f}M oz</td>
                <td style="padding: 11px 0; text-align: center; font-size: 13px; color: #424245; border-bottom: 1px solid #f2f2f7;">{silver_badge} {change_str}</td>
            </tr>""")

        # 构建黄金行
        gold_rows = []
        if comex_signal.gold_registered_million is not None:
            gold_badge = self._render_comex_badge(comex_signal.gold_alert_level)

            daily_str = ""
            weekly_str = ""
            if comex_signal.gold_daily_change_pct is not None:
                change_color = (
                    "#34c759" if comex_signal.gold_daily_change_pct >= 0 else "#ff3b30"
                )
                daily_str = f'<span style="color: {change_color}; font-weight: 500;">({comex_signal.gold_daily_change_pct:+.1f}% 日)</span>'

            if comex_signal.gold_weekly_change_pct is not None:
                change_color = (
                    "#34c759" if comex_signal.gold_weekly_change_pct >= 0 else "#ff3b30"
                )
                weekly_str = f'<span style="color: {change_color}; font-weight: 500;">({comex_signal.gold_weekly_change_pct:+.1f}% 周)</span>'

            change_str = " ".join(filter(None, [daily_str, weekly_str]))

            gold_rows.append(f"""<tr>
                <td style="padding: 11px 0; font-size: 15px; color: #1d1d1f; border-bottom: 1px solid #f2f2f7;">黄金 (Registered)</td>
                <td style="padding: 11px 0; text-align: right; font-size: 15px; color: #1d1d1f; border-bottom: 1px solid #f2f2f7;">{comex_signal.gold_registered_million:.2f}M oz</td>
                <td style="padding: 11px 0; text-align: center; font-size: 13px; color: #424245; border-bottom: 1px solid #f2f2f7;">{gold_badge} {change_str}</td>
            </tr>""")

        if not silver_rows and not gold_rows:
            return "", {}

        table_rows = "\n".join(silver_rows + gold_rows)

        # 构建警报消息
        alert_messages = []
        if (
            comex_signal.silver_alert_message
            and comex_signal.silver_alert_level != ComexAlertLevel.SAFE
        ):
            alert_messages.append(comex_signal.silver_alert_message)
        if (
            comex_signal.gold_alert_message
            and comex_signal.gold_alert_level != ComexAlertLevel.SAFE
        ):
            alert_messages.append(comex_signal.gold_alert_message)

        alert_html = ""
        if alert_messages:
            alert_items = "".join(
                [
                    f'<div style="margin-bottom: 4px;">{msg}</div>'
                    for msg in alert_messages
                ]
            )
            alert_html = f"""<div style="padding: 10px 12px; font-size: 16px; background-color: #f8fafc; border-top: 1px solid #e2e8f0;">
                {alert_items}
            </div>"""

        # 投资建议
        recommendations = []
        if (
            comex_signal.silver_recommendation
            and comex_signal.silver_alert_level != ComexAlertLevel.SAFE
        ):
            recommendations.append(f"白银: {comex_signal.silver_recommendation}")
        if (
            comex_signal.gold_recommendation
            and comex_signal.gold_alert_level != ComexAlertLevel.SAFE
        ):
            recommendations.append(f"黄金: {comex_signal.gold_recommendation}")

        rec_html = ""
        if recommendations:
            rec_items = "".join(
                [
                    f'<div style="margin-bottom: 4px;">建议: {rec}</div>'
                    for rec in recommendations
                ]
            )
            rec_html = f"""<div style="padding: 10px 12px; font-size: 16px; color: #854d0e; background-color: #fef3c7; border-top: 1px solid #fde68a;">
                {rec_items}
            </div>"""

        # 趋势图表
        charts_html = ""
        images = {}

        if comex_signal.silver_chart_base64 or comex_signal.gold_chart_base64:
            chart_items = []

            if comex_signal.silver_chart_base64:
                # 使用 CID 引用图片
                cid = "silver_chart"
                images[cid] = comex_signal.silver_chart_base64

                chart_items.append(f"""
                    <div style="margin-bottom: 10px;">
                        <img src="cid:{cid}" 
                             alt="白银库存趋势" 
                             style="width: 100%; max-width: 560px; height: auto; border-radius: 4px;" />
                    </div>
                """)

            if comex_signal.gold_chart_base64:
                # 使用 CID 引用图片
                cid = "gold_chart"
                images[cid] = comex_signal.gold_chart_base64

                chart_items.append(f"""
                    <div style="margin-bottom: 10px;">
                        <img src="cid:{cid}" 
                             alt="黄金库存趋势" 
                             style="width: 100%; max-width: 560px; height: auto; border-radius: 4px;" />
                    </div>
                """)

            charts_html = f"""<div style="padding: 12px; background-color: #f8fafc; border-top: 1px solid #e2e8f0;">
                {"".join(chart_items)}
            </div>"""

        # 报告日期
        report_date_str = ""
        if comex_signal.report_date:
            report_date_str = (
                f" (数据日期: {comex_signal.report_date.strftime('%Y-%m-%d')})"
            )

        return (
            f"""<!-- COMEX Inventory Section -->
        <tr>
            <td style="padding: 24px 28px 20px 28px; border-top: 1px solid #d2d2d7;">
                <p style="margin: 0 0 14px 0; font-size: 11px; font-weight: 600; letter-spacing: 0.1em; color: #86868b; text-transform: uppercase;">COMEX库存监控{report_date_str}</p>
                <table width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                        <th style="padding: 12px 0 8px 0; text-align: left; font-size: 11px; font-weight: 600; letter-spacing: 0.08em; color: #86868b; text-transform: uppercase; border-top: 1px solid #d2d2d7;">品种</th>
                        <th style="padding: 12px 0 8px 0; text-align: right; font-size: 11px; font-weight: 600; letter-spacing: 0.08em; color: #86868b; text-transform: uppercase; border-top: 1px solid #d2d2d7;">库存</th>
                        <th style="padding: 12px 0 8px 0; text-align: center; font-size: 11px; font-weight: 600; letter-spacing: 0.08em; color: #86868b; text-transform: uppercase; border-top: 1px solid #d2d2d7;">状态</th>
                    </tr>
                    {table_rows}
                </table>
                {alert_html}
                {rec_html}
                {charts_html}
            </td>
        </tr>""",
            images,
        )


# ============================================================
# JSON Schema - LLM只返回结构化数据
# ============================================================
DIGEST_JSON_SCHEMA: Dict[str, Any] = {
    "name": "finnews_digest_data",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "subject": {
                "type": "string",
                "description": "邮件标题，格式: YYYY-MM-DD 市场日报：[今日核心内容]",
            },
            "news_clusters": {
                "type": "array",
                "description": "新闻综述组，按事件/主题聚合并按重要性排序",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "cluster_title": {
                            "type": "string",
                            "description": "综述标题（中文）",
                        },
                        "cluster_summary": {
                            "type": "string",
                            "description": "整合摘要（中文，1-3句话）",
                        },
                        "impact_tag": {
                            "type": "string",
                            "enum": ["Bullish", "Bearish", "Neutral"],
                            "description": "对贵金属整体影响方向",
                        },
                        "sources": {
                            "type": "array",
                            "description": "原始新闻列表（按重要性排序）",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "title": {
                                        "type": "string",
                                        "description": "原始新闻标题（中文）",
                                    },
                                    "source": {
                                        "type": "string",
                                        "description": "新闻来源",
                                    },
                                    "url": {
                                        "type": "string",
                                        "description": "新闻原文链接，无链接时返回空字符串",
                                    },
                                    "timestamp": {
                                        "type": "string",
                                        "description": "发布时间，格式 HH:MM，未知时返回空字符串",
                                    },
                                },
                                "required": ["title", "source", "url", "timestamp"],
                            },
                        },
                    },
                    "required": [
                        "cluster_title",
                        "cluster_summary",
                        "impact_tag",
                        "sources",
                    ],
                },
            },
            "analysis": {
                "type": "object",
                "additionalProperties": False,
                "description": "市场分析 (所有分析内容集中在此)",
                "properties": {
                    "market_sentiment": {
                        "type": "string",
                        "description": "市场情绪判断，30-60字要点式",
                    },
                    "price_outlook": {
                        "type": "string",
                        "description": "走势预判，30-60字要点式",
                    },
                    "risk_factors": {
                        "type": "string",
                        "description": "风险因素，30-60字要点式",
                    },
                    "trading_suggestion": {
                        "type": "string",
                        "description": "操作建议，30-60字要点式",
                    },
                },
                "required": [
                    "market_sentiment",
                    "price_outlook",
                    "risk_factors",
                    "trading_suggestion",
                ],
            },
        },
        "required": ["subject", "news_clusters", "analysis"],
    },
}


# ============================================================
# HTML 邮件模板 - Apple 科技风格：扁平层级 + 大内容区
# ============================================================
EMAIL_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; background-color: #f5f5f7; font-family: -apple-system, 'Helvetica Neue', Arial, sans-serif;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f5f5f7; padding: 24px 0;">
        <tr>
            <td align="center">
                <table width="100%" cellpadding="0" cellspacing="0" style="max-width: 680px; background-color: #ffffff; border-radius: 16px; overflow: hidden;">

                    <!-- Header -->
                    <tr>
                        <td style="padding: 32px 28px 24px 28px; border-bottom: 1px solid #d2d2d7;">
                            <p style="margin: 0 0 8px 0; font-size: 11px; font-weight: 600; letter-spacing: 0.1em; color: #86868b; text-transform: uppercase;">FinNews &nbsp;&middot;&nbsp; {datetime}</p>
                            <h1 style="margin: 0 0 12px 0; font-size: 21px; line-height: 1.35; font-weight: 700; color: #1d1d1f;">{subject}</h1>
                            {price_summary_line}
                        </td>
                    </tr>

                    <!-- Section: 市场行情 -->
                    <tr>
                        <td style="padding: 24px 28px 20px 28px;">
                            <p style="margin: 0 0 14px 0; font-size: 11px; font-weight: 600; letter-spacing: 0.1em; color: #86868b; text-transform: uppercase;">市场行情</p>
                            <table width="100%" cellpadding="0" cellspacing="0">
                                {vix_market_row}
                                {market_summary_row}
                                <tr>
                                    <th style="padding: 12px 0 8px 0; text-align: left; font-size: 11px; font-weight: 600; letter-spacing: 0.08em; color: #86868b; text-transform: uppercase; border-top: 1px solid #d2d2d7;">品种</th>
                                    <th style="padding: 12px 0 8px 0; text-align: right; font-size: 11px; font-weight: 600; letter-spacing: 0.08em; color: #86868b; text-transform: uppercase; border-top: 1px solid #d2d2d7;">价格</th>
                                    <th style="padding: 12px 0 8px 0; text-align: right; font-size: 11px; font-weight: 600; letter-spacing: 0.08em; color: #86868b; text-transform: uppercase; border-top: 1px solid #d2d2d7;">涨跌幅</th>
                                </tr>
                                {price_table}
                            </table>
                        </td>
                    </tr>

                    <!-- Section: 经济指标 (动态) -->
                    {econ_section}

                    <!-- Section: COMEX库存 (动态) -->
                    {comex_section}

                    <!-- Section: 新闻综述 -->
                    <tr>
                        <td style="padding: 24px 28px 20px 28px; border-top: 1px solid #d2d2d7;">
                            <p style="margin: 0 0 14px 0; font-size: 11px; font-weight: 600; letter-spacing: 0.1em; color: #86868b; text-transform: uppercase;">新闻综述</p>
                            {news_clusters}
                        </td>
                    </tr>

                    <!-- Section: 市场分析 -->
                    <tr>
                        <td style="padding: 24px 28px 20px 28px; border-top: 1px solid #d2d2d7;">
                            <p style="margin: 0 0 14px 0; font-size: 11px; font-weight: 600; letter-spacing: 0.1em; color: #86868b; text-transform: uppercase;">市场分析</p>
                            {analysis}
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="padding: 20px 28px 24px 28px; border-top: 1px solid #d2d2d7;">
                            <p style="margin: 0; font-size: 12px; color: #86868b; text-align: center;">FinNews &nbsp;|&nbsp; 黄金白银市场智能分析系统</p>
                            <p style="margin: 4px 0 0 0; font-size: 11px; color: #aeaeb2; text-align: center;">本报告由 AI 自动生成，仅供参考，不构成投资建议</p>
                        </td>
                    </tr>

                </table>
            </td>
        </tr>
    </table>

</body>
</html>"""
