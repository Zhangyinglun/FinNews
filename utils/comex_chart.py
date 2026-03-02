"""COMEX 库存趋势图表生成器 (matplotlib 版)。"""

import base64
import json
import logging
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")  # 非交互式后端，必须在 pyplot import 之前
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

logger = logging.getLogger("utils.comex_chart")

# 输出规格：1120×600 @ dpi=144（Retina，邮件 width="560" 显示为 2× 清晰）
_OUTPUT_W = 1120
_OUTPUT_H = 600
_DPI = 144

# 配色方案（与原 Pillow 版完全一致）
_METAL = {
    "silver": {"line": "#7E8DA4", "shadow": "#5E6D82", "fill_alpha": 0.15},
    "gold":   {"line": "#B08A2D", "shadow": "#8B6A20", "fill_alpha": 0.18},
}
_C = {
    "grid":          "#DFE5EE",
    "text":          "#334155",
    "muted":         "#7889A0",
    "border":        "#D6DFEA",
    "bg":            "#F7FAFE",
    "ax_bg":         "#FAFCFE",
    "delta_up_bg":   "#F1F6FC",
    "delta_up_fg":   "#567190",
    "delta_dn_bg":   "#FAF2F2",
    "delta_dn_fg":   "#996060",
}


class ComexChartGenerator:
    """COMEX 库存趋势图表生成器 (matplotlib 版)。"""

    def __init__(self, history_file: Path):
        self.history_file = history_file

    @staticmethod
    def _format_million(value: float) -> str:
        """格式化百万盎司数值。"""
        if value >= 100:
            return f"{value:.0f}M"
        if value >= 10:
            return f"{value:.1f}M"
        return f"{value:.2f}M"

    def _extract_time_series(
        self, metal: str, value_type: str = "registered", days: int = 14
    ) -> Tuple[List[datetime], List[float]]:
        """从历史文件提取时间序列数据。"""
        if not self.history_file.exists():
            return [], []

        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                history = json.load(f)

            if isinstance(history, list):
                logger.warning("检测到旧版历史数据格式，无法解析")
                return [], []

            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            key = f"{metal}_{value_type}"
            records = sorted(history.get(key, []), key=lambda x: x["date"])

            dates: List[datetime] = []
            values: List[float] = []
            for record in records:
                dt_str = record["date"]
                try:
                    rec_date = (
                        datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S")
                        if "T" in dt_str
                        else datetime.strptime(dt_str, "%Y-%m-%d")
                    )
                except ValueError:
                    continue

                if start_date <= rec_date <= end_date:
                    dates.append(rec_date)
                    values.append(record["value"] / 1_000_000.0)

            return dates, values

        except Exception as e:
            logger.error(f"提取 COMEX 历史数据失败: {e}", exc_info=True)
            return [], []

    def generate_chart(
        self, metal: str, days: int = 14, value_type: str = "registered"
    ) -> Optional[str]:
        """
        生成趋势图表。

        Args:
            metal: "silver" 或 "gold"
            days: 展示天数（默认 14）
            value_type: 数据类型（默认 "registered"）

        Returns:
            base64 编码的 PNG 字符串（1120×600 Retina），失败返回 None
        """
        dates, values = self._extract_time_series(metal, value_type, days)
        if not dates or not values:
            logger.warning(f"无法生成 {metal} 图表: 数据不足")
            return None

        try:
            colors = _METAL[metal]
            fig, ax = plt.subplots(
                figsize=(_OUTPUT_W / _DPI, _OUTPUT_H / _DPI), dpi=_DPI
            )

            # ── 背景 ──────────────────────────────────────────────
            fig.set_facecolor(_C["bg"])
            ax.set_facecolor(_C["ax_bg"])

            # ── 数据 ──────────────────────────────────────────────
            x = np.array(mdates.date2num(dates))
            y = np.array(values)
            y_min = y.min() - (y.max() - y.min()) * 0.12

            # 区域填充（上深下浅）
            ax.fill_between(
                x, y, y_min,
                color=colors["line"],
                alpha=colors["fill_alpha"],
                zorder=2,
                linewidth=0,
            )

            # 折线：阴影层 + 主线层
            ax.plot(x, y, color=colors["shadow"], linewidth=2.8, alpha=0.30, zorder=3)
            ax.plot(
                x, y,
                color=colors["line"], linewidth=1.6,
                solid_capstyle="round", solid_joinstyle="round",
                zorder=4,
            )

            # 数据点：非末尾点（空心）
            if len(x) > 1:
                ax.scatter(
                    x[:-1], y[:-1],
                    s=22, color="white", edgecolors=colors["line"],
                    linewidths=1.3, zorder=5,
                )
            # 末尾点（实心）
            ax.scatter(
                [x[-1]], [y[-1]],
                s=40, color=colors["line"], edgecolors=colors["shadow"],
                linewidths=1.5, zorder=5,
            )

            # ── 最新值标注框 ──────────────────────────────────────
            ax.annotate(
                self._format_million(y[-1]),
                xy=(x[-1], y[-1]),
                xytext=(10, -14),
                textcoords="offset points",
                fontsize=7.5,
                color=_C["text"],
                bbox=dict(
                    boxstyle="round,pad=0.35",
                    facecolor="white",
                    edgecolor=colors["line"],
                    linewidth=1.0,
                ),
                zorder=6,
            )

            # ── 网格 ─────────────────────────────────────────────
            ax.yaxis.grid(
                True, linestyle="--", color=_C["grid"],
                alpha=0.85, linewidth=0.8
            )
            ax.set_axisbelow(True)
            ax.xaxis.grid(False)

            # ── 坐标轴样式 ────────────────────────────────────────
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
            ax.xaxis.set_major_locator(
                mdates.AutoDateLocator(minticks=4, maxticks=7)
            )
            ax.yaxis.set_major_formatter(
                ticker.FuncFormatter(lambda v, _: self._format_million(v))
            )
            ax.tick_params(
                axis="both", which="both",
                colors=_C["muted"], labelsize=7.5,
                length=0,
            )
            for spine in ("top", "right"):
                ax.spines[spine].set_visible(False)
            ax.spines["left"].set_color(_C["border"])
            ax.spines["bottom"].set_color(_C["border"])

            # ── 标题区 ───────────────────────────────────────────
            metal_en = "Silver" if metal == "silver" else "Gold"
            fig.suptitle(
                f"COMEX {metal_en} Registered Inventory ({days} Days)",
                fontsize=9.5, fontweight="bold", color=_C["text"],
                y=0.97, x=0.5, ha="center",
            )
            date_range = (
                f"{dates[0].strftime('%Y-%m-%d')} ~ {dates[-1].strftime('%Y-%m-%d')}"
            )
            ax.set_title(
                f"{value_type.capitalize()} | {date_range}",
                fontsize=7, color=_C["muted"], pad=2,
            )

            # ── Delta 标签（右上角）─────────────────────────────
            delta = float(y[-1] - y[0])
            delta_pct = (delta / float(y[0]) * 100.0) if y[0] else 0.0
            is_up = delta >= 0
            fig.text(
                0.97, 0.93,
                f"{delta_pct:+.2f}%",
                ha="right", va="top", fontsize=7.5,
                color=_C["delta_up_fg"] if is_up else _C["delta_dn_fg"],
                bbox=dict(
                    boxstyle="round,pad=0.35",
                    facecolor=_C["delta_up_bg"] if is_up else _C["delta_dn_bg"],
                    edgecolor=_C["border"],
                    linewidth=0.8,
                ),
            )

            # ── 输出 Base64 ──────────────────────────────────────
            plt.tight_layout(rect=[0, 0, 1, 0.90])
            buffer = BytesIO()
            fig.savefig(
                buffer, format="PNG", dpi=_DPI,
                facecolor=fig.get_facecolor(),
            )
            plt.close(fig)

            img_base64 = base64.encodebytes(buffer.getvalue()).decode("utf-8")
            logger.info(f"✅ {metal} 图表生成成功 (matplotlib 版, 1120×600)")
            return img_base64

        except Exception as e:
            logger.error(f"matplotlib 生成图表失败: {e}", exc_info=True)
            return None

    def generate_all_charts(self, days: int = 14) -> Dict[str, Optional[str]]:
        """生成所有品种的图表。"""
        return {
            "silver_chart": self.generate_chart("silver", days, "registered"),
            "gold_chart": self.generate_chart("gold", days, "registered"),
        }
