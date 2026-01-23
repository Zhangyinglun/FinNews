# 邮件模板手机端优化设计方案

创建日期: 2026-01-23
目标: 优化邮件HTML模板,提升手机端阅读体验
适用客户端: iOS Mail, Gmail App (iOS/Android), Outlook Mobile

---

## 需求概述

用户需求:
1. 全屏自适应布局 - 移除固定600px宽度限制,充分利用手机屏幕
2. 字体放大 - 中等放大字体,标题20-24px,正文16-18px
3. 修复经济指标缺失 - CPI/PCE/NFP缺失时显示警告消息

目标环境:
- 主要目标: iOS/Android原生邮件客户端
- 次要目标: 桌面邮件客户端最大宽度600px

---

## 问题分析

### 问题1: 固定宽度布局浪费屏幕空间

当前实现:
```html
<table width="600" cellpadding="0" cellspacing="0">
```

问题:
- 手机端宽度不足时出现横向滚动
- 固定宽度 + 32px内边距浪费空间

---

### 问题2: 字体偏小,手机端阅读吃力

核心问题:
- 标题和正文层级不够清晰
- 关键数据(VIX/价格)不够突出

---

### 问题3: 经济指标区块有时完全消失

当前逻辑:
```python
if econ_items:
    econ_html = "..."
else:
    econ_html = ""
```

根因:
- 经济指标字段为Optional
- 无数据时整个区块被隐藏

影响:
- 用户无法判断系统是否获取过数据

---

## 解决方案

### 方案1: 响应式布局改造

主容器宽度调整:
```html
<table width="100%" cellpadding="0" cellspacing="0" style="max-width: 600px;">
```

内边距缩减规则:
- 外层容器: 20px -> 8px
- Header: 24px 32px -> 20px 16px
- 内容区块: 0 32px 24px 32px -> 0 16px 20px 16px
- 小卡片: 12px 16px -> 10px 12px
- Footer: 20px 32px -> 16px 16px

---

### 方案2: 字体大小优化

字体规格调整:
- 邮件主标题: 22px -> 24px
- VIX数值: 18px -> 20px
- 区块标题: 17px -> 20px
- 表格基准字号: 16px -> 18px
- 新闻标题: 16px -> 19px
- 新闻来源: 14px -> 16px
- 新闻摘要: 15px -> 17px
- 分析标题: 16px -> 18px
- 分析内容: 15px -> 17px
- 经济指标: 15px -> 16px
- 经济指标标签: 13px -> 14px

---

### 方案3: 经济指标缺失修复

改造逻辑:
```python
if econ_items:
    econ_content = " | ".join(econ_items)
else:
    econ_content = '<span style="color: #ff9800; font-weight: 500;">⚠️ 经济指标数据暂时不可用</span>'

econ_html = (
    '<div style="padding: 10px 12px; font-size: 16px; color: #666; background-color: #fafafa; border-top: 1px solid #e9ecef;">'
    '<span style="color: #999; font-size: 14px;">📅 每日/定期发布数据</span><br/>'
    + econ_content
    + "</div>"
)
```

预期效果:
- 有数据时正常显示CPI/PCE/NFP
- 无数据时显示警告提示

---

## 实施清单

需要修改的文件:
- utils/digest_controller.py

修改区域:
- EMAIL_TEMPLATE (布局/字体/内边距)
- render_email_html (经济指标逻辑)
- _render_news_list (新闻字体)
- _render_analysis (分析字体)
- _render_comex_section (COMEX字体/内边距)

---

## 测试计划

1. 离线测试:
```bash
python test_digest_to_file.py
```

2. 集成测试:
```bash
python main.py
```

3. 经济指标缺失场景:
- 模拟cycle字段为None
- 确认警告消息显示

---

## 兼容性说明

- Gmail App不支持@media,使用内联样式
- max-width在主流移动端支持良好
- width=100%提供降级支持

---

设计完成,待实施。
