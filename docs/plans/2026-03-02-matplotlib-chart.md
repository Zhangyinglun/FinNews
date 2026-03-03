# COMEX 图表迁移至 matplotlib 实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 用 matplotlib 重写 `utils/comex_chart.py`，输出从 560×300 提升到 1120×600 Retina 分辨率，保持对外接口完全不变。

**Architecture:** 完全重写 `ComexChartGenerator.generate_chart()` 方法，用 matplotlib/numpy 替代全部 Pillow 绘图逻辑。保留 `_extract_time_series()`（纯 JSON 数据处理）和 `_format_million()`（数字格式化）不变。对外接口 `generate_chart()` → `Optional[str]`（Base64 PNG）和 `generate_all_charts()` → `Dict` 完全不变。

**Tech Stack:** matplotlib>=3.8.0（新增），numpy==1.26.4（已有），Pillow 保留但不再使用。

---

## Task 1: 添加 matplotlib 依赖

**Files:**
- Modify: `requirements.txt:24`

**Step 1: 在 requirements.txt Data Processing 区块加入 matplotlib**

在 `Pillow>=10.0.0` 行后加一行：

```
matplotlib>=3.8.0             # 图表绘制 (COMEX趋势图)
```

**Step 2: 验证依赖安装**

```bash
pip install matplotlib>=3.8.0
python -c "import matplotlib; print(matplotlib.__version__)"
```

Expected: 打印版本号（如 `3.10.0`），无报错。

**Step 3: Commit**

```bash
git add requirements.txt
git commit -m "feat: 添加 matplotlib 依赖用于 COMEX 图表重写"
```

---

## Task 2: 新增分辨率验证测试（先写 Failing Test）

**Files:**
- Modify: `tests/utils/test_comex_chart.py`

**Step 1: 在测试文件末尾追加新测试**

```python
def test_chart_output_resolution(history_file):
    """图表输出为 Retina 分辨率 1120×600"""
    import base64
    from PIL import Image
    from io import BytesIO

    generator = ComexChartGenerator(history_file)
    chart_base64 = generator.generate_chart("silver", days=14)

    assert chart_base64 is not None
    img_bytes = base64.decodebytes(chart_base64.encode("utf-8"))
    img = Image.open(BytesIO(img_bytes))
    assert img.size == (1120, 600), f"期望 1120×600，实际 {img.size}"
```

**Step 2: 运行测试，确认它 FAIL（当前 Pillow 版本输出 560×300）**

```bash
cd /mnt/d/Projects/FinNews
python -m pytest tests/utils/test_comex_chart.py::test_chart_output_resolution -v
```

Expected: **FAIL**，错误信息类似 `期望 1120×600，实际 (560, 300)`

**Step 3: Commit 失败的测试**

```bash
git add tests/utils/test_comex_chart.py
git commit -m "test: 新增 COMEX 图表 Retina 分辨率验证测试（预期 1120×600）"
```

---

## Task 3: 用 matplotlib 重写 `comex_chart.py`

**Files:**
- Modify: `utils/comex_chart.py`（完整替换）

**Step 1: 完整替换 `utils/comex_chart.py` 内容**

```python
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
    "grid":    "#DFE5EE",
    "text":    "#334155",
    "muted":   "#7889A0",
    "border":  "#D6DFEA",
    "bg":      "#F7FAFE",   # 原渐变 top/bot 中间值
    "ax_bg":   "#FAFCFE",
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
                bbox_inches="tight",
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
```

**Step 2: 运行所有图表测试**

```bash
cd /mnt/d/Projects/FinNews
python -m pytest tests/utils/test_comex_chart.py -v
```

Expected: **所有测试 PASS**，包括新的分辨率测试。

**Step 3: 运行完整测试套件确认无回归**

```bash
python -m pytest tests/ --tb=short -q
```

Expected: **78+ 个测试全部通过**（+1 新增 = 79+）

**Step 4: Commit**

```bash
git add utils/comex_chart.py
git commit -m "feat: 用 matplotlib 重写 COMEX 图表，输出提升至 1120×600 Retina 分辨率"
```

---

## Task 4: 手动视觉验证

**Files:**
- Read: `tests/debug_chart.py`（运行调试脚本）

**Step 1: 运行调试脚本查看实际生成图表**

```bash
cd /mnt/d/Projects/FinNews
python tests/debug_chart.py
```

Expected: 在 `outputs/` 生成预览图片文件，查看视觉效果。

如果 `debug_chart.py` 不支持直接查看，可临时运行：

```python
# 临时验证脚本（不提交）
import base64
from pathlib import Path
from utils.comex_chart import ComexChartGenerator

gen = ComexChartGenerator(Path("outputs/comex_history.json"))
result = gen.generate_chart("silver", days=14)
if result:
    img_bytes = base64.decodebytes(result.encode())
    Path("outputs/test_chart_silver.png").write_bytes(img_bytes)
    print("图表已保存到 outputs/test_chart_silver.png")
```

**Step 2: 确认视觉效果符合预期**

检查清单：
- [ ] 折线平滑、无锯齿
- [ ] 区域填充颜色正确（白银灰色 / 黄金金色）
- [ ] 右上角 Delta 标签显示正确颜色（上涨蓝/下跌红）
- [ ] 最新值标注框显示在折线末尾
- [ ] 日期标签正常显示
- [ ] 背景为浅蓝白色

---

## 验收标准

1. `python -m pytest tests/utils/test_comex_chart.py -v` → 全部 PASS（含 `test_chart_output_resolution`）
2. `python -m pytest tests/ -q` → 无新增失败
3. `generate_chart("silver", 14)` 返回可解码为 1120×600 PNG 的 Base64 字符串
4. `generate_all_charts()` 返回包含 `silver_chart` 和 `gold_chart` 的字典
5. 邮件模板 `digest_controller.py` 无需修改（接口兼容）
