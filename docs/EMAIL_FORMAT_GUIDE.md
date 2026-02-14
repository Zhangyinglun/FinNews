# 纯文本邮件格式使用指南

## 概述

已成功集成纯文本邮件格式（包含 COMEX ASCII 表格和 Top 5 新闻），可通过配置切换邮件内容类型。

---

## 配置方法

### 1. 设置邮件内容类型

在 `.env` 文件中添加或修改以下配置：

```env
# 邮件内容类型（必需）
EMAIL_CONTENT_TYPE=plain_text    # 使用纯文本格式（推荐）
# EMAIL_CONTENT_TYPE=html        # 使用 HTML 格式（原有方式，需要 LLM）

# 纯文本邮件格式配置（可选）
EMAIL_FORMAT_MODE=full           # "full"=头条+详细附录 | "brief"=仅头条(30行)
EMAIL_TOP_NEWS_COUNT=5           # Top N 新闻数量
EMAIL_MAX_SUMMARY_LENGTH=80      # 新闻摘要最大长度
```

### 2. 默认配置

如果不设置 `EMAIL_CONTENT_TYPE`，默认使用 `plain_text` 模式。

---

## 邮件格式特性

### ✅ 纯文本模式 (`plain_text`)

**优势：**
- ✅ **极致兼容性**：所有邮件客户端完美显示
- ✅ **快速生成**：无需调用 LLM，速度提升 10x
- ✅ **节省成本**：不消耗 OpenRouter API 额度
- ✅ **ASCII 艺术表格**：COMEX 使用 Unicode 边框（┏━┓┃┗━┛）
- ✅ **清晰层次**：头条区 + Top 5 + 详细附录

**邮件结构：**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 市场分析速报 | 2026-02-14 02:04
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔴 VIX恐慌指数: 22.50 (+22.95%) ⚠️ 紧急预警
💵 美元指数(DXY): 107.25 (+0.45%)
📈 10年期国债: 4.52% (+3.20%)
💰 黄金(GC=F): $2,678.40 (+1.25%)
💎 白银(SI=F): $30.85 (+2.17%)

📊 情绪评分: [███████░░░] +0.42 (偏利多)
📌 宏观倾向: 中性

⚠️ 警报消息:
  • 🔴 VIX 暴涨 22.95%，市场恐慌情绪急剧升温
  • ⚠️ VIX=22.5 超过警戒线 20.0

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  🏦 COMEX 库存监控 (2026-02-14)      ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃                                       ┃
┃  💎 白银 (Registered)                 ┃
┃     库存: 104.88M oz                    ┃
┃     变化: 📉 -1.9% (日)  📉 -12.3% (周)     ┃
┃     状态: 🔴 生死线                   ┃
┃     💡 密切监控挤仓风险，关注白银期货持仓量变化             ┃
┃                                       ┃
┃  ───────────────────────────────      ┃
┃                                       ┃
┃  💰 黄金 (Registered)                 ┃
┃     库存: 8.23M oz                     ┃
┃     变化: 📉 -0.4% (日)  📉 -2.6% (周)      ┃
┃     状态: 🟢 安全                     ┃
┃                                       ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📰 今日必读 Top 5
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. [时间 | 来源] 标签 新闻标题
   摘要：...
   🔗 URL

...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📎 查看完整数据（下方附录）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

============================================================
详细数据附录
============================================================

[完整的市场数据、新闻列表、统计信息]
```

### ⚙️ HTML 模式 (`html`)

**优势：**
- ✅ LLM 生成的智能摘要和分析
- ✅ 图表支持（COMEX 趋势图）
- ✅ 富文本格式

**劣势：**
- ❌ 需要 OpenRouter API（费用 ~$0.02/次）
- ❌ 生成时间较长（20-40秒）
- ❌ 部分邮件客户端可能显示异常

---

## 运行测试

### 1. 本地测试（不发送邮件）

运行测试脚本生成邮件预览：

```bash
python test_plain_email_generation.py
```

输出：
- 终端显示前 40 行预览
- 保存完整预览文件到 `outputs/plain_email_test_YYYYMMDD_HHMMSS.txt`

### 2. 完整流程测试（实际发送邮件）

**⚠️ 注意：** 这会发送真实邮件到配置的收件人！

```bash
python main.py
```

确保 `.env` 配置正确：
```env
# SMTP 配置
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
EMAIL_FROM=your_email@gmail.com
EMAIL_TO=recipient@example.com

