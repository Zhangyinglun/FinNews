# Sonar 接入主流程设计方案

**创建日期**: 2026-01-25  \
**状态**: 已确认  \
**作者**: OpenCode

---

## 1. 目标

将 Perplexity Sonar 作为新的新闻发现数据源接入主流程，保持与 Tavily/DDG 并行，仍由清洗、去重与正文抓取链路控制质量与一致性。

核心原则:
- Sonar 仅负责“引用发现”，不替代正文抓取与去重判定。
- citations 为空则跳过，不进入后续链路。
- 失败不阻断全流程，日志可追踪。

---

## 2. 数据流

```
SonarScraper (引用发现)
      │
      ├─ answer + citations
      ▼
统一记录结构 (window_type/query/sonar_answer)
      ▼
DataCleaner → Deduplicator → ContentFetcher
      ▼
下游分析与存储
```

---

## 3. 组件与接入点

### 3.1 `scrapers/__init__.py`
- 导出 `SonarScraper`，支持主入口 import。

### 3.2 `main.py`
- 添加 `SonarScraper` import。
- 在初始化数据源列表中追加 `SonarScraper`，由 `ENABLE_SONAR` 控制。
- 日志输出 "✓ Sonar 爬虫就绪" 便于验证。

### 3.3 `config/config.py`
- 新增 `ENABLE_SONAR` 数据源开关。
- 新增 `SONAR_MODEL` 配置 (默认 `perplexity/sonar`)。
- 新增 `SONAR_USE_TRUSTED_DOMAINS` 过滤开关 (默认 false)。

### 3.4 `.env.example`
- 增加 Sonar 配置示例，并提醒复用 `OPENROUTER_API_KEY`。

---

## 4. 错误处理与可观测性

- Sonar 初始化失败仅记录 warning，不影响其他数据源。
- 查询失败记录 `exc_info=True` 堆栈，便于排查。
- 统计日志记录 Flash/Cycle/Trend 数量。
- 可选 `SONAR_USE_TRUSTED_DOMAINS` 过滤并记录被过滤的引用 (debug)。

---

## 5. 测试与验证

1. `tests/utils/test_sonar_client.py`
   - 提示词要求 citations
   - citations 解析 (字符串/字典)
   - 异常日志 `exc_info=True`

2. `tests/scrapers/test_sonar_scraper.py`
   - 可信域过滤、无 scheme 处理
   - `sonar_*` 元字段
   - window_type/query 字段

3. 运行验证
   - `python run_tests.py --quick`
   - `python main.py` 观察 `Sonar采集完成` 日志

---

## 6. 交付清单

- `main.py` + `scrapers/__init__.py` 主流程接入
- `config/config.py` + `.env.example` 配置接入
- Sonar 统计日志与异常堆栈
- Sonar 单元测试与爬虫测试
