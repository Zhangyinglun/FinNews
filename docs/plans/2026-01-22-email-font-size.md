# 邮件模板字号提升计划

## 需求分析
- 目标：将项目输出的邮件文字整体调大两号，提升可读性。
- 范围：HTML 邮件模板（`utils/digest_controller.py`）及离线导出模板（`test_digest_to_file.py`）。
- 约束：保持现有结构与颜色，仅调整字号；不引入新依赖。

## 任务拆解（每步 2-5 分钟）
1. 盘点邮件模板字号分布并确定统一提升 +2px 的规则。
2. 修改 `utils/digest_controller.py` 中的 HTML 模板与内联样式字号。
3. 同步调整 `test_digest_to_file.py` 的导出 HTML 样式字号。
4. 运行 `python test_digest_to_file.py` 生成 HTML 并自检排版。

## 详细实施方案

### 1) 统一提升规则
- 所有 `font-size` 数值整体 +2px。
- 保持相对层级（标题仍大于正文、脚注仍最小）。

### 2) 更新 `utils/digest_controller.py`
目标：将模板与新闻/分析渲染的内联样式字号统一 +2px。

#### 需要修改的代码片段（完整替换）

```python
# 1) 经济数据小字与提示
"<div style=\"padding: 12px 16px; font-size: 15px; color: #666; background-color: #fafafa; border-top: 1px solid #e9ecef;\">"
"<span style=\"color: #999; font-size: 13px;\">📅 每日/定期发布数据</span><br/>"
```

```python
# 2) 新闻列表（标题/来源/摘要）
<div style="font-size: 16px; font-weight: 600; color: #1a1a2e; margin-bottom: 4px;">{title}</div>
<div style="font-size: 14px; color: #999; margin-bottom: 6px;">来源: {source}</div>
{f'<div style="font-size: 15px; color: #555; line-height: 1.6;">{summary}</div>' if summary else ""}
```

```python
# 3) 分析段落（标题/内容）
<div style="font-size: 16px; font-weight: 600; color: #1a1a2e; margin-bottom: 4px;">{title}</div>
<div style="font-size: 15px; color: #555; line-height: 1.6;">{content}</div>
```

```python
# 4) COMEX 区块标题与表格
<span style="font-size: 17px; font-weight: 600; color: #1a1a2e;">🏦 COMEX库存监控{report_date_str}</span>
<span style="float: right; font-size: 16px;">{emoji} {status_text}</span>
<table width="100%" cellpadding="0" cellspacing="0" style="font-size: 16px;">
```

```python
# 5) COMEX 警报与建议
<div style="padding: 12px 16px; font-size: 15px; background-color: #fafafa; border-top: 1px solid #e9ecef;">
<div style="padding: 12px 16px; font-size: 15px; color: #856404; background-color: #fff3cd; border-top: 1px solid #e9ecef;">
```

```python
# 6) 主模板 Header 与 VIX
<h1 style="margin: 0; color: #ffffff; font-size: 22px; font-weight: 600;">{subject}</h1>
<p style="margin: 8px 0 0 0; color: rgba(255,255,255,0.7); font-size: 15px;">生成时间: {datetime}</p>
<div style="width: 44px; height: 44px; border-radius: 50%; background-color: {vix_bg_color}; text-align: center; line-height: 44px; font-size: 24px;">{vix_emoji}</div>
<div style="font-size: 18px; font-weight: 600; color: #1a1a2e;">VIX: {vix_value} <span style="font-weight: 400; color: #666;">({vix_change})</span></div>
<div style="font-size: 15px; color: #666; margin-top: 4px;">市场状态: {vix_status} | 宏观倾向: {macro_bias}</div>
```

```python
# 7) Section 标题与表格基准字号
<span style="font-size: 17px; font-weight: 600; color: #1a1a2e;">📈 市场行情</span>
<table width="100%" cellpadding="0" cellspacing="0" style="font-size: 16px;">
<span style="font-size: 17px; font-weight: 600; color: #1a1a2e;">📰 重点新闻</span>
<span style="font-size: 17px; font-weight: 600; color: #1a1a2e;">📋 其他新闻</span>
<span style="font-size: 17px; font-weight: 600; color: #1a1a2e;">🔍 市场分析</span>
```

```python
# 8) Footer 字号
<p style="margin: 0; font-size: 14px; color: #999; text-align: center;">FinNews - 黄金白银市场智能分析系统</p>
<p style="margin: 6px 0 0 0; font-size: 13px; color: #bbb; text-align: center;">本报告由AI自动生成，仅供参考，不构成投资建议</p>
```

### 3) 更新 `test_digest_to_file.py`
目标：离线导出 HTML 的样式字号统一 +2px。

#### 需要修改的代码片段（完整替换）
```python
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    line-height: 1.6;
    font-size: 16px;
    max-width: 800px;
    margin: 0 auto;
    padding: 20px;
    background-color: #f5f5f5;
}

.metadata {
    color: #7f8c8d;
    font-size: 1.1em;
    margin-bottom: 20px;
}
```

### 4) 验证步骤
1. 运行 `python test_digest_to_file.py`，确认生成的 HTML 文字整体放大两号。
2. 如需实际邮件验证，运行 `python main.py` 并检查收到的邮件排版。

## 执行选项
1. 我直接按计划逐步修改并提交结果。
2. 使用 subagent 执行第 2-4 步，我进行最终检查。
3. 你先确认字号调整范围或指定仅调整某些区块后再执行。