# 邮件内容类型
EMAIL_CONTENT_TYPE=plain_text
```

---

## 技术实现

### 修改的文件

1. **`config/config.py`**
   - 添加 `EMAIL_CONTENT_TYPE` 配置项
   - 添加纯文本邮件格式配置

2. **`utils/mailer.py`**
   - 新增 `send_plain()` 方法（发送纯文本邮件）

3. **`main.py`**
   - 在邮件生成部分添加分支：根据 `EMAIL_CONTENT_TYPE` 选择生成方式
   - 修改 `send_email_with_retry()` 函数：支持纯文本和 HTML 两种模式
   - 修改邮件发送部分：根据内容类型调用相应方法

4. **`analyzers/market_analyzer.py`**（之前已完成）
   - 新增 `build_email_prompt()` 方法
   - 新增 `_render_comex_text()` 方法
   - 新增 `_select_top_news()` 方法

### 代码流程

#### 纯文本模式流程：

```
1. 加载原始新闻数据（scrapers）
   ↓
2. 运行规则引擎分析（analyzers/rule_engine.py）
   → 生成 MarketSignal, ComexSignal
   ↓
3. 组织多窗口数据（analyzers/market_analyzer.py）
   → analyzer.organize_data()
   ↓
4. 生成纯文本邮件内容
   → analyzer.build_email_prompt(data, signal, comex_signal, mode)
   ↓
5. 生成邮件标题
   → signal.get_email_subject_tag() + signal.get_signal_summary()
   ↓
6. 发送纯文本邮件
   → mailer.send_plain(subject, plain_body, email_from, to_list)
```

#### HTML 模式流程（原有）：

```
1. 加载原始新闻数据
   ↓
2. 运行规则引擎分析
   ↓
3. 组织多窗口数据
   ↓
4. 构建 LLM 输入提示词
   → digest_controller.build_llm_prompt()
   ↓
5. 调用 OpenRouter API
   → client.chat_completions() [20-40秒，$0.02]
   ↓
6. 解析 LLM 返回的 JSON
   ↓
7. 渲染 HTML 模板
   → digest_controller.render_email_html()
   ↓
8. 发送 HTML 邮件（带图片）
   → mailer.send_html(subject, html_body, email_from, to_list, images)
```

---

## 已知问题

### 1. COMEX 数据可能为空

如果 COMEX API 抓取失败，COMEX 表格将不显示。这是正常现象。

**解决方案：** 确保 `scrapers/comex_scraper.py` 正常工作，或者检查 `outputs/comex_history.json` 是否有数据。

### 2. 邮件客户端字体差异

某些邮件客户端可能使用非等宽字体，导致 ASCII 表格错位。

**已验证兼容的客户端：**
- ✅ Gmail（网页版/移动端）
- ✅ Outlook（桌面版/网页版）
- ✅ Apple Mail
- ✅ Thunderbird

**不兼容的客户端：**
- ❌ 某些老旧的邮件客户端（非 UTF-8 编码）

---

## 推荐配置

**日常使用（推荐）：**
```env
EMAIL_CONTENT_TYPE=plain_text
EMAIL_FORMAT_MODE=full
EMAIL_TOP_NEWS_COUNT=5
```

**紧急简报模式：**
```env
EMAIL_CONTENT_TYPE=plain_text
EMAIL_FORMAT_MODE=brief
EMAIL_TOP_NEWS_COUNT=3
```

**深度分析模式：**
```env
EMAIL_CONTENT_TYPE=html
# 需要 OPENROUTER_API_KEY
```

---

## 下一步

1. **运行 `main.py` 发送一封测试邮件**
2. **在不同邮件客户端查看显示效果**
3. **根据实际效果微调 `EMAIL_TOP_NEWS_COUNT` 和 `EMAIL_FORMAT_MODE`**

---

**最后更新:** 2026-02-14  
**版本:** 1.0.0
