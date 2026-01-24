"""
COMEX 库存趋势图表生成器 (Pillow版)

使用 Pillow (PIL) 生成 14 天库存趋势图，返回 base64 编码的 PNG。
替换 matplotlib 以解决 Python 3.14 的兼容性问题。
"""

import base64
import json
import logging
import math
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger("utils.comex_chart")


class ComexChartGenerator:
    """COMEX 库存趋势图表生成器 (使用 Pillow)"""

    def __init__(self, history_file: Path):
        """
        初始化图表生成器

        Args:
            history_file: 包含历史数据的 JSON 文件路径
        """
        self.history_file = history_file
        self.width = 560
        self.height = 280
        # 边距
        self.margin_left = 60
        self.margin_right = 40
        self.margin_top = 40
        self.margin_bottom = 30

        # 绘图区域
        self.plot_width = self.width - self.margin_left - self.margin_right
        self.plot_height = self.height - self.margin_top - self.margin_bottom

    def _extract_time_series(
        self, metal: str, value_type: str = "registered", days: int = 14
    ) -> Tuple[List[datetime], List[float]]:
        """从历史文件提取时间序列数据"""
        if not self.history_file.exists():
            return [], []

        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                history = json.load(f)

            dates = []
            values = []

            # 截止日期 (今天)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            # 构造键名 (例如: silver_registered)
            key = f"{metal}_{value_type}"
            records = history.get(key, [])

            # 如果是旧格式 (list of dicts with all metals)，尝试兼容 (虽然现在看起来是新格式)
            if isinstance(history, list):
                logger.warning("检测到旧版历史数据格式，可能无法正确解析")
                return [], []

            # 按日期排序
            sorted_records = sorted(records, key=lambda x: x["date"])

            for record in sorted_records:
                # 解析日期 (ISO格式: 2026-01-21T00:00:00)
                try:
                    dt_str = record["date"]
                    if "T" in dt_str:
                        rec_date = datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S")
                    else:
                        rec_date = datetime.strptime(dt_str, "%Y-%m-%d")
                except ValueError:
                    continue

                # 过滤日期范围
                if start_date <= rec_date <= end_date:
                    val = record["value"]
                    # 转换为百万盎司 (如果是原始值)
                    # 假设原始值是盎司，我们需要除以 1,000,000
                    # 但从前面的日志看，库存是 "114.26M oz"，说明 RuleEngine 可能已经处理过了？
                    # 检查 JSON: "value": 119542537.55
                    # 这是一个大数值，需要除以 1,000,000
                    val_million = val / 1_000_000.0

                    dates.append(rec_date)
                    values.append(val_million)

            return dates, values

        except Exception as e:
            logger.error(f"提取 COMEX 历史数据失败: {e}", exc_info=True)
            return [], []

    def _get_y_pos(self, value: float, min_val: float, max_val: float) -> float:
        """计算 Y 轴坐标 (值越大，坐标越小/越靠上)"""
        if max_val == min_val:
            return self.margin_top + self.plot_height / 2

        # 归一化位置 (0.0 - 1.0)
        normalized = (value - min_val) / (max_val - min_val)
        # 翻转 Y 轴 (画布原点在左上角)
        return self.margin_top + self.plot_height * (1 - normalized)

    def _get_x_pos(self, index: int, total_points: int) -> float:
        """计算 X 轴坐标"""
        if total_points <= 1:
            return self.margin_left + self.plot_width / 2

        step = self.plot_width / (total_points - 1)
        return self.margin_left + index * step

    def generate_chart(
        self, metal: str, days: int = 14, value_type: str = "registered"
    ) -> Optional[str]:
        """
        生成趋势图表

        Args:
            metal: "silver" 或 "gold"
            days: 展示天数 (默认 14)
            value_type: 数据类型 (默认 "registered")

        Returns:
            base64 编码的 PNG 字符串，失败返回 None
        """
        dates, values = self._extract_time_series(metal, value_type, days)

        if not dates or not values:
            logger.warning(f"无法生成 {metal} 图表: 数据不足")
            return None

        try:
            # 创建画布
            img = Image.new("RGB", (self.width, self.height), color="white")
            draw = ImageDraw.Draw(img)

            # 配置颜色
            line_color = (
                (108, 117, 125) if metal == "silver" else (255, 193, 7)
            )  # #6c757d / #ffc107
            point_color = line_color
            grid_color = (233, 236, 239)  # #e9ecef
            text_color = (33, 37, 41)  # #212529

            # 加载字体 (尝试加载系统字体，否则使用默认)
            try:
                # 尝试 Windows 常见字体
                title_font = ImageFont.truetype("arialbd.ttf", 16)
                label_font = ImageFont.truetype("arial.ttf", 11)
            except IOError:
                # 回退到默认
                title_font = ImageFont.load_default()
                label_font = ImageFont.load_default()

            # 计算数据范围 (Y轴) - 增加一点缓冲区
            min_val = min(values)
            max_val = max(values)
            y_padding = (
                (max_val - min_val) * 0.1 if max_val != min_val else max_val * 0.1
            )
            min_scale = min_val - y_padding
            max_scale = max_val + y_padding

            # 1. 绘制标题
            metal_cn = "白银" if metal == "silver" else "黄金"
            title = f"COMEX {metal_cn} Registered 库存趋势 ({days}天)"
            # 居中标题
            left, top, right, bottom = draw.textbbox((0, 0), title, font=title_font)
            title_w = right - left

            draw.text(
                ((self.width - title_w) / 2, 10),
                title,
                fill=text_color,
                font=title_font,
            )

            # 2. 绘制网格线和 Y 轴标签
            # 绘制 5 条水平网格线
            num_grid_lines = 5
            for i in range(num_grid_lines):
                val = min_scale + (max_scale - min_scale) * i / (num_grid_lines - 1)
                y = self._get_y_pos(val, min_scale, max_scale)

                # 网格线
                draw.line(
                    [(self.margin_left, y), (self.width - self.margin_right, y)],
                    fill=grid_color,
                    width=1,
                )

                # Y轴标签 (靠右对齐到 margin_left)
                label = f"{val:.1f}M"
                left, top, right, bottom = draw.textbbox((0, 0), label, font=label_font)
                label_w = right - left
                label_h = bottom - top

                draw.text(
                    (self.margin_left - label_w - 5, y - label_h / 2),
                    label,
                    fill=text_color,
                    font=label_font,
                )

            # 3. 绘制数据线和点
            points = []
            for i, val in enumerate(values):
                x = self._get_x_pos(i, len(values))
                y = self._get_y_pos(val, min_scale, max_scale)
                points.append((x, y))

            # 绘制折线
            if len(points) > 1:
                draw.line(points, fill=line_color, width=2)
            elif len(points) == 1:
                pass  # 只有一个点时不画线

            # 绘制数据点
            dot_radius = 3
            for x, y in points:
                draw.ellipse(
                    (x - dot_radius, y - dot_radius, x + dot_radius, y + dot_radius),
                    fill=point_color,
                )

            # 4. 绘制 X 轴日期标签
            # 根据数据点数量决定间隔
            step = max(1, len(dates) // 7)
            for i in range(0, len(dates), step):
                x = self._get_x_pos(i, len(values))
                date_str = dates[i].strftime("%m/%d")

                left, top, right, bottom = draw.textbbox(
                    (0, 0), date_str, font=label_font
                )
                w = right - left

                draw.text(
                    (x - w / 2, self.height - self.margin_bottom + 5),
                    date_str,
                    fill=text_color,
                    font=label_font,
                )

            # 2. 绘制网格线和 Y 轴标签
            # 绘制 5 条水平网格线
            num_grid_lines = 5
            for i in range(num_grid_lines):
                val = min_scale + (max_scale - min_scale) * i / (num_grid_lines - 1)
                y = self._get_y_pos(val, min_scale, max_scale)

                # 网格线
                draw.line(
                    [(self.margin_left, y), (self.width - self.margin_right, y)],
                    fill=grid_color,
                    width=1,
                )

                # Y轴标签 (靠右对齐到 margin_left)
                label = f"{val:.1f}M"
                try:
                    left, top, right, bottom = draw.textbbox(
                        (0, 0), label, font=label_font
                    )
                    label_w = right - left
                    label_h = bottom - top
                except AttributeError:
                    label_w, label_h = draw.textsize(label, font=label_font)

                draw.text(
                    (self.margin_left - label_w - 5, y - label_h / 2),
                    label,
                    fill=text_color,
                    font=label_font,
                )

            # 3. 绘制数据线和点
            points = []
            for i, val in enumerate(values):
                x = self._get_x_pos(i, len(values))
                y = self._get_y_pos(val, min_scale, max_scale)
                points.append((x, y))

            # 绘制折线
            if len(points) > 1:
                draw.line(points, fill=line_color, width=2)

            # 绘制数据点
            dot_radius = 3
            for x, y in points:
                draw.ellipse(
                    (x - dot_radius, y - dot_radius, x + dot_radius, y + dot_radius),
                    fill=point_color,
                )

            # 4. 绘制 X 轴日期标签
            # 根据数据点数量决定间隔
            step = max(1, len(dates) // 7)
            for i in range(0, len(dates), step):
                x = self._get_x_pos(i, len(values))
                date_str = dates[i].strftime("%m/%d")

                try:
                    left, top, right, bottom = draw.textbbox(
                        (0, 0), date_str, font=label_font
                    )
                    w = right - left
                except AttributeError:
                    w, _ = draw.textsize(date_str, font=label_font)

                draw.text(
                    (x - w / 2, self.height - self.margin_bottom + 5),
                    date_str,
                    fill=text_color,
                    font=label_font,
                )

            # 5. 标注最新值
            last_x, last_y = points[-1]
            last_val = values[-1]
            label = f"{last_val:.1f}M"
            draw.text(
                (last_x + 5, last_y - 10), label, fill=line_color, font=label_font
            )

            # 输出为 Base64
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            img_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

            logger.info(f"✅ {metal} 图表生成成功 (Pillow)")
            return img_base64

        except Exception as e:
            logger.error(f"Pillow 生成图表失败: {e}", exc_info=True)
            return None

    def generate_all_charts(self, days: int = 14) -> Dict[str, Optional[str]]:
        """生成所有品种的图表"""
        return {
            "silver_chart": self.generate_chart("silver", days, "registered"),
            "gold_chart": self.generate_chart("gold", days, "registered"),
        }
