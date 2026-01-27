"""
4段式邮件摘要控制器
结构: 市场指数与数据 → 重点新闻 → 其他新闻 → 市场分析

架构:
- LLM 只返回结构化 JSON 数据 (新闻筛选 + 分析内容)
- Python 端负责 HTML 模板渲染 (价格/指标数据直接填充)
"""

from __future__ import annotations

import json
from datetime import datetime
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

    def _get_vix_indicator(self, signal: MarketSignal) -> Tuple[str, str, str]:
        """
        获取VIX信号灯指示器

        Args:
            signal: 市场信号

        Returns:
            (emoji, css_class, status_text)
        """
        if signal.is_urgent or signal.vix_alert_level == AlertLevel.CRITICAL:
            return "🔴", "vix-red", "紧急"
        elif signal.vix_alert_level == AlertLevel.WARNING:
            return "⚠️", "vix-yellow", "警戒"
        else:
            return "🟢", "vix-green", "正常"

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
        lines.append("=" * 60)
        lines.append("【新闻数据 - 请从中筛选重点新闻和其他新闻】")
        lines.append("=" * 60)
        lines.append("")

        # Flash窗口新闻
        lines.append("## Flash窗口新闻 (12小时内)")
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
        else:
            lines.append("- 暂无")
        lines.append("")

        # Cycle窗口新闻
        lines.append("## Cycle窗口新闻 (7天内)")
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
            lines.append("- 暂无")
        lines.append("")

        # Trend窗口新闻
        lines.append("## Trend窗口新闻 (30天内)")
        if data.trend.news:
            for i, news in enumerate(data.trend.news[:8], 1):
                lines.append(f"{i}. [{news.source}] {news.title}")
                if news.summary:
                    summary = (
                        news.summary[:150] + "..."
                        if len(news.summary) > 150
                        else news.summary
                    )
                    lines.append(f"   摘要: {summary}")
        else:
            lines.append("- 暂无")
        lines.append("")

        # === 任务说明 ===
        lines.append("=" * 60)
        lines.append("【你的任务】")
        lines.append("=" * 60)
        lines.append("")
        lines.append("1. 生成邮件标题 (subject)")
        lines.append("   - 格式: YYYY-MM-DD 市场日报：[关键信号] | [主要事件]")
        lines.append("   - 例如: 2026-01-20 市场日报：🔴 VIX红色警报 | 金价创历史新高")
        lines.append("")
        lines.append("2. 筛选重点新闻 (key_news)")
        lines.append("   - 从上述新闻中选取5-8条最重要的")
        lines.append("   - 只陈述事实，不要添加分析")
        lines.append("   - 每条包含: title, source, summary")
        lines.append("")
        lines.append("3. 筛选其他新闻 (other_news)")
        lines.append("   - 未入选重点的其他相关新闻")
        lines.append("   - 只陈述事实，不要添加分析")
        lines.append("   - 每条包含: title, source, summary")
        lines.append("")
        lines.append("4. 撰写市场分析 (analysis)")
        lines.append("   - market_sentiment: 当前市场情绪判断 (基于VIX和宏观数据)")
        lines.append("   - price_outlook: 黄金白银短期走势预判")
        lines.append("   - risk_factors: 需要关注的风险点")
        lines.append("   - trading_suggestion: 操作建议")
        lines.append("   - 每项100-200字，专业但易懂")
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
        prefix = signal.get_email_subject_tag()
        summary = signal.get_signal_summary()
        return f"{date_str} 市场日报：{prefix} | {summary}"

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

        # ... (VIX logic remains same)
        vix_emoji, vix_class, vix_status = self._get_vix_indicator(signal)
        vix_value = f"{signal.vix_value:.2f}" if signal.vix_value else "N/A"
        vix_change = (
            f"{signal.vix_change_percent:+.2f}%" if signal.vix_change_percent else "N/A"
        )

        # VIX背景颜色
        vix_bg_colors = {
            "vix-red": "#f8d7da",
            "vix-yellow": "#fff3cd",
            "vix-green": "#d4edda",
        }
        vix_bg_color = vix_bg_colors.get(vix_class, "#f8f9fa")

        # 构建价格表行
        price_rows = []
        has_any_value = False
        price_data = [
            ("黄金 (XAU)", signal.gold_price, signal.gold_change_percent, "$", ""),
            ("白银 (XAG)", signal.silver_price, signal.silver_change_percent, "$", ""),
            ("VIX 恐慌指数", signal.vix_value, signal.vix_change_percent, "", ""),
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
                change_color = "#28a745" if change >= 0 else "#dc3545"
                change_str = f'<span style="color: {change_color}; font-weight: 500;">{change:+.2f}%</span>'
            else:
                change_str = "-"

            price_rows.append(f"""<tr>
                <td style="padding: 10px 12px; text-align: left; border-bottom: 1px solid #f0f0f0;">{name}</td>
                <td style="padding: 10px 12px; text-align: right; border-bottom: 1px solid #f0f0f0;">{value_str}</td>
                <td style="padding: 10px 12px; text-align: right; border-bottom: 1px solid #f0f0f0;">{change_str}</td>
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
                <td colspan="3" style="padding: 10px 12px; font-size: 14px; color: #666; font-style: italic; border-bottom: 1px solid #f0f0f0;">
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
            econ_content = " | ".join(econ_items)
            econ_section_html = f"""<tr>
        <td style="padding: 0 16px 20px 16px;">
            <div style="border: 1px solid #e9ecef; border-radius: 8px; overflow: hidden;">
                <div style="background-color: #f8f9fa; padding: 10px 12px; border-bottom: 1px solid #e9ecef;">
                    <span style="font-size: 20px; font-weight: 600; color: #1a1a2e;">📅 经济指标</span>
                </div>
                <div style="padding: 12px; font-size: 16px; color: #333;">
                    {econ_content}
                </div>
            </div>
        </td>
    </tr>"""
        else:
            econ_section_html = ""  # 无数据时隐藏整个板块

        # 构建重点新闻
        key_news_html = self._render_news_list(digest_data.get("key_news", []))

        # 构建其他新闻
        other_news_html = self._render_news_list(digest_data.get("other_news", []))

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

        # 渲染完整HTML
        html = EMAIL_TEMPLATE.format(
            subject=subject,
            datetime=now.strftime("%Y-%m-%d %H:%M:%S"),
            vix_class=vix_class,
            vix_emoji=vix_emoji,
            vix_value=vix_value,
            vix_change=vix_change,
            vix_status=vix_status,
            vix_bg_color=vix_bg_color,
            macro_bias=macro_bias_text,
            price_table=price_table_html,
            econ_section=econ_section_html,
            comex_section=comex_section_html,
            key_news=key_news_html,
            other_news=other_news_html,
            analysis=analysis_html,
        )

        return html, images

    def _render_news_list(self, news_list: List[Dict[str, str]]) -> str:
        """渲染新闻列表HTML (内联样式，Gmail兼容)"""
        if not news_list:
            return '<div style="padding: 12px 0; color: #999; font-size: 16px;">暂无相关新闻</div>'

        items = []
        for i, news in enumerate(news_list):
            title = news.get("title", "无标题")
            source = news.get("source", "未知来源")
            summary = news.get("summary", "")

            # 最后一条不加底部边框
            border_style = (
                "border-bottom: 1px solid #f0f0f0;" if i < len(news_list) - 1 else ""
            )

            item_html = f"""<div style="padding: 12px 0; {border_style}">
                <div style="font-size: 19px; font-weight: 600; color: #1a1a2e; margin-bottom: 4px;">{title}</div>
                <div style="font-size: 16px; color: #999; margin-bottom: 6px;">来源: {source}</div>
                {f'<div style="font-size: 17px; color: #555; line-height: 1.6;">{summary}</div>' if summary else ""}
            </div>"""
            items.append(item_html)

        return "\n".join(items)

    def _render_analysis(self, analysis: Dict[str, str]) -> str:
        """渲染市场分析HTML (与新闻格式统一，内联样式)"""
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
                "border-bottom: 1px solid #f0f0f0;"
                if i < len(valid_sections) - 1
                else ""
            )

            item_html = f"""<div style="padding: 12px 0; {border_style}">
                <div style="font-size: 18px; font-weight: 600; color: #1a1a2e; margin-bottom: 4px;">{title}</div>
                <div style="font-size: 17px; color: #555; line-height: 1.6;">{content}</div>
            </div>"""
            items.append(item_html)

        if not items:
            return '<div style="padding: 12px 0; color: #999; font-size: 16px;">暂无分析内容</div>'

        return "\n".join(items)

    def _get_comex_indicator(
        self, comex_signal: Optional[ComexSignal]
    ) -> Tuple[str, str, str, str]:
        """
        获取COMEX库存信号灯指示器

        Args:
            comex_signal: COMEX信号对象

        Returns:
            (emoji, css_class, status_text, bg_color)
        """
        if comex_signal is None:
            return "❓", "comex-unknown", "数据缺失", "#f8f9fa"

        worst_level = comex_signal.get_worst_alert_level()

        if worst_level == ComexAlertLevel.SYSTEM_FAILURE:
            return "⚫", "comex-black", "系统风险", "#343a40"
        elif worst_level == ComexAlertLevel.RED:
            return "🔴", "comex-red", "高风险", "#f8d7da"
        elif worst_level == ComexAlertLevel.YELLOW:
            return "🟡", "comex-yellow", "需关注", "#fff3cd"
        else:
            return "🟢", "comex-green", "正常", "#d4edda"

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

        emoji, css_class, status_text, bg_color = self._get_comex_indicator(
            comex_signal
        )

        # 构建白银行
        silver_rows = []
        if comex_signal.silver_registered_million is not None:
            silver_emoji = {
                ComexAlertLevel.SYSTEM_FAILURE: "⚫",
                ComexAlertLevel.RED: "🔴",
                ComexAlertLevel.YELLOW: "🟡",
                ComexAlertLevel.SAFE: "🟢",
            }.get(comex_signal.silver_alert_level, "")

            daily_str = ""
            weekly_str = ""
            if comex_signal.silver_daily_change_pct is not None:
                change_color = (
                    "#28a745"
                    if comex_signal.silver_daily_change_pct >= 0
                    else "#dc3545"
                )
                daily_str = f'<span style="color: {change_color}; font-weight: 500;">({comex_signal.silver_daily_change_pct:+.1f}% 日)</span>'

            if comex_signal.silver_weekly_change_pct is not None:
                change_color = (
                    "#28a745"
                    if comex_signal.silver_weekly_change_pct >= 0
                    else "#dc3545"
                )
                weekly_str = f'<span style="color: {change_color}; font-weight: 500;">({comex_signal.silver_weekly_change_pct:+.1f}% 周)</span>'

            change_str = " ".join(filter(None, [daily_str, weekly_str]))

            silver_rows.append(f"""<tr>
                <td style="padding: 10px 12px; text-align: left; border-bottom: 1px solid #f0f0f0;">白银 (Registered)</td>
                <td style="padding: 10px 12px; text-align: right; border-bottom: 1px solid #f0f0f0;">{comex_signal.silver_registered_million:.2f}M oz</td>
                <td style="padding: 10px 12px; text-align: center; border-bottom: 1px solid #f0f0f0;">{silver_emoji} {change_str}</td>
            </tr>""")

        # 构建黄金行
        gold_rows = []
        if comex_signal.gold_registered_million is not None:
            gold_emoji = {
                ComexAlertLevel.SYSTEM_FAILURE: "⚫",
                ComexAlertLevel.RED: "🔴",
                ComexAlertLevel.YELLOW: "🟡",
                ComexAlertLevel.SAFE: "🟢",
            }.get(comex_signal.gold_alert_level, "")

            daily_str = ""
            weekly_str = ""
            if comex_signal.gold_daily_change_pct is not None:
                change_color = (
                    "#28a745" if comex_signal.gold_daily_change_pct >= 0 else "#dc3545"
                )
                daily_str = f'<span style="color: {change_color}; font-weight: 500;">({comex_signal.gold_daily_change_pct:+.1f}% 日)</span>'

            if comex_signal.gold_weekly_change_pct is not None:
                change_color = (
                    "#28a745" if comex_signal.gold_weekly_change_pct >= 0 else "#dc3545"
                )
                weekly_str = f'<span style="color: {change_color}; font-weight: 500;">({comex_signal.gold_weekly_change_pct:+.1f}% 周)</span>'

            change_str = " ".join(filter(None, [daily_str, weekly_str]))

            gold_rows.append(f"""<tr>
                <td style="padding: 10px 12px; text-align: left; border-bottom: 1px solid #f0f0f0;">黄金 (Registered)</td>
                <td style="padding: 10px 12px; text-align: right; border-bottom: 1px solid #f0f0f0;">{comex_signal.gold_registered_million:.2f}M oz</td>
                <td style="padding: 10px 12px; text-align: center; border-bottom: 1px solid #f0f0f0;">{gold_emoji} {change_str}</td>
            </tr>""")

        if not silver_rows and not gold_rows:
            return "", {}

        table_rows = "\n".join(silver_rows + gold_rows)

        # 构建警报消息
        alert_messages = []
        if comex_signal.silver_alert_message:
            alert_messages.append(comex_signal.silver_alert_message)
        if comex_signal.gold_alert_message:
            alert_messages.append(comex_signal.gold_alert_message)

        alert_html = ""
        if alert_messages:
            alert_items = "".join(
                [
                    f'<div style="margin-bottom: 4px;">{msg}</div>'
                    for msg in alert_messages
                ]
            )
            alert_html = f"""<div style="padding: 10px 12px; font-size: 16px; background-color: #fafafa; border-top: 1px solid #e9ecef;">
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
                    f'<div style="margin-bottom: 4px;">💡 {rec}</div>'
                    for rec in recommendations
                ]
            )
            rec_html = f"""<div style="padding: 10px 12px; font-size: 16px; color: #856404; background-color: #fff3cd; border-top: 1px solid #e9ecef;">
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

            charts_html = f"""<div style="padding: 12px; background-color: #fafafa; border-top: 1px solid #e9ecef;">
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
            <td style="padding: 0 16px 20px 16px;">
                <div style="border: 1px solid #e9ecef; border-radius: 8px; overflow: hidden;">
                    <div style="background-color: #f8f9fa; padding: 10px 12px; border-bottom: 1px solid #e9ecef;">
                        <span style="font-size: 20px; font-weight: 600; color: #1a1a2e;">🏦 COMEX库存监控{report_date_str}</span>
                    </div>
                    <table width="100%" cellpadding="0" cellspacing="0" style="font-size: 18px;">
                        <tr style="background-color: #f8f9fa;">
                            <th style="padding: 10px 12px; text-align: left; font-weight: 600; color: #666; font-size: 16px; border-bottom: 1px solid #e9ecef;">品种</th>
                            <th style="padding: 10px 12px; text-align: right; font-weight: 600; color: #666; font-size: 16px; border-bottom: 1px solid #e9ecef;">库存</th>
                            <th style="padding: 10px 12px; text-align: center; font-weight: 600; color: #666; font-size: 16px; border-bottom: 1px solid #e9ecef;">状态</th>
                        </tr>
                        {table_rows}
                    </table>
                    {alert_html}
                    {rec_html}
                    {charts_html}
                </div>
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
                "description": "邮件标题，格式: YYYY-MM-DD 市场日报：[信号] | [事件]",
            },
            "key_news": {
                "type": "array",
                "description": "重点新闻 (5-8条)，只陈述事实",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "title": {"type": "string"},
                        "source": {"type": "string"},
                        "summary": {"type": "string"},
                    },
                    "required": ["title", "source", "summary"],
                },
            },
            "other_news": {
                "type": "array",
                "description": "其他新闻，只陈述事实",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "title": {"type": "string"},
                        "source": {"type": "string"},
                        "summary": {"type": "string"},
                    },
                    "required": ["title", "source", "summary"],
                },
            },
            "analysis": {
                "type": "object",
                "additionalProperties": False,
                "description": "市场分析 (所有分析内容集中在此)",
                "properties": {
                    "market_sentiment": {
                        "type": "string",
                        "description": "市场情绪判断",
                    },
                    "price_outlook": {"type": "string", "description": "走势预判"},
                    "risk_factors": {"type": "string", "description": "风险因素"},
                    "trading_suggestion": {"type": "string", "description": "操作建议"},
                },
                "required": [
                    "market_sentiment",
                    "price_outlook",
                    "risk_factors",
                    "trading_suggestion",
                ],
            },
        },
        "required": ["subject", "key_news", "other_news", "analysis"],
    },
}


