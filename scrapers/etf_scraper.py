"""
GLD ETF Scraper
抓取 SPDR Gold Shares (GLD) 的每日持仓数据 (吨数)
资金流向是判断机构意图的重要指标
"""

import csv
import io
import requests
from datetime import datetime
from typing import List, Dict, Any

from .base_scraper import BaseScraper
from config.config import Config


class EtfScraper(BaseScraper):
    """
    ETF持仓数据抓取器
    目前仅支持 GLD (SPDR Gold Shares)
    """

    def __init__(self):
        super().__init__("ETF_GLD")
        # SPDR GLD 官方历史数据 CSV
        self.url = (
            "https://www.spdrgoldshares.com/assets/dynamic/GLD/GLD_US_archive_EN.csv"
        )

    def fetch(self) -> List[Dict[str, Any]]:
        """
        抓取并解析 GLD 持仓数据
        """
        # 下载 CSV
        response = requests.get(self.url, timeout=30)
        response.raise_for_status()

        # 解析 CSV
        f = io.StringIO(response.text)
        reader = csv.DictReader(f)
        rows = list(reader)

        # 过滤无效行
        def is_valid(row):
            if not row.get("Date"):
                return False
            # 排除包含 HOLIDAY 的行
            if any(v and "HOLIDAY" in str(v).upper() for v in row.values()):
                return False
            return True

        valid_rows = [r for r in rows if is_valid(r)]

        if not valid_rows:
            self.logger.warning("GLD CSV 数据为空或全是节假日")
            return []

        # 获取最新两天的数据
        latest = valid_rows[-1]
        prev = valid_rows[-2] if len(valid_rows) > 1 else None

        # 提取日期
        date_str = latest.get("Date", "").strip()
        try:
            # 格式: 18-Nov-2004
            data_date = datetime.strptime(date_str, "%d-%b-%Y")
        except ValueError:
            data_date = datetime.now()
            self.logger.warning(f"GLD 日期格式解析失败: {date_str}, 使用当前时间")

        # 查找 Tonnes 列名
        tonnes_key = None
        for key in latest.keys():
            if key and "Tonnes" in key:
                tonnes_key = key
                break

        if not tonnes_key:
            self.logger.error("未找到 'Tonnes' 列")
            return []

        # 提取持仓量
        try:
            current_tonnes = float(latest[tonnes_key].replace(",", "").strip())
            prev_tonnes = (
                float(prev[tonnes_key].replace(",", "").strip())
                if prev
                else current_tonnes
            )
        except (ValueError, AttributeError) as e:
            self.logger.error(f"持仓数据解析失败: {e}")
            return []

        change = current_tonnes - prev_tonnes

        # 构建标题和摘要
        if change > 0:
            action = "增持"
            emoji = "📈"
            impact = "#Bullish"
        elif change < 0:
            action = "减持"
            emoji = "📉"
            impact = "#Bearish"
        else:
            action = "持平"
            emoji = "➖"
            impact = "#Neutral"

        change_str = f"{change:+.2f}"

        title = f"{emoji} GLD ETF资金流向: {action} {abs(change):.2f}吨"
        summary = (
            f"全球最大黄金ETF (GLD) 最新持仓数据:\n"
            f"- 当前持仓: {current_tonnes:.2f} 吨\n"
            f"- 较前日变化: {change_str} 吨\n"
            f"- 数据日期: {date_str}\n\n"
            f"机构资金流向是衡量西方投资需求的关键指标。"
        )

        record = self._create_base_record(
            title=title,
            summary=summary,
            url="https://www.spdrgoldshares.com/usa/",
            timestamp=data_date,
        )
        record["source"] = "SPDR Gold Shares"
        record["impact_tag"] = impact
        record["window_type"] = "flash"
        record["relevance_score"] = 0.95
        record["content"] = summary
        record["daily_label"] = "每日发布数据"

        result = [record]

        # 应用时间窗口过滤 (12小时)，允许回退到最新数据
        filtered = self._filter_recent_records(
            result,
            window_hours=Config.FLASH_WINDOW_HOURS,
            allow_fallback=True,
            fallback_note="GLD ETF每日更新，显示最近一次数据",
            daily_label="每日发布数据",
        )

        return filtered
