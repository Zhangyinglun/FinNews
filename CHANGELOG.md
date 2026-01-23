# Changelog

本文档记录 FinNews 项目的所有重要更改。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

---

## [stable-V1.0] - 2026-01-23

### 🎉 首个稳定版本发布

这是 FinNews 黄金白银市场智能分析系统的首个稳定版本。

### ✨ 核心功能

#### 数据采集
- **多数据源聚合**：整合 5+ 数据源
  - Tavily API - 新闻搜索与地缘政治信息
  - YFinance - 实时价格数据（VIX、美元指数、国债、黄金/白银期货）
  - RSS 订阅 - mining.com, FXStreet, Investing.com, ZeroHedge
  - FRED API - 9 个核心经济指标（CPI、PCE、NFP、失业率、联邦基金利率等）
  - COMEX 库存监控 - 白银/黄金 Registered 库存数据

#### 智能分析
- **规则引擎**：VIX 预警、宏观倾向分析、市场情绪评分
- **COMEX 预警**：四级库存预警（安全/黄色/红色/系统风险）
- **多窗口数据**：Flash(12小时) / Cycle(7天) / Trend(30天)
- **LLM 驱动**：Gemini 3 Pro 生成专业市场分析报告

#### 邮件系统
- **响应式 HTML 邮件**：手机端完美适配
- **模块化设计**：
  - 📈 市场行情（价格表格）
  - 📅 经济指标（独立板块，无数据时隐藏）
  - 🏦 COMEX 库存监控
  - 📰 重点新闻 / 其他新闻
  - 🔍 AI 市场分析
- **Gmail SMTP 发送**：支持 App Password 认证

### 🐛 Bug 修复

#### COMEX 数据丢失问题 [#1525d72]
- **问题**：当 COMEX 数据超过 12 小时窗口时，黄金数据丢失，只显示白银数据
- **根因**：`BaseScraper._filter_recent_records()` 的 fallback 逻辑只返回 1 条最新记录
- **修复**：修改 fallback 逻辑，返回所有具有最新 timestamp 的记录
- **影响**：白银和黄金数据现在都能正确显示

#### COMEX 标题格式优化 [#861e689]
- **问题**：标题右侧显示总体状态（如"🟢 正常"），与表格中每行状态重复
- **修复**：移除标题右侧的冗余状态显示
- **效果**：界面更简洁，可读性提升

### 🔧 优化改进

#### 数据源配置优化 [#24c0985]
- **RSS 源调整**：
  - ❌ 删除 `kitco_gold` (404 失效)
  - ❌ 删除 `oilprice` (与黄金白银弱相关)
  - ✅ 新增 `mining.com` (矿业专业新闻)
  - ✅ 保留 FXStreet、Investing.com、ZeroHedge

- **FRED 指标精简**（14 → 9 个核心指标）：
  - ❌ 删除 `treasury_10y` (与 YFinance 的 ^TNX 重复)
  - ❌ 删除 `dxy` (与 YFinance 的 DX-Y.NYB 重复)
  - ❌ 删除 `gdp` (季度发布，滞后性强)
  - ❌ 删除 `m1`, `m2` (货币供应量，相关性弱)
  - ✅ 保留核心指标：
    - 通胀 (4个): CPI, Core CPI, PCE, Core PCE
    - 就业 (2个): NFP, Unemployment
    - 利率 (3个): Fed Funds, Treasury 2Y, Real Rate

#### 邮件模板重构 [#24c0985]
- **经济指标独立板块**：
  - 从市场行情内移出，成为独立板块
  - 无数据时完全隐藏，不再显示警告消息
  - 与 COMEX、重点新闻等板块同级

### 📚 文档

- ✅ 添加数据源优化实施计划 (`docs/plans/2026-01-23-datasource-optimization.md`)
- ✅ 添加移动端邮件优化设计文档 (`docs/plans/2026-01-23-mobile-email-optimization-design.md`)
- ✅ 添加邮件字体优化设计文档 (`docs/plans/2026-01-22-email-font-size.md`)

### 🔧 技术栈

- **语言**: Python 3.10+
- **数据模型**: Pydantic
- **LLM**: Google Gemini 3 Pro (via OpenRouter)
- **邮件**: Gmail SMTP
- **数据源**: Tavily, YFinance, RSS, FRED, COMEX

### 📦 部署

```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入 API 密钥

# 运行
python main.py
```

### ⚠️ 已知问题

- COMEX 数据依赖 CME 官网 Excel 文件，偶尔可能无法访问
- 部分新闻源（WSJ、Investing.com）可能返回 403/401 错误
- LLM 生成内容质量依赖 Gemini 3 Pro 服务可用性

### 🙏 致谢

感谢所有数据源提供商：
- Tavily API
- Federal Reserve Economic Data (FRED)
- CME Group (COMEX)
- Yahoo Finance
- 各新闻源 (mining.com, FXStreet, Investing.com, ZeroHedge)

---

## [Unreleased]

### 计划中的功能
- [ ] 定时任务调度（APScheduler）
- [ ] Web Dashboard 界面
- [ ] 历史数据回测
- [ ] 更多技术指标（RSI, MACD, Bollinger Bands）
- [ ] Telegram Bot 通知
- [ ] Docker 容器化部署

---

[stable-V1.0]: https://github.com/Zhangyinglun/FinNews/releases/tag/stable-V1.0