# ============================================================
# HTML 邮件模板 - 整洁 + 结构化 + 统一格式
# ============================================================
EMAIL_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; background-color: #f5f5f5; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f5f5f5; padding: 8px 0;">
        <tr>
            <td align="center">
                <table width="100%" cellpadding="0" cellspacing="0" style="max-width: 600px; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                    
                    <!-- Header -->
                    <tr>
                        <td style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); padding: 20px 16px;">
                            <h1 style="margin: 0; color: #ffffff; font-size: 24px; font-weight: 600;">{subject}</h1>
                            <p style="margin: 8px 0 0 0; color: rgba(255,255,255,0.7); font-size: 14px;">生成时间: {datetime}</p>
                        </td>
                    </tr>

                    <!-- VIX Signal -->
                    <tr>
                        <td style="padding: 16px 16px 12px 16px;">
                            <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f8f9fa; border-radius: 8px; padding: 12px;">
                                <tr>
                                    <td width="50" style="vertical-align: middle; padding: 10px;">
                                        <div style="width: 48px; height: 48px; border-radius: 50%; background-color: {vix_bg_color}; text-align: center; line-height: 48px; font-size: 26px;">{vix_emoji}</div>
                                    </td>
                                    <td style="vertical-align: middle; padding: 10px;">
                                        <div style="font-size: 20px; font-weight: 600; color: #1a1a2e;">VIX: {vix_value} <span style="font-weight: 400; color: #666;">({vix_change})</span></div>
                                        <div style="font-size: 16px; color: #666; margin-top: 4px;">市场状态: {vix_status} | 宏观倾向: {macro_bias}</div>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Section 1: Market Data -->
                    <tr>
                        <td style="padding: 0 16px 20px 16px;">
                            <div style="border: 1px solid #e9ecef; border-radius: 8px; overflow: hidden;">
                                <div style="background-color: #f8f9fa; padding: 10px 12px; border-bottom: 1px solid #e9ecef;">
                                    <span style="font-size: 20px; font-weight: 600; color: #1a1a2e;">📈 市场行情</span>
                                </div>
                                <table width="100%" cellpadding="0" cellspacing="0" style="font-size: 18px;">
                                    <tr style="background-color: #f8f9fa;">
                                        <th style="padding: 10px 12px; text-align: left; font-weight: 600; color: #666; font-size: 16px; border-bottom: 1px solid #e9ecef;">品种</th>
                                        <th style="padding: 10px 12px; text-align: right; font-weight: 600; color: #666; font-size: 16px; border-bottom: 1px solid #e9ecef;">价格</th>
                                        <th style="padding: 10px 12px; text-align: right; font-weight: 600; color: #666; font-size: 16px; border-bottom: 1px solid #e9ecef;">涨跌</th>
                                    </tr>
                                    {price_table}
                                </table>
                            </div>
                        </td>
                    </tr>

                    <!-- Section 1.5: Economic Indicators (独立板块) -->
                    {econ_section}

                    <!-- Section 1.6: COMEX Inventory (dynamically inserted) -->
                    {comex_section}

                    <!-- Section 2: Key News -->
                    <tr>
                        <td style="padding: 0 16px 20px 16px;">
                            <div style="border: 1px solid #e9ecef; border-radius: 8px; overflow: hidden;">
                                <div style="background-color: #f8f9fa; padding: 10px 12px; border-bottom: 1px solid #e9ecef;">
                                    <span style="font-size: 20px; font-weight: 600; color: #1a1a2e;">📰 重点新闻</span>
                                </div>
                                <div style="padding: 8px 12px;">
                                    {key_news}
                                </div>
                            </div>
                        </td>
                    </tr>

                    <!-- Section 3: Other News -->
                    <tr>
                        <td style="padding: 0 16px 20px 16px;">
                            <div style="border: 1px solid #e9ecef; border-radius: 8px; overflow: hidden;">
                                <div style="background-color: #f8f9fa; padding: 10px 12px; border-bottom: 1px solid #e9ecef;">
                                    <span style="font-size: 20px; font-weight: 600; color: #1a1a2e;">📋 其他新闻</span>
                                </div>
                                <div style="padding: 8px 12px;">
                                    {other_news}
                                </div>
                            </div>
                        </td>
                    </tr>

                    <!-- Section 4: Analysis -->
                    <tr>
                        <td style="padding: 0 16px 20px 16px;">
                            <div style="border: 1px solid #e9ecef; border-radius: 8px; overflow: hidden;">
                                <div style="background-color: #f8f9fa; padding: 10px 12px; border-bottom: 1px solid #e9ecef;">
                                    <span style="font-size: 20px; font-weight: 600; color: #1a1a2e;">🔍 市场分析</span>
                                </div>
                                <div style="padding: 8px 12px;">
                                    {analysis}
                                </div>
                            </div>
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="padding: 16px 16px; background-color: #f8f9fa; border-top: 1px solid #e9ecef;">
                            <p style="margin: 0; font-size: 14px; color: #999; text-align: center;">FinNews - 黄金白银市场智能分析系统</p>
                            <p style="margin: 6px 0 0 0; font-size: 13px; color: #bbb; text-align: center;">本报告由AI自动生成，仅供参考，不构成投资建议</p>
                        </td>
                    </tr>

                </table>
            </td>
        </tr>
    </table>

</body>
</html>"""
