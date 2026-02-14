"""
JSON存储模块
输出格式: Markdown块(LLM友好)
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

from config.config import Config

logger = logging.getLogger("storage.json")


class JSONStorage:
    """JSON文件存储"""

    def __init__(self):
        self.raw_dir = Config.RAW_DIR
        self.processed_dir = Config.PROCESSED_DIR

    def save_raw(self, data: List[Dict[str, Any]], filename: Optional[str] = None):
        """
        保存原始数据

        Args:
            data: 数据列表
            filename: 文件名(可选,默认自动生成)
        """
        if not filename:
            filename = f"raw_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        filepath = self.raw_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

        logger.info(f"原始数据已保存: {filepath}")

    def save_processed(
        self, data: List[Dict[str, Any]], filename: Optional[str] = None
    ):
        """
        保存处理后数据(Markdown格式)

        Args:
            data: 处理后的数据列表
            filename: 文件名(可选,默认自动生成)
        """
        if not filename:
            filename = f"processed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

        filepath = self.processed_dir / filename
        markdown = self._to_markdown(data)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(markdown)

        logger.info(f"处理数据已保存: {filepath}")

    def _to_markdown(self, data: List[Dict[str, Any]]) -> str:
        """
        转换为Markdown格式(LLM友好)

        Args:
            data: 数据列表

        Returns:
            Markdown格式文本
        """
        lines = [
            "# 黄金白银走势分析 - 数据汇总",
            f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "---",
            "",
        ]

        # 按来源分组
        news_items = [
            r
            for r in data
            if r.get("type") not in ["price_data", "economic_data", "fx_data"]
        ]
        price_items = [r for r in data if r.get("type") == "price_data"]
        econ_items = [r for r in data if r.get("type") == "economic_data"]
        fx_items = [r for r in data if r.get("type") == "fx_data"]

        # 1. 宏观经济指标
        if econ_items:
            lines.append("## 📊 宏观经济指标")
            lines.append("")
            for item in econ_items:
                change_str = ""
                if item.get("change_pct") is not None:
                    change_str = f" ({item['change_pct']:+.2f}%)"
                elif item.get("change") is not None:
                    change_str = f" ({item['change']:+.4f})"

                lines.append(
                    f"- **{item['indicator'].upper()}**: {item['value']}{change_str}"
                )
            lines.append("")

        # 2. 市场价格（增强显示）
        if price_items:
            lines.append("## 💰 最新市场价格与技术指标")
            lines.append("")
            for item in price_items:
                ticker_name = item.get("ticker_name", "Unknown")
                ticker = item.get("ticker", "")
                price = item.get("price", 0)

                # 基础价格信息
                price_line = f"### {ticker_name} ({ticker})"
                lines.append(price_line)
                lines.append(f"- **当前价格**: ${price:.2f}")

                # 涨跌幅信息
                if "change" in item and "change_percent" in item:
                    change = item["change"]
                    change_pct = item["change_percent"]
                    change_emoji = "📈" if change > 0 else "📉" if change < 0 else "➡️"
                    lines.append(
                        f"- **日涨跌**: {change_emoji} {change:+.2f} ({change_pct:+.2f}%)"
                    )

                # 周涨跌幅
                if "week_change_percent" in item:
                    week_change = item["week_change_percent"]
                    week_emoji = (
                        "📈" if week_change > 0 else "📉" if week_change < 0 else "➡️"
                    )
                    lines.append(f"- **周涨跌**: {week_emoji} {week_change:+.2f}%")

                # 当日行情
                if "high" in item and "low" in item and "open" in item:
                    lines.append(f"- **今日开盘**: ${item['open']:.2f}")
                    lines.append(f"- **今日最高**: ${item['high']:.2f}")
                    lines.append(f"- **今日最低**: ${item['low']:.2f}")

                # 成交量
                if "volume" in item and item["volume"] > 0:
                    volume_formatted = f"{item['volume']:,}"
                    lines.append(f"- **成交量**: {volume_formatted}")

                # 移动平均线
                if "ma5" in item:
                    lines.append(f"- **5日均线**: ${item['ma5']:.2f}")

                # 趋势判断
                if "change_percent" in item and "ma5" in item:
                    current = item.get("current_price", price)
                    ma5 = item["ma5"]
                    if current > ma5:
                        lines.append(f"- **趋势**: 🟢 价格在5日均线上方 (多头)")
                    elif current < ma5:
                        lines.append(f"- **趋势**: 🔴 价格在5日均线下方 (空头)")
                    else:
                        lines.append(f"- **趋势**: ⚪ 价格接近5日均线")

                lines.append("")
            lines.append("")

        # 3. 外汇数据
        if fx_items:
            lines.append("## 💱 外汇数据")
            lines.append("")
            for item in fx_items:
                lines.append(f"- **{item['pair']}**: {item['close']:.4f}")
            lines.append("")

        # 4. 新闻摘要
        if news_items:
            lines.append("## 📰 相关新闻与分析")
            lines.append("")

            # 按来源分组显示
            sources = {}
            for item in news_items:
                source = item.get("source", "Unknown")
                if source not in sources:
                    sources[source] = []
                sources[source].append(item)

            for source, items in sources.items():
                lines.append(f"### 📌 {source} ({len(items)}条)")
                lines.append("")

                for item in items[:10]:  # 每个源最多显示10条
                    timestamp = item.get("timestamp", "N/A")
                    if isinstance(timestamp, datetime):
                        timestamp = timestamp.strftime("%Y-%m-%d %H:%M")

                    title = item.get("title", "N/A")
                    summary = item.get("summary", "N/A")
                    if len(summary) > 200:
                        summary = summary[:200] + "..."

                    impact = item.get("impact_tag", "#Neutral")
                    url = item.get("url", "N/A")

                    lines.append(f"**{timestamp}** | {impact}")
                    lines.append(f"**标题**: {title}")
                    lines.append(f"**摘要**: {summary}")

                    # 添加完整内容（如果有）
                    full_content = item.get("full_content")
                    if full_content and len(full_content) > len(summary):
                        # 限制显示长度，避免报告过长
                        if len(full_content) > 2000:
                            full_content = full_content[:2000] + "..."
                        lines.append(f"**完整内容**: {full_content}")

                    lines.append(f"**链接**: {url}")
                    lines.append("")

        # 统计信息
        lines.append("---")
        lines.append("")
        lines.append("## 📈 数据统计")
        lines.append("")
        lines.append(f"- 经济指标: {len(econ_items)} 条")
        lines.append(f"- 价格数据: {len(price_items)} 条")
        lines.append(f"- 外汇数据: {len(fx_items)} 条")
        lines.append(f"- 新闻文章: {len(news_items)} 条")
        lines.append(f"- **总计**: {len(data)} 条")

        return "\n".join(lines)
