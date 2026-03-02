# 移除 Header 价格速览行中的黄金白银标签

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 去掉 digest 邮件 Header 中与下方表格重复的价格速览行（黄金、白银、VIX 全部移除）

**Architecture:** 在 `digest_controller.py` 的 `render_email_html` 方法中，将价格速览行设为空字符串

**Tech Stack:** Python

---

### Task 1: 移除黄金白银价格速览

**Files:**
- Modify: `utils/digest_controller.py:570-586`

**Step 1: 修改代码**

将原有的 Header 价格速览行生成逻辑：

```python
        # Header 价格速览行
        summary_parts = []
        if signal.gold_price is not None and signal.gold_change_percent is not None:
            gc = "#34c759" if signal.gold_change_percent >= 0 else "#ff3b30"
            summary_parts.append(
                f'黄金 ${signal.gold_price:.2f} '
                f'<span style="color: {gc}; font-weight: 600;">{signal.gold_change_percent:+.2f}%</span>'
            )
        if signal.silver_price is not None and signal.silver_change_percent is not None:
            sc = "#34c759" if signal.silver_change_percent >= 0 else "#ff3b30"
            summary_parts.append(
                f'白银 ${signal.silver_price:.2f} '
                f'<span style="color: {sc}; font-weight: 600;">{signal.silver_change_percent:+.2f}%</span>'
            )
        if signal.vix_value is not None:
            summary_parts.append(f"VIX {signal.vix_value:.1f}")
        price_summary_line = "&nbsp;&nbsp;&middot;&nbsp;&nbsp;".join(summary_parts)
```

替换为：

```python
        # Header 价格速览行已移除（信息在下方表格展示）
        price_summary_line = ""
```

**Step 2: 运行测试**

Run: `python3 -m pytest tests/utils/test_digest_to_file.py -v --tb=short`
Expected: 2 passed

**Step 3: 提交**

```bash
git add utils/digest_controller.py
git commit -m "fix: 移除 Header 价格速览行中与表格重复的黄金白银标签"
```
