# AGENTS.md — FinNews 项目指南

**最后更新:** 2026-01-23
**分支:** main

## 🔴 全局强制规范 (Global Mandates)

### 1. 强制中文输出 (Mandatory Chinese Output)
*   **所有** 交互、注释、文档和提交信息 (commit messages) 必须使用 **简体中文**。
*   **例外**: 变量名、函数名、技术术语 (API, JSON) 和 CLI 命令。
*   **示例**: `git commit -m "修复数据抓取逻辑"` (正确) vs `Fix scraper logic` (错误)。

### 2. 绝对路径 (Absolute Paths Only)
*   所有文件操作必须使用 **绝对路径** (例如: `D:\Projects\FinNews\...`)。
*   严禁在工具调用中使用相对路径。

---

## 项目概览 (Overview)
用于黄金/白银价格分析的财经新闻聚合管道。抓取 5+ 个数据源，通过关键词过滤，去重，应用规则驱动的市场信号分析，并输出结构化报告供 LLM 使用。

## 技术栈 (Tech Stack)
*   **Python**: 3.10+
*   **管道**: Scrapers (抓取) → Processors (处理) → Analyzers (分析) → Storage (存储)
*   **测试**: 自定义运行器 (`run_tests.py`)，**不使用** pytest/unittest 自动发现。
*   **日志**: `utils/logger.py` (双语/中文)。
*   **数据模型**: Pydantic。

---

## 常用命令 (Commands)

### 安装
```bash
pip install -r requirements.txt
```

### 运行
```bash
# 运行完整管道
python main.py
```

### 测试 (自定义运行器)
```bash
# 运行所有测试
python run_tests.py

# 运行特定模块测试 (scrapers, processors, storage, utils, config, integration)
python run_tests.py scrapers

# 运行"快速"测试 (跳过耗时的 API 调用)
python run_tests.py --quick
```

### 单个测试执行
测试是独立的脚本。直接使用 Python 运行：
```bash
python tests/scrapers/test_tavily.py
```

---

## 代码风格与规范 (Code Style)

### 1. 格式化与导入
*   **缩进**: 4 空格。
*   **行长**: ~88-100 字符。
*   **导入**: 标准 `import` 顺序。
*   **测试导入**: 必须在文件顶部使用绝对路径插入：
    ```python
    import sys
    sys.path.insert(0, "D:\\Projects\\FinNews")
    from scrapers import ...
    ```

### 2. 命名规范
*   **类**: `PascalCase`
*   **函数/变量**: `snake_case`
*   **常量**: `UPPER_SNAKE_CASE`
*   **私有成员**: `_prefix`

### 3. 类型与文档
*   **类型提示**: 所有函数必须包含 (例如: `def run() -> List[Dict]:`)。
*   **文档字符串**: **中文** 或双语。
*   **日志**: 推荐双语 (例如: `"任务开始 | Task started"`).

### 4. 错误处理
*   外部 API 调用必须包裹在 `try/except` 中。
*   使用 `logger.error(..., exc_info=True)` 记录完整堆栈。

---

## 项目结构 (Structure)
```
FinNews/
├── scrapers/         # 数据抓取器 (Tavily, RSS 等)
├── processors/       # 清洗与去重 (Cleaning & Deduplication)
├── analyzers/        # 规则引擎与市场信号 (Rule Engine & Market Signals)
├── models/           # Pydantic 数据模型
├── storage/          # JSON & Markdown 输出
├── utils/            # 日志, 邮件, LLM 辅助工具
├── config/           # 配置与 .env
├── tests/            # 测试脚本 (镜像结构)
│   ├── scrapers/     # 例如: test_tavily.py
│   └── ...
├── main.py           # 入口点
└── run_tests.py      # 自定义测试运行器
```

---

## 独特模式 (Unique Patterns)

### 市场分析
*   **时间窗口**: Flash (24h), Cycle (7d), Trend (30d)。
*   **规则引擎**: 生成 `MarketSignal` (VIX 等级, 宏观偏向, 情绪分数)。

### 数据流
*   **去重**: 基于 MD5 哈希，24小时滚动窗口。
*   **过滤**: 关键词白名单/黑名单，在 `config/config.py` 中配置。

### "反模式" (禁止事项)
*   ❌ **禁止** 添加 `pytest` 或 `unittest` 自动发现 (坚持使用 `run_tests.py`)。
*   ❌ **禁止** 引入 linters/formatters (除非明确要求)。
*   ❌ **禁止** 删除测试文件中的 `sys.path.insert` hack。
*   ❌ **禁止** 重构无关代码。
*   ❌ **禁止** 纯英文注释/提交 (必须包含中文)。

---

## 查阅指南 (Where to Look)

| 任务 | 位置 |
|------|----------|
| **添加数据源** | `scrapers/` (继承 BaseScraper) + 在 `main.py` 中注册 |
| **编辑规则** | `analyzers/rule_engine.py` + `config/config.py` |
| **输出格式** | `storage/json_storage.py` |
| **日志** | `utils/logger.py` |

---

## 已知缺口 (Known Gaps)
*   文档中提到的 `schedulers/` 目录不存在。
*   `main.py` 忽略了一些 CLI 参数。
*   测试依赖硬编码路径 (`D:\Projects\FinNews`)。
