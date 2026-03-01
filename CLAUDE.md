# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 全局强制规范

- **语言**: 所有交互、注释、文档和 commit message 必须使用**简体中文**（变量名、函数名、技术术语保留英文）

## 常用命令

```bash
# 安装依赖
pip install -r requirements.txt

# 运行完整管道
python main.py

# 运行所有测试（pytest）
python run_tests.py
# 或直接使用 pytest
pytest

# 运行特定模块测试 (scrapers|processors|storage|utils|config|integration)
python run_tests.py scrapers

# 快速测试（跳过慢速和集成测试）
python run_tests.py quick
python run_tests.py --quick

# 运行单个测试文件
pytest tests/scrapers/test_tavily.py -v

# 运行集成测试
pytest tests/ -m integration
```

## 项目架构

黄金/白银财经新闻聚合管道。从 5+ 数据源采集数据，经过清洗、去重、规则引擎分析，生成结构化报告并通过邮件发送。

### 9 步管道流程 (main.py)

```
环境验证 → 初始化爬虫 → 数据采集 → 价格补全(Stooq兜底→本地缓存回退)
→ 清洗+去重 → 内容增强(ContentFetcher) → 规则引擎(VIX/DXY/US10Y/COMEX警报)
→ 三窗口数据组织(Flash 12h / Cycle 7d / Trend 30d) → 邮件生成+发送
```

### 模块职责

| 目录 | 职责 |
|------|------|
| `scrapers/` | 11 个数据源爬虫，继承 `BaseScraper`，返回 `List[Dict]` |
| `processors/` | `DataCleaner`(关键词白/黑名单过滤) + `Deduplicator`(MD5+模糊匹配) |
| `analyzers/` | `RuleEngine`(市场信号生成) + `MarketAnalyzer`(多窗口数据组织) |
| `models/` | Pydantic 数据模型: PriceData, NewsItem, MarketSignal, ComexSignal 等 |
| `storage/` | JSON 和 Markdown 输出 |
| `utils/` | 邮件(mailer)、LLM客户端(openrouter_client)、摘要生成(digest_controller)、日志(logger)等 |
| `config/config.py` | 统一配置管理，环境变量 + 默认值，支持 validate() 验证 |

### 关键设计模式

- **爬虫层**: 策略模式 — `BaseScraper` 定义接口，各爬虫实现 `fetch()`，main.py 根据 `ENABLE_*` 开关动态创建
- **价格兜底**: yfinance → Stooq 补充 → 本地缓存回退，确保关键数据可用
- **去重**: MD5 精确匹配 + 标题模糊匹配(SequenceMatcher > 0.75)，24h 滚动窗口，跨运行状态持久化
- **规则引擎**: VIX 绝对值/暴涨检测、DXY+US10Y 组合判断、COMEX 库存三级预警(SAFE/YELLOW/RED/SYSTEM_FAILURE)
- **邮件输出**: 支持 plain_text（直接构建）和 html（LLM 生成摘要 → 模板渲染）两种模式

## 添加新数据源

1. 在 `scrapers/` 中创建新爬虫，继承 `BaseScraper`
2. 在 `config/config.py` 中添加 `ENABLE_*` 开关和相关配置
3. 在 `main.py` 中注册爬虫实例

## 禁止事项

- 禁止纯英文注释/提交（必须包含中文）
- 禁止重构无关代码
