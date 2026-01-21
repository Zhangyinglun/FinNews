"""
COMEX仓库库存数据爬虫
数据源: CME Group 每日库存报告 (Excel格式)
- 白银: https://www.cmegroup.com/delivery_reports/Silver_stocks.xls
- 黄金: https://www.cmegroup.com/delivery_reports/Gold_Stocks.xls

三级预警系统 (白银 Registered 库存):
- 🟢 安全: >= 40,000,000 oz
- 🟡 警戒线: < 40,000,000 oz (市场紧张)
- 🔴 生死线: < 30,000,000 oz (脱钩风险)
- ⚫ 熔断线: < 20,000,000 oz (系统性风险)
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

try:
    import xlrd

    XLRD_AVAILABLE = True
except ImportError:
    XLRD_AVAILABLE = False

from config.config import Config
from .base_scraper import BaseScraper


# COMEX 数据 URL
COMEX_URLS = {
    "silver": "https://www.cmegroup.com/delivery_reports/Silver_stocks.xls",
    "gold": "https://www.cmegroup.com/delivery_reports/Gold_Stocks.xls",
}

# 本地历史数据存储路径
HISTORY_FILE = Config.OUTPUT_DIR / "comex_history.json"


class ComexScraper(BaseScraper):
    """
    COMEX仓库库存数据爬虫

    抓取CME官方每日库存报告，解析Registered和Eligible库存数据。
    支持本地历史存储以计算周变化。
    """

    def __init__(self):
        super().__init__("COMEX")

        if not XLRD_AVAILABLE:
            raise ImportError("xlrd未安装。请运行: pip install xlrd")

        self.history_file = HISTORY_FILE
        self._ensure_history_file()

    def _ensure_history_file(self) -> None:
        """确保历史数据文件存在"""
        if not self.history_file.exists():
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            self.history_file.write_text("{}", encoding="utf-8")

    def _load_history(self) -> Dict[str, Any]:
        """加载历史数据"""
        try:
            return json.loads(self.history_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def _save_history(self, history: Dict[str, Any]) -> None:
        """保存历史数据"""
        self.history_file.write_text(
            json.dumps(history, indent=2, default=str, ensure_ascii=False),
            encoding="utf-8",
        )

    def _download_excel(self, url: str) -> Optional[bytes]:
        """
        下载Excel文件

        Args:
            url: CME Excel文件URL

        Returns:
            Excel文件二进制内容，失败返回None
        """
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            response = requests.get(
                url, headers=headers, timeout=Config.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            return response.content
        except requests.RequestException as e:
            self.logger.error(f"下载Excel失败 {url}: {e}")
            return None

    def _parse_excel(self, content: bytes, metal: str) -> Optional[Dict[str, Any]]:
        """
        解析CME Excel库存报告

        Args:
            content: Excel文件二进制内容
            metal: 金属类型 ("silver" 或 "gold")

        Returns:
            解析后的库存数据字典
        """
        try:
            workbook = xlrd.open_workbook(file_contents=content)
            sheet = workbook.sheet_by_index(0)

            data = {
                "metal": metal,
                "report_date": None,
                "registered": None,
                "eligible": None,
                "total": None,
                "registered_change": None,
                "eligible_change": None,
                "total_change": None,
                "depositories": [],
            }

            # 解析Excel内容
            for row_idx in range(sheet.nrows):
                row = [sheet.cell_value(row_idx, col) for col in range(sheet.ncols)]
                row_text = " ".join(str(cell).strip().upper() for cell in row if cell)

                # 查找报告日期 (通常在前几行)
                if "ACTIVITY DATE" in row_text or "REPORT DATE" in row_text:
                    for cell in row:
                        if isinstance(cell, float) and cell > 40000:
                            # Excel日期格式转换
                            try:
                                date_tuple = xlrd.xldate_as_tuple(
                                    cell, workbook.datemode
                                )
                                data["report_date"] = datetime(*date_tuple[:3])
                            except Exception:
                                pass
                        elif isinstance(cell, str) and cell.strip():
                            # 尝试解析字符串日期
                            try:
                                data["report_date"] = datetime.strptime(
                                    cell.strip(), "%m/%d/%Y"
                                )
                            except ValueError:
                                pass

                # 获取第一列文本 (用于精确匹配行标签)
                first_cell = str(row[0]).strip().upper() if row else ""

                # 查找 TOTAL REGISTERED 行 (第一列必须是标签，避免匹配注释行)
                if first_cell == "TOTAL REGISTERED":
                    data["registered"] = self._extract_total_today(row)
                    data["registered_change"] = self._extract_net_change(row)

                # 查找 TOTAL ELIGIBLE 行
                elif first_cell == "TOTAL ELIGIBLE":
                    data["eligible"] = self._extract_total_today(row)
                    data["eligible_change"] = self._extract_net_change(row)

                # 查找 COMBINED TOTAL 行
                elif first_cell in ("COMBINED TOTAL", "GRAND TOTAL"):
                    data["total"] = self._extract_total_today(row)
                    data["total_change"] = self._extract_net_change(row)

            # 如果没有找到日期，使用今天
            if data["report_date"] is None:
                data["report_date"] = datetime.now().replace(
                    hour=0, minute=0, second=0, microsecond=0
                )

            # 验证关键数据
            if data["registered"] is None and data["total"] is None:
                self.logger.warning(f"无法解析{metal}库存数据")
                return None

            return data

        except Exception as e:
            self.logger.error(f"解析Excel失败: {e}", exc_info=True)
            return None

    def _extract_total_today(self, row: List[Any]) -> Optional[float]:
        """
        从行数据中提取TOTAL TODAY值 (通常是最后一个数值列)

        Args:
            row: Excel行数据列表

        Returns:
            库存总量(盎司)
        """
        # 从右向左查找第一个有效数值
        numeric_values = []
        for cell in row:
            if isinstance(cell, (int, float)) and cell > 0:
                numeric_values.append(float(cell))

        # TOTAL TODAY 通常是倒数第一或第二个大数值
        if numeric_values:
            # 过滤掉明显不是库存数量的小数值
            large_values = [v for v in numeric_values if v > 10000]
            if large_values:
                return large_values[-1]  # 最后一个大数值通常是 TOTAL TODAY

        return None

    def _extract_net_change(self, row: List[Any]) -> Optional[float]:
        """
        从行数据中提取NET CHANGE值

        Args:
            row: Excel行数据列表

        Returns:
            净变化量(盎司)，可能为负数
        """
        # NET CHANGE 通常是中间位置的数值，可能为负
        numeric_values = []
        for cell in row:
            if isinstance(cell, (int, float)):
                numeric_values.append(float(cell))

        # 如果有多个数值，NET CHANGE 通常在中间位置
        if len(numeric_values) >= 4:
            # 典型列顺序: PREV TOTAL, RECEIVED, WITHDRAWN, NET CHANGE, ADJUSTMENT, TOTAL TODAY
            return numeric_values[3] if len(numeric_values) > 3 else None

        return None

    def _calculate_weekly_change(
        self, current_value: float, metal: str, value_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        计算周变化 (与7天前数据对比)

        Args:
            current_value: 当前值
            metal: 金属类型
            value_type: 数据类型 ("registered", "eligible", "total")

        Returns:
            包含变化量和百分比的字典
        """
        history = self._load_history()
        key = f"{metal}_{value_type}"

        # 查找7天前的数据
        records = history.get(key, [])
        if not records:
            return None

        # 找到大约7天前的记录
        now = datetime.now()
        week_ago = None
        for record in reversed(records):
            try:
                record_date = datetime.fromisoformat(record["date"])
                days_diff = (now - record_date).days
                if 6 <= days_diff <= 8:  # 允许±1天误差
                    week_ago = record
                    break
            except (KeyError, ValueError):
                continue

        if week_ago is None:
            return None

        prev_value = week_ago.get("value")
        if prev_value is None or prev_value == 0:
            return None

        change = current_value - prev_value
        change_pct = (change / prev_value) * 100

        return {
            "change": change,
            "change_percent": round(change_pct, 2),
            "prev_value": prev_value,
            "prev_date": week_ago.get("date"),
        }

    def _update_history(self, metal: str, data: Dict[str, Any]) -> None:
        """
        更新历史数据 (保留30天)

        Args:
            metal: 金属类型
            data: 当天的库存数据
        """
        history = self._load_history()
        date_str = (
            data["report_date"].isoformat()
            if data.get("report_date")
            else datetime.now().isoformat()
        )

        for value_type in ["registered", "eligible", "total"]:
            key = f"{metal}_{value_type}"
            if key not in history:
                history[key] = []

            value = data.get(value_type)
            if value is not None:
                # 检查是否已有当天数据
                today_str = date_str[:10]
                existing = [
                    r for r in history[key] if r.get("date", "")[:10] == today_str
                ]
                if not existing:
                    history[key].append({"date": date_str, "value": value})

                # 保留最近30天
                cutoff = datetime.now().timestamp() - 30 * 24 * 3600
                history[key] = [
                    r
                    for r in history[key]
                    if datetime.fromisoformat(r["date"]).timestamp() > cutoff
                ]

        self._save_history(history)

    def fetch_metal(self, metal: str) -> Optional[Dict[str, Any]]:
        """
        抓取单个金属的库存数据

        Args:
            metal: "silver" 或 "gold"

        Returns:
            标准化的库存数据记录
        """
        if metal not in COMEX_URLS:
            self.logger.error(f"不支持的金属类型: {metal}")
            return None

        url = COMEX_URLS[metal]
        self.logger.info(f"正在抓取COMEX {metal}库存数据...")

        # 下载Excel
        content = self._download_excel(url)
        if content is None:
            return None

        # 解析Excel
        data = self._parse_excel(content, metal)
        if data is None:
            return None

        # 计算周变化
        if data.get("registered"):
            weekly = self._calculate_weekly_change(
                data["registered"], metal, "registered"
            )
            if weekly:
                data["registered_weekly_change"] = weekly["change"]
                data["registered_weekly_change_pct"] = weekly["change_percent"]

        # 更新历史数据
        self._update_history(metal, data)

        # 构建标准记录
        record = {
            "source": "COMEX",
            "type": "inventory_data",
            "metal": metal,
            "report_date": data.get("report_date"),
            "timestamp": data.get("report_date"),  # 用于时间窗口过滤
            "registered": data.get("registered"),
            "eligible": data.get("eligible"),
            "total": data.get("total"),
            "registered_change": data.get("registered_change"),
            "eligible_change": data.get("eligible_change"),
            "total_change": data.get("total_change"),
            "registered_weekly_change": data.get("registered_weekly_change"),
            "registered_weekly_change_pct": data.get("registered_weekly_change_pct"),
            "fetched_at": datetime.now(),
        }

        # 计算百万盎司单位 (便于阅读)
        if record["registered"]:
            record["registered_million"] = round(record["registered"] / 1_000_000, 2)
        if record["eligible"]:
            record["eligible_million"] = round(record["eligible"] / 1_000_000, 2)
        if record["total"]:
            record["total_million"] = round(record["total"] / 1_000_000, 2)

        self.logger.info(
            f"COMEX {metal} 库存: Registered={record.get('registered_million', 'N/A')}M oz, "
            f"Total={record.get('total_million', 'N/A')}M oz"
        )

        return record

    def fetch(self) -> List[Dict[str, Any]]:
        """
        抓取所有金属的库存数据

        Returns:
            库存数据列表 (白银 + 黄金)
        """
        all_data = []

        # 根据配置决定是否启用
        if not getattr(Config, "ENABLE_COMEX", True):
            self.logger.info("COMEX数据源已禁用")
            return []

        for metal in ["silver", "gold"]:
            try:
                data = self.fetch_metal(metal)
                if data:
                    # 添加每日发布数据标记
                    data["daily_label"] = "每日发布数据"
                    all_data.append(data)
            except Exception as e:
                self.logger.error(f"抓取COMEX {metal}失败: {e}", exc_info=True)

        # 应用时间窗口过滤 (12小时)，允许回退到最新数据
        # COMEX每日更新，若无12小时内数据则显示最近一次
        filtered = self._filter_recent_records(
            all_data,
            window_hours=Config.FLASH_WINDOW_HOURS,
            allow_fallback=True,
            fallback_note="COMEX库存每日更新，显示最近一次数据",
            daily_label="每日发布数据",
        )

        return filtered
