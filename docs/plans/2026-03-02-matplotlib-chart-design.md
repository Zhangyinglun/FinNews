# 设计文档：COMEX 图表从 Pillow 迁移到 matplotlib

**日期**: 2026-03-02
**状态**: 已确认，待实现

---

## 背景与动机

当前 `utils/comex_chart.py` 使用 Pillow (PIL) 手动绘制折线图，存在以下局限：

- 所有视觉效果（渐变、虚线、抗锯齿）需要像素级手动实现，代码量大且脆弱
- 超采样抗锯齿（2× scale 后缩小）是变通方案，线条仍有锯齿感
- 分辨率锁定在 560×300px，不支持 Retina/HiDPI 邮件客户端

目标：用 matplotlib 重写图表生成逻辑，提升输出质量（Retina 分辨率 + 真实抗锯齿），同时保持对外接口完全不变。

---

## 选型决策

**选择方案 A：纯 matplotlib 重写**

| 对比维度 | Pillow | matplotlib |
|---------|--------|-----------|
| 抗锯齿 | 2× 超采样变通 | 原生 FreeType 渲染 |
| 输出分辨率 | 560×300 px | 1120×600 px (dpi=144) |
| 渐变填充 | 像素 for 循环 | numpy 数组 + imshow |
| 折线 | 两次叠加模拟阴影 | 真实 alpha 混合 |
| 代码量 | ~513 行 | 预计 ~220 行 |
| 新增依赖 | 无 | matplotlib + numpy |

---

## 设计要求

### 对外接口（不变）

```python
class ComexChartGenerator:
    def __init__(self, history_file: Path): ...
    def generate_chart(self, metal: str, days: int = 14, value_type: str = "registered") -> Optional[str]: ...
    def generate_all_charts(self, days: int = 14) -> Dict[str, Optional[str]]: ...
```

- 输入：JSON 历史数据文件路径
- 输出：Base64 编码 PNG 字符串（可直接用于邮件 MIME 嵌入）

### 输出规格

- 尺寸：**1120×600 px**（2× Retina，邮件 HTML 用 `width="560"` 显示为正常大小）
- DPI：144
- 格式：PNG，Base64 编码（保持 `base64.encodebytes` 76字符换行，邮件兼容）

---

## 配色方案

与现有设计完全一致：

```python
PALETTE = {
    "silver": {"line": "#7E8DA4", "shadow": "#5E6D82"},
    "gold":   {"line": "#B08A2D", "shadow": "#8B6A20"},
    "grid":   "#DFE5EE",
    "text":   "#334155",
    "muted":  "#7889A0",
    "border": "#D6DFEA",
    "bg_top": "#FBFDFF",
    "bg_bot": "#F3F8FD",
}
```

---

## 视觉元素实现映射

| 元素 | Pillow 实现 | matplotlib 实现 |
|------|-----------|----------------|
| 背景渐变 | `_draw_vertical_gradient()` 逐行 | `ax.imshow(gradient_array, aspect='auto', extent=...)` |
| 折线阴影 | 两次 `draw.line()` 叠加 | `ax.plot(lw=2.5, color=shadow, alpha=0.4)` |
| 折线主线 | `draw.line(width=2)` | `ax.plot(lw=1.5, solid_capstyle='round')` |
| 区域填充 | 像素 for 循环 + mask | `ax.fill_between(alpha=0.15)` |
| 数据点 | `draw.ellipse()` | `ax.scatter(s=28, zorder=5)` |
| 最新值标注 | `draw.rounded_rectangle()` + text | `ax.annotate(bbox=dict(boxstyle='round'))` |
| Delta 标签 | 手绘圆角框 | `fig.text()` + `FancyBboxPatch` |
| 虚线网格 | `_draw_dashed_line()` | `ax.yaxis.grid(linestyle='--', alpha=0.6)` |
| 标题/副标题 | `draw.text()` | `fig.suptitle()` + `ax.set_title()` |
| X 轴日期 | 手动计算间距 + `draw.text()` | `ax.set_xticks()` + `ax.set_xticklabels()` |
| Y 轴标签 | 手动格式化 + `draw.text()` | `ax.yaxis.set_major_formatter(FuncFormatter(...))` |

---

## 保留不变的代码

- `_extract_time_series()` — 纯数据处理，无 Pillow 依赖
- `_format_million()` — 数字格式化工具
- `generate_all_charts()` — 调用逻辑不变

## 删除的代码

- `_try_load_font()` — matplotlib 有内置字体系统
- `_draw_vertical_gradient()` — numpy 替代
- `_draw_dashed_line()` — matplotlib 原生支持
- `_text_size()` — Pillow 版本兼容工具
- `_get_y_pos()` / `_get_x_pos()` — matplotlib 自动处理坐标轴
- `import PIL` 相关所有 import

---

## 依赖变更

**`requirements.txt` 新增：**
```
matplotlib>=3.8.0
numpy>=1.24.0
```

**保留 Pillow（项目其他地方可能仍需要）**，但 `comex_chart.py` 不再 import。

---

## 邮件模板

`utils/digest_controller.py` 中的 img 标签不需要修改：
```html
<img src="cid:silver_chart" width="560" ... />
```
1120×600 图片在 `width="560"` 约束下，Retina 屏幕自动显示为 2× 清晰度。

---

## 测试策略

1. **现有测试直接复用**：`tests/utils/test_comex_chart.py` 的接口测试无需改动
2. **新增分辨率验证测试**：解码 Base64 → PIL.Image，验证 `image.size == (1120, 600)`
3. **手动验证**：运行 `tests/debug_chart.py` 对比新旧图表视觉效果

---

## 修改文件清单

| 文件 | 变更类型 |
|------|---------|
| `utils/comex_chart.py` | 完全重写（保留接口） |
| `requirements.txt` | 新增 matplotlib>=3.8.0, numpy>=1.24.0 |
| `tests/utils/test_comex_chart.py` | 新增分辨率验证测试用例 |
