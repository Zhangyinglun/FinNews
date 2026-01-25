# 2026-01-24-new-data-sources-design.md

## 1. 概述
为了解决 Tavily API 配额限制问题，本设计引入 **DuckDuckGo Scraper** 作为免费的主动搜索替代方案，并扩展 **RSS 订阅源** 以增强被动信息获取能力。最终目标是实现**多源并行采集**（Tavily + DDG + RSS），通过强大的去重机制汇聚数据，为 LLM 提供最全面的信息输入。

## 2. DuckDuckGo Scraper 设计

### 2.1 技术选型
*   **库**: `duckduckgo_search` (需添加到 `requirements.txt`)
*   **类名**: `DuckDuckGoScraper` (继承自 `BaseScraper`)
*   **位置**: `scrapers/ddg_scraper.py`

### 2.2 抓取策略
*   **关键词**: 复用 `config.py` 中原本用于 Tavily 的查询词 (`TAVILY_FLASH_QUERIES`, etc.)。
*   **内容提取**: 仅提取搜索结果页面的 `title`, `href` (url), `body` (summary)。
*   **数据结构**:
    ```python
    {
        "title": "SearchResult Title",
        "source": "duckduckgo",
        "summary": "SearchResult Snippet...",
        "url": "...",
        "published_at": "...", # 如果可用，否则当前时间
        "data_type": "news"
    }
    ```
*   **错误处理**: 捕获 `RateLimitException`，实现简单的重试或跳过。

### 2.3 配置开关
*   `ENABLE_DDG`: 新增开关，默认 `True`。

## 3. RSS 源扩展设计

### 3.1 新增源列表
在 `config.py` 的 `RSS_FEEDS` 中追加：
*   **Kitco Gold**: `https://www.kitco.com/rss/category/commodities/gold`
*   **CNBC Commodities**: `https://www.cnbc.com/id/10000086/device/rss/rss.html`
*   **DailyFX Commodities**: `https://www.dailyfx.com/feeds/market-news`

## 4. 全量并行集成设计

### 4.1 逻辑变更
*   **Main Logic**: 在 `main.py` 中，不再互斥。
    ```python
    if Config.ENABLE_TAVILY: scrapers.append(TavilyScraper())
    if Config.ENABLE_DDG: scrapers.append(DuckDuckGoScraper())
    if Config.ENABLE_RSS: scrapers.append(RSSFeedScraper())
    ```
*   **去重**: 依赖现有的 `Deduplicator` (基于 URL MD5)。由于 DDG 和 Tavily 可能抓到同一 URL，去重器将自动保留第一份，丢弃后续重复项，确保数据干净。

## 5. 风险与缓解
*   **DDG 限流**: 设置请求间隔（sleep），避免并发请求。
*   **Token 超限**: 增加的数据量可能导致 LLM Token 溢出。现有 `DigestController` 已有筛选逻辑，且 `OPENROUTER_MAX_TOKENS` 设置较大，暂不作为阻碍点，后续可观察日志调整。
