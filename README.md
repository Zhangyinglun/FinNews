# FinNews - 黄金白银价格趋势数据抓取系统

[English](#english) | [中文](#chinese)

---

<a name="english"></a>
## English Documentation

### Overview

FinNews is a production-ready financial news aggregation pipeline designed to analyze gold (XAU) and silver (XAG) price trends. It automatically scrapes news from 5+ sources every 6 hours, filters data using keyword rules, deduplicates content, and outputs structured JSON and Markdown reports for AI agent analysis.

### Features

- **Multi-Source Data Aggregation**: Tavily API, yfinance, RSS feeds (Kitco, FXStreet), FRED API, Alpha Vantage
- **Intelligent Filtering**: Whitelist/blacklist keyword system for relevant news
- **Deduplication**: MD5-based content hashing with 24-hour time window
- **LLM-Friendly Output**: Structured Markdown reports optimized for AI analysis
- **Scheduled Execution**: APScheduler-based automation (default: every 6 hours)
- **Sentiment Tagging**: Automatic #Bullish/#Bearish/#Neutral classification

### Quick Start

#### 1. Installation

```bash
# Clone the repository
git clone <repository-url>
cd FinNews

# Install dependencies (Python 3.10+ required)
pip install -r requirements.txt
```

#### 2. API Key Setup

Copy the example environment file and configure your API keys:

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```env
# Required API Keys
TAVILY_API_KEY=tvly-xxxxxxxxxxxxxxxxxxxxxx
FRED_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENROUTER_API_KEY=sk-or-your-openrouter-api-key

# Optional API Keys
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key_here

# OpenRouter digest defaults
OPENROUTER_MODEL=deepseek/deepseek-v3.2
OPENROUTER_ENABLE_RESPONSE_HEALING=true
OPENROUTER_REQUIRE_PARAMETERS=true
```

**How to Obtain API Keys:**

- **Tavily API** (Required): https://tavily.com/ - Free tier available (1,000 requests/month)
- **FRED API** (Required): https://fred.stlouisfed.org/docs/api/api_key.html - Free registration
- **Alpha Vantage** (Optional): https://www.alphavantage.co/support/#api-key - Free tier available

#### 3. Run the System

**One-Time Execution** (for testing):
```bash
python main.py --mode once
```

**Scheduled Mode** (runs every 6 hours):
```bash
python main.py --mode scheduled
```

#### 4. Check Output

Results are saved in `outputs/` directory:

```
outputs/
├── raw/               # Raw JSON data from each scraper
├── processed/         # Cleaned & deduplicated Markdown reports
└── logs/              # Execution logs
```

**Example Output**: `outputs/processed/report_20260120_141830.md`

### Configuration

All settings are in `config/config.py`:

#### Data Sources

```python
# RSS Feeds
RSS_FEEDS = [
    "https://www.kitco.com/rss/KitcoGold.xml",
    "https://www.fxstreet.com/rss/commodities.xml"
]

# Market Ticker Symbols (yfinance)
TICKER_SYMBOLS = ["DX-Y.NYB", "^TNX", "GC=F", "SI=F"]

# FRED Economic Indicators
FRED_SERIES_IDS = [
    "CPIAUCSL",      # Consumer Price Index
    "PCEPI",         # Personal Consumption Expenditures
    "PAYEMS",        # Non-Farm Payrolls
    "UNRATE",        # Unemployment Rate
    "DGS10",         # 10-Year Treasury Yield
]
```

#### Keyword Filters

**Whitelist** (must contain at least one):
```python
KEYWORD_WHITELIST = [
    "gold", "silver", "XAU", "XAG", "precious metals",
    "inflation", "CPI", "PCE", "Fed", "Federal Reserve",
    "geopolitical", "war", "conflict", "sanctions",
    "central bank", "interest rate", "dollar index"
]
```

**Blacklist** (exclude if contains any):
```python
KEYWORD_BLACKLIST = [
    "crypto", "bitcoin", "ethereum", "NFT",
    "stock market", "S&P 500", "equity"
]
```

#### Scheduling

Default: Every 6 hours. Modify in `schedulers/job_scheduler.py`:

```python
scheduler.add_job(
    run_pipeline,
    "interval",
    hours=6,  # Change interval here
    id="data_pipeline"
)
```

### Output Format

#### Markdown Report Structure

```markdown
# 财经数据报告 | Financial Data Report
生成时间 | Generated: 2026-01-20 14:18:30

## 📊 宏观经济数据 | Macro-Economic Data
### FRED Economic Indicators
- **CPI (Consumer Price Index)**: 3.2% (2026-01-15) #Neutral
- **PCE (Personal Consumption Expenditures)**: 2.8% (2026-01-15) #Bullish
...

## 📰 新闻资讯 | News Articles
### Tavily API News
**Title**: Gold Prices Surge Amid Geopolitical Tensions
**Source**: Reuters | **Published**: 2026-01-20 10:30:00
**Sentiment**: #Bullish
**Summary**: Gold prices jumped 2% as Middle East conflicts escalate...
...
```

### Troubleshooting

#### Issue: "Missing API Key" Error

**Solution**: Ensure `.env` file exists and contains valid API keys:
```bash
cat .env  # Linux/Mac
type .env  # Windows
```

#### Issue: Rate Limit Exceeded

**Solution**: Tavily free tier allows 1,000 requests/month. Reduce query frequency or upgrade to paid plan.

#### Issue: No Data in Output Files

**Possible Causes**:
1. All articles filtered out by keyword rules → Check `KEYWORD_WHITELIST` in `config/config.py`
2. Network connectivity issues → Check logs in `outputs/logs/`
3. API quota exceeded → Verify API key status on provider websites

#### Issue: Import Errors

**Solution**: Ensure all dependencies are installed:
```bash
pip install -r requirements.txt --upgrade
```

### Project Structure

```
FinNews/
├── config/
│   ├── __init__.py
│   └── config.py              # Central configuration
├── utils/
│   ├── __init__.py
│   ├── logger.py              # Logging system
│   └── helpers.py             # Helper functions
├── scrapers/
│   ├── __init__.py
│   ├── base_scraper.py        # Abstract base class
│   ├── tavily_scraper.py      # Tavily API scraper
│   ├── yfinance_scraper.py    # yfinance scraper
│   ├── rss_scraper.py         # RSS feed scraper
│   ├── fred_scraper.py        # FRED API scraper
│   └── alpha_vantage_scraper.py  # Alpha Vantage scraper
├── processors/
│   ├── __init__.py
│   ├── cleaner.py             # Data cleaning & filtering
│   └── deduplicator.py        # MD5-based deduplication
├── storage/
│   ├── __init__.py
│   └── json_storage.py        # JSON/Markdown output
├── schedulers/
│   ├── __init__.py
│   └── job_scheduler.py       # APScheduler job runner
├── outputs/                   # Generated data (gitignored)
├── requirements.txt
├── .env.example
├── .gitignore
└── main.py                    # Main entry point
```

### Advanced Usage

#### Custom Keyword Rules

Edit `config/config.py` to add industry-specific terms:

```python
KEYWORD_WHITELIST = [
    # Existing keywords...
    "mining stocks", "COMEX", "futures", "ETF"
]
```

#### Export to CSV

Modify `storage/json_storage.py` to add CSV export:

```python
import csv

def save_to_csv(self, data, filename):
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
```

### License

MIT License - See LICENSE file for details

---

<a name="chinese"></a>
## 中文文档

### 概述

FinNews 是一个生产级财经新闻聚合管道，专为分析黄金（XAU）和白银（XAG）价格趋势而设计。系统每6小时自动从5个以上数据源抓取新闻，使用关键词规则过滤数据，去重内容，并输出结构化的JSON和Markdown报告供AI智能体分析。

### 功能特性

- **多源数据聚合**：Tavily API、yfinance、RSS源（Kitco、FXStreet）、FRED API、Alpha Vantage
- **智能过滤**：基于白名单/黑名单的关键词过滤系统
- **智能去重**：基于MD5哈希的内容去重，24小时时间窗口
- **LLM友好输出**：为AI分析优化的结构化Markdown报告
- **定时执行**：基于APScheduler的自动化调度（默认：每6小时）
- **情感标签**：自动分类 #Bullish/#Bearish/#Neutral

### 快速开始

#### 1. 安装

```bash
# 克隆仓库
git clone <repository-url>
cd FinNews

# 安装依赖（需要Python 3.10+）
pip install -r requirements.txt
```

#### 2. 配置API密钥

复制环境变量示例文件并配置API密钥：

```bash
cp .env.example .env
```

编辑 `.env` 文件并添加你的API密钥：

```env
# 必需的API密钥
TAVILY_API_KEY=tvly-xxxxxxxxxxxxxxxxxxxxxx
FRED_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 可选的API密钥
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key_here
```

**如何获取API密钥：**

- **Tavily API**（必需）：https://tavily.com/ - 提供免费套餐（1000次请求/月）
- **FRED API**（必需）：https://fred.stlouisfed.org/docs/api/api_key.html - 免费注册
- **Alpha Vantage**（可选）：https://www.alphavantage.co/support/#api-key - 提供免费套餐

#### 3. 运行系统

**单次执行**（用于测试）：
```bash
python main.py --mode once
```

**定时模式**（每6小时运行一次）：
```bash
python main.py --mode scheduled
```

#### 4. 查看输出

结果保存在 `outputs/` 目录：

```
outputs/
├── raw/               # 各个抓取器的原始JSON数据
├── processed/         # 清洗和去重后的Markdown报告
└── logs/              # 执行日志
```

**输出示例**：`outputs/processed/report_20260120_141830.md`

### 配置说明

所有设置都在 `config/config.py` 中：

#### 数据源配置

```python
# RSS订阅源
RSS_FEEDS = [
    "https://www.kitco.com/rss/KitcoGold.xml",
    "https://www.fxstreet.com/rss/commodities.xml"
]

# 市场代码（yfinance）
TICKER_SYMBOLS = ["DX-Y.NYB", "^TNX", "GC=F", "SI=F"]

# FRED经济指标
FRED_SERIES_IDS = [
    "CPIAUCSL",      # 消费者物价指数
    "PCEPI",         # 个人消费支出
    "PAYEMS",        # 非农就业人数
    "UNRATE",        # 失业率
    "DGS10",         # 10年期国债收益率
]
```

#### DuckDuckGo (ddgs) 配置

DuckDuckGo 使用 `ddgs` 包进行新闻抓取，当 `news()` 无结果时会回退到 `text()` 搜索。

```env
DDG_REGION=us-en
DDG_BACKEND=auto
DDG_MAX_RESULTS=5
```

#### 关键词过滤器

**白名单**（必须包含至少一个）：
```python
KEYWORD_WHITELIST = [
    "gold", "silver", "XAU", "XAG", "precious metals",
    "inflation", "CPI", "PCE", "Fed", "Federal Reserve",
    "geopolitical", "war", "conflict", "sanctions",
    "central bank", "interest rate", "dollar index"
]
```

**黑名单**（包含任何一个则排除）：
```python
KEYWORD_BLACKLIST = [
    "crypto", "bitcoin", "ethereum", "NFT",
    "stock market", "S&P 500", "equity"
]
```

#### 定时调度

默认：每6小时。在 `schedulers/job_scheduler.py` 中修改：

```python
scheduler.add_job(
    run_pipeline,
    "interval",
    hours=6,  # 在此修改间隔
    id="data_pipeline"
)
```

### 输出格式

#### Markdown报告结构

```markdown
# 财经数据报告 | Financial Data Report
生成时间 | Generated: 2026-01-20 14:18:30

## 📊 宏观经济数据 | Macro-Economic Data
### FRED Economic Indicators
- **CPI (Consumer Price Index)**: 3.2% (2026-01-15) #Neutral
- **PCE (Personal Consumption Expenditures)**: 2.8% (2026-01-15) #Bullish
...

## 📰 新闻资讯 | News Articles
### Tavily API News
**Title**: Gold Prices Surge Amid Geopolitical Tensions
**Source**: Reuters | **Published**: 2026-01-20 10:30:00
**Sentiment**: #Bullish
**Summary**: Gold prices jumped 2% as Middle East conflicts escalate...
...
```

### 故障排除

#### 问题："缺少API密钥"错误

**解决方案**：确保 `.env` 文件存在且包含有效的API密钥：
```bash
cat .env  # Linux/Mac
type .env  # Windows
```

#### 问题：超出速率限制

**解决方案**：Tavily免费套餐允许每月1000次请求。降低查询频率或升级到付费计划。

#### 问题：输出文件中没有数据

**可能原因**：
1. 所有文章被关键词规则过滤 → 检查 `config/config.py` 中的 `KEYWORD_WHITELIST`
2. 网络连接问题 → 检查 `outputs/logs/` 中的日志
3. API配额用尽 → 在提供商网站上验证API密钥状态

#### 问题：导入错误

**解决方案**：确保所有依赖已安装：
```bash
pip install -r requirements.txt --upgrade
```

### 高级用法

#### 自定义关键词规则

编辑 `config/config.py` 添加行业特定术语：

```python
KEYWORD_WHITELIST = [
    # 现有关键词...
    "mining stocks", "COMEX", "futures", "ETF"
]
```

#### 导出为CSV

修改 `storage/json_storage.py` 添加CSV导出：

```python
import csv

def save_to_csv(self, data, filename):
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
```

### 许可证

MIT许可证 - 详见LICENSE文件

---

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues and questions, please open an issue on GitHub.
