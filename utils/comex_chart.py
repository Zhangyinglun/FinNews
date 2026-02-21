"""COMEX 库存趋势图表生成器 (Pillow 增强版)。"""

import base64
import json
import logging
import math
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, cast

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger("utils.comex_chart")


class ComexChartGenerator:
    """COMEX 库存趋势图表生成器 (使用 Pillow)。"""

    def __init__(self, history_file: Path):
        """
        初始化图表生成器

        Args:
            history_file: 包含历史数据的 JSON 文件路径
        """
        self.history_file = history_file
        self.width = 560
        self.height = 300
        # 边距
        self.margin_left = 58
        self.margin_right = 26
        self.margin_top = 54
        self.margin_bottom = 36

        # 绘图区域
        self.plot_width = self.width - self.margin_left - self.margin_right
        self.plot_height = self.height - self.margin_top - self.margin_bottom

    @staticmethod
    def _try_load_font(candidates: List[str], size: int) -> Any:
        """尝试按候选列表加载字体，失败则回退到默认字体。"""
        for name in candidates:
            try:
                return ImageFont.truetype(name, size)
            except OSError:
                continue
        return ImageFont.load_default()

    @staticmethod
    def _format_million(value: float) -> str:
        """格式化百万盎司数值。"""
        if value >= 100:
            return f"{value:.0f}M"
        if value >= 10:
            return f"{value:.1f}M"
        return f"{value:.2f}M"

    @staticmethod
    def _draw_vertical_gradient(
        draw: ImageDraw.ImageDraw,
        left: int,
        top: int,
        right: int,
        bottom: int,
        start_rgb: Tuple[int, int, int],
        end_rgb: Tuple[int, int, int],
    ) -> None:
        """绘制垂直背景渐变。"""
        height = max(1, bottom - top)
        for y in range(height):
            ratio = y / height
            r = int(start_rgb[0] * (1 - ratio) + end_rgb[0] * ratio)
            g = int(start_rgb[1] * (1 - ratio) + end_rgb[1] * ratio)
            b = int(start_rgb[2] * (1 - ratio) + end_rgb[2] * ratio)
            draw.line([(left, top + y), (right, top + y)], fill=(r, g, b))

    @staticmethod
    def _draw_dashed_line(
        draw: ImageDraw.ImageDraw,
        start: Tuple[float, float],
        end: Tuple[float, float],
        dash: int,
        gap: int,
        fill: Tuple[int, int, int],
        width: int,
    ) -> None:
        """绘制虚线。"""
        x1, y1 = start
        x2, y2 = end
        length = math.hypot(x2 - x1, y2 - y1)
        if length <= 0:
            return

        unit_x = (x2 - x1) / length
        unit_y = (y2 - y1) / length
        progress = 0.0

        while progress < length:
            seg_start = progress
            seg_end = min(progress + dash, length)
            sx = x1 + unit_x * seg_start
            sy = y1 + unit_y * seg_start
            ex = x1 + unit_x * seg_end
            ey = y1 + unit_y * seg_end
            draw.line([(sx, sy), (ex, ey)], fill=fill, width=width)
            progress += dash + gap

    @staticmethod
    def _text_size(draw: ImageDraw.ImageDraw, text: str, font: Any) -> Tuple[int, int]:
        """兼容不同 Pillow 版本获取文本尺寸。"""
        try:
            left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
            return int(right - left), int(bottom - top)
        except AttributeError:
            width, height = cast(Any, draw).textsize(text, font=font)
            return int(width), int(height)

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
            # 超采样抗锯齿：在高分辨率画布绘制后缩小
            scale = 2
            canvas_w = self.width * scale
            canvas_h = self.height * scale

            margin_left = self.margin_left * scale
            margin_right = self.margin_right * scale
            margin_top = self.margin_top * scale
            margin_bottom = self.margin_bottom * scale

            plot_left = margin_left
            plot_right = canvas_w - margin_right
            plot_top = margin_top
            plot_bottom = canvas_h - margin_bottom
            plot_width = plot_right - plot_left
            plot_height = plot_bottom - plot_top

            # 配色
            line_color = (126, 141, 164) if metal == "silver" else (176, 138, 45)
            line_shadow = (94, 109, 130)
            grid_color = (223, 229, 238)
            text_color = (51, 65, 85)
            label_muted = (120, 137, 160)
            border_color = (214, 223, 234)
            fill_alpha_max = 40 if metal == "silver" else 48

            # 背景
            img = Image.new("RGB", (canvas_w, canvas_h), color=(249, 251, 254))
            draw = ImageDraw.Draw(img)
            self._draw_vertical_gradient(
                draw,
                0,
                0,
                canvas_w,
                canvas_h,
                (251, 253, 255),
                (243, 248, 253),
            )

            # 绘图区容器
            container_pad = 8 * scale
            draw.rounded_rectangle(
                (
                    plot_left - container_pad,
                    plot_top - container_pad,
                    plot_right + container_pad,
                    plot_bottom + container_pad,
                ),
                radius=14 * scale,
                fill=(254, 255, 255),
                outline=border_color,
                width=max(1, scale),
            )

            # 字体
            title_font = self._try_load_font(
                ["arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf"],
                16 * scale,
            )
            label_font = self._try_load_font(
                ["arial.ttf", "Arial.ttf", "DejaVuSans.ttf"],
                11 * scale,
            )
            value_font = self._try_load_font(
                ["arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf"],
                10 * scale,
            )
            meta_font = self._try_load_font(
                ["arial.ttf", "Arial.ttf", "DejaVuSans.ttf"],
                9 * scale,
            )

            # 数值范围
            min_val = min(values)
            max_val = max(values)
            span = max_val - min_val
            if span <= 0:
                span = max(1.0, max_val * 0.05)
            y_padding = max(span * 0.16, 0.20)
            min_scale = max(0.0, min_val - y_padding)
            max_scale = max_val + y_padding

            # 标题
            metal_en = "Silver" if metal == "silver" else "Gold"
            title = f"COMEX {metal_en} Registered Inventory ({days} Days)"
            title_w, _ = self._text_size(draw, title, title_font)
            draw.text(
                ((canvas_w - title_w) / 2, 10 * scale),
                title,
                fill=text_color,
                font=title_font,
            )

            # 副标题：日期范围 + 数据类型
            date_range = (
                f"{dates[0].strftime('%Y-%m-%d')} ~ {dates[-1].strftime('%Y-%m-%d')}"
            )
            subtitle = f"{value_type.capitalize()} | {date_range}"
            sub_w, _ = self._text_size(draw, subtitle, meta_font)
            draw.text(
                ((canvas_w - sub_w) / 2, 31 * scale),
                subtitle,
                fill=label_muted,
                font=meta_font,
            )

            # 右上角简洁变化标签
            delta = values[-1] - values[0]
            delta_pct = (delta / values[0] * 100.0) if values[0] else 0.0
            delta_text = f"{delta_pct:+.2f}%"
            tag_w, tag_h = self._text_size(draw, delta_text, meta_font)
            tag_pad_x = 6 * scale
            tag_pad_y = 3 * scale
            tag_x2 = plot_right + container_pad
            tag_x1 = tag_x2 - tag_w - 2 * tag_pad_x
            tag_y1 = 10 * scale
            tag_y2 = tag_y1 + tag_h + 2 * tag_pad_y
            tag_fill = (241, 246, 252) if delta >= 0 else (250, 242, 242)
            tag_text_color = (86, 113, 144) if delta >= 0 else (153, 96, 96)

            draw.rounded_rectangle(
                (tag_x1, tag_y1, tag_x2, tag_y2),
                radius=6 * scale,
                fill=tag_fill,
                outline=border_color,
                width=max(1, scale),
            )
            draw.text(
                (tag_x1 + tag_pad_x, tag_y1 + tag_pad_y),
                delta_text,
                fill=tag_text_color,
                font=meta_font,
            )

            # 网格与 Y 轴标签
            num_grid_lines = 5
            for i in range(num_grid_lines):
                val = min_scale + (max_scale - min_scale) * i / (num_grid_lines - 1)
                normalized = (val - min_scale) / (max_scale - min_scale)
                y = plot_top + plot_height * (1 - normalized)

                self._draw_dashed_line(
                    draw,
                    (plot_left, y),
                    (plot_right, y),
                    dash=8 * scale,
                    gap=6 * scale,
                    fill=grid_color,
                    width=max(1, scale),
                )

                y_label = self._format_million(val)
                label_w, label_h = self._text_size(draw, y_label, label_font)
                draw.text(
                    (plot_left - label_w - 6 * scale, y - label_h / 2),
                    y_label,
                    fill=label_muted,
                    font=label_font,
                )

            # 计算点坐标
            points: List[Tuple[float, float]] = []
            for i, value in enumerate(values):
                if len(values) <= 1:
                    x = plot_left + plot_width / 2
                else:
                    x = plot_left + i * plot_width / (len(values) - 1)

                normalized = (value - min_scale) / (max_scale - min_scale)
                y = plot_top + plot_height * (1 - normalized)
                points.append((x, y))

            # 渐变面积填充
            if len(points) >= 2:
                area_layer = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
                area_draw = ImageDraw.Draw(area_layer)

                polygon = points + [
                    (points[-1][0], plot_bottom),
                    (points[0][0], plot_bottom),
                ]
                mask = Image.new("L", (canvas_w, canvas_h), 0)
                mask_draw = ImageDraw.Draw(mask)
                mask_draw.polygon(polygon, fill=255)

                for y in range(plot_top, plot_bottom):
                    ratio = (y - plot_top) / max(1, plot_height)
                    alpha = int(fill_alpha_max * (1 - ratio))
                    area_draw.line(
                        [(plot_left, y), (plot_right, y)],
                        fill=(line_color[0], line_color[1], line_color[2], alpha),
                        width=1,
                    )

                area_layer.putalpha(mask)
                img = Image.alpha_composite(img.convert("RGBA"), area_layer).convert(
                    "RGB"
                )
                draw = ImageDraw.Draw(img)

            # 折线
            if len(points) >= 2:
                draw.line(points, fill=line_shadow, width=4 * scale, joint="curve")
                draw.line(points, fill=line_color, width=2 * scale, joint="curve")

            # 数据点
            dot_r = 3 * scale
            for idx, (x, y) in enumerate(points):
                outline = line_color
                fill = (255, 255, 255)
                width = max(1, scale)
                if idx == len(points) - 1:
                    outline = line_shadow
                    fill = line_color
                    width = 2 * scale
                    dot_r = 4 * scale
                draw.ellipse(
                    (x - dot_r, y - dot_r, x + dot_r, y + dot_r),
                    fill=fill,
                    outline=outline,
                    width=width,
                )
                dot_r = 3 * scale

            # X 轴日期标签
            label_step = max(1, len(dates) // 6)
            for i in range(0, len(dates), label_step):
                date_text = dates[i].strftime("%m/%d")
                x = points[i][0]
                w, _ = self._text_size(draw, date_text, label_font)
                draw.text(
                    (x - w / 2, plot_bottom + 8 * scale),
                    date_text,
                    fill=label_muted,
                    font=label_font,
                )

            # 保证最后一个日期一定绘制
            if dates:
                last_idx = len(dates) - 1
                if last_idx % label_step != 0:
                    date_text = dates[last_idx].strftime("%m/%d")
                    x = points[last_idx][0]
                    w, _ = self._text_size(draw, date_text, label_font)
                    draw.text(
                        (x - w / 2, plot_bottom + 8 * scale),
                        date_text,
                        fill=label_muted,
                        font=label_font,
                    )

            # 最新值标注
            last_x, last_y = points[-1]
            latest_text = self._format_million(values[-1])
            tw, th = self._text_size(draw, latest_text, value_font)
            pad_x = 6 * scale
            pad_y = 3 * scale
            box_x1 = min(last_x + 8 * scale, plot_right - tw - 2 * pad_x)
            box_y1 = max(plot_top + 2 * scale, last_y - th - 8 * scale)
            box_x2 = box_x1 + tw + 2 * pad_x
            box_y2 = box_y1 + th + 2 * pad_y

            draw.rounded_rectangle(
                (box_x1, box_y1, box_x2, box_y2),
                radius=6 * scale,
                fill=(255, 255, 255),
                outline=line_color,
                width=max(1, scale),
            )
            draw.text(
                (box_x1 + pad_x, box_y1 + pad_y),
                latest_text,
                fill=text_color,
                font=value_font,
            )

            # 输出为 Base64（使用每 76 字符换行，提高邮件兼容性）
            buffer = BytesIO()
            img_small = img.resize((self.width, self.height), Image.Resampling.LANCZOS)
            img_small.save(buffer, format="PNG", optimize=True)
            img_base64 = base64.encodebytes(buffer.getvalue()).decode("utf-8")

            logger.info(f"✅ {metal} 图表生成成功 (Pillow 增强版)")
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
