# 新闻综述聚合 实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将邮件中"重点新闻+其他新闻"两个扁平列表改为按事件/主题聚合的"新闻综述组"格式，由 LLM 完成语义聚合。

**Architecture:** 修改 `utils/digest_controller.py` 中的 LLM prompt、JSON Schema 和 HTML 渲染逻辑。Python 端在构建 prompt 前做一轮标题去重过滤，语义聚合完全交给 LLM。同步更新 `main.py` 中的 system_prompt 和日志，以及所有依赖旧 schema 的测试。

**Tech Stack:** Python 3.10+, Pydantic, OpenRouter LLM API

---

### Task 1: 新增 `_pre_deduplicate_news` 预处理方法

**Files:**
- Modify: `utils/digest_controller.py:35-48` (DigestController 类)

**Step 1: 在 DigestController 类中新增导入和预处理方法**

在文件顶部添加 `re` 导入（如果没有的话），然后在 `DigestController` 类中 `build_llm_prompt` 方法之前新增方法：

```python
import re  # 添加到文件顶部导入区

# 在 DigestController 类内部，__init__ 之后，build_llm_prompt 之前
def _normalize_title(self, title: str) -> List[str]:
    """
    标题归一化：小写化 + 提取词汇 + 轻量词形还原
    复用 Deduplicator 的归一化思路
    """
    text = title.lower().strip()
    # 提取英文单词和中文字符
    tokens = re.findall(r'[a-z]+|[\u4e00-\u9fff]', text)
    # 轻量词形还原
    normalized = []
    for t in tokens:
        if t.endswith('ing') and len(t) > 4:
            t = t[:-3]
        elif t.endswith('ies') and len(t) > 4:
            t = t[:-3] + 'y'
        elif t.endswith('es') and len(t) > 3:
            t = t[:-2]
        elif t.endswith('s') and len(t) > 3:
            t = t[:-1]
        normalized.append(t)
    return normalized

def _pre_deduplicate_news(self, news_list: list) -> list:
    """
    传入 LLM 前的标题去重过滤
    使用 Jaccard 相似度剔除高度重复的条目，保留质量更高的一条
    阈值 0.75，只做精确/近似去重，不做语义聚合
    """
    if not news_list:
        return []

    threshold = 0.75
    kept = []
    kept_tokens = []

    for news in news_list:
        title = news.title if hasattr(news, 'title') else str(news)
        tokens = set(self._normalize_title(title))

        is_dup = False
        for i, existing_tokens in enumerate(kept_tokens):
            if not tokens or not existing_tokens:
                continue
            intersection = tokens & existing_tokens
            union = tokens | existing_tokens
            jaccard = len(intersection) / len(union) if union else 0

            if jaccard >= threshold:
                # 保留 relevance_score 更高的一条
                existing_score = getattr(kept[i], 'relevance_score', None) or 0
                new_score = getattr(news, 'relevance_score', None) or 0
                if new_score > existing_score:
                    kept[i] = news
                    kept_tokens[i] = tokens
                is_dup = True
                break

        if not is_dup:
            kept.append(news)
            kept_tokens.append(tokens)

    return kept
```

**Step 2: 验证语法**

运行: `python -c "import sys; sys.path.insert(0, '/mnt/d/Projects/FinNews'); from utils.digest_controller import DigestController; print('OK')"`
预期: 输出 `OK`

**Step 3: 提交**

```bash
git add utils/digest_controller.py
git commit -m "新增新闻标题预去重方法 _pre_deduplicate_news"
```

---

### Task 2: 改造 `build_llm_prompt` 方法

**Files:**
- Modify: `utils/digest_controller.py:67-301` (build_llm_prompt 方法)

**Step 1: 在新闻数据构建前插入预去重调用**

在 `build_llm_prompt` 方法中，三个窗口新闻输出部分（约第 150-245 行）之前，对每个窗口的新闻列表调用预去重：

```python
# 在 "# === 新闻数据 ===" 注释之前插入
# 预去重：剔除高度重复的新闻标题
flash_news = self._pre_deduplicate_news(data.flash.news[:15])
cycle_news = self._pre_deduplicate_news(data.cycle.news[:10])
trend_news = self._pre_deduplicate_news(data.trend.news[:8])
```

然后将后面三个循环中的 `data.flash.news[:15]` 改为 `flash_news`，`data.cycle.news[:10]` 改为 `cycle_news`，`data.trend.news[:8]` 改为 `trend_news`。

**Step 2: 替换任务说明部分**

将原来第 247-287 行的【你的任务】部分替换为新版：

```python
# === 任务说明 ===
lines.append("=" * 60)
lines.append("【你的任务】")
lines.append("=" * 60)
lines.append("")
lines.append("1. 生成邮件标题 (subject)")
lines.append("   - 格式: YYYY-MM-DD 市场日报：[今日核心内容]")
lines.append("   - 要求: 不要在标题中固定使用VIX警报词或符号")
lines.append("   - 例如: 2026-01-20 市场日报：美联储表态偏鹰，金价高位震荡")
lines.append("")
lines.append("2. 新闻综述聚合 (news_clusters)")
lines.append("   - 将上述所有新闻按事件/主题进行语义聚合")
lines.append("   - 报道同一事件的不同角度新闻合并到同一个 cluster")
lines.append("   - 独立新闻（无相关新闻）单独成为一个 cluster")
lines.append("   - cluster 之间按重要性排序（最重要的事件排第一）")
lines.append("   - 每个 cluster 内的 sources 也按重要性排序")
lines.append("   - 重要性排序规则:")
lines.append("     1) 影响标签: Bullish/Bearish > Neutral")
lines.append("     2) 相关性评分: 越高越优先")
lines.append("     3) 时效性: 越新越优先")
lines.append("   - 每个 cluster 必须包含:")
lines.append("     * cluster_title: 综述标题（中文），概括该组新闻的核心事件")
lines.append("     * cluster_summary: 整合摘要（中文，1-3句话），综合所有相关新闻的核心含义")
lines.append("     * impact_tag: 该事件对贵金属的整体影响方向 (Bullish/Bearish/Neutral)")
lines.append("     * sources: 原始新闻列表，每条含 title, source, url, timestamp")
lines.append("   - 综述标题和摘要应整合多条新闻的信息，而非简单复制某一条")
lines.append("   - 所有英文标题和摘要必须翻译成中文")
lines.append("   - 新闻只陈述事实，不要添加分析性判断")
lines.append("")
lines.append("3. 撰写精简的市场分析 (analysis)")
lines.append("   - market_sentiment: 当前市场情绪判断 (基于VIX和宏观数据)")
lines.append("   - price_outlook: 黄金白银短期走势预判")
lines.append("   - risk_factors: 需要关注的风险点")
lines.append("   - trading_suggestion: 操作建议")
lines.append("   - 每项30-60字，用要点式写作，专业但易懂")
lines.append("")
```

**Step 3: 验证 prompt 可生成**

运行: `python -c "...构造最小 MultiWindowData 和 MarketSignal，调用 build_llm_prompt 检查无异常..."`
预期: 无报错

**Step 4: 提交**

```bash
git add utils/digest_controller.py
git commit -m "改造 build_llm_prompt：新闻预去重 + 综述聚合任务指令"
```

---

### Task 3: 替换 JSON Schema

**Files:**
- Modify: `utils/digest_controller.py:866-986` (DIGEST_JSON_SCHEMA)

**Step 1: 替换完整 schema**

将原有的 `DIGEST_JSON_SCHEMA` 替换为：

```python
DIGEST_JSON_SCHEMA: Dict[str, Any] = {
    "name": "finnews_digest_data",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "subject": {
                "type": "string",
                "description": "邮件标题，格式: YYYY-MM-DD 市场日报：[今日核心内容]",
            },
            "news_clusters": {
                "type": "array",
                "description": "新闻综述组，按事件/主题聚合，按重要性排序",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "cluster_title": {
                            "type": "string",
                            "description": "综述标题（中文），概括该组新闻的核心事件",
                        },
                        "cluster_summary": {
                            "type": "string",
                            "description": "整合摘要（中文，1-3句话），综合所有相关新闻的核心含义",
                        },
                        "impact_tag": {
                            "type": "string",
                            "enum": ["Bullish", "Bearish", "Neutral"],
                            "description": "该事件对贵金属的整体影响方向",
                        },
                        "sources": {
                            "type": "array",
                            "description": "原始新闻列表，按重要性排序",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "title": {
                                        "type": "string",
                                        "description": "原始新闻标题（中文）",
                                    },
                                    "source": {
                                        "type": "string",
                                        "description": "新闻来源",
                                    },
                                    "url": {
                                        "type": "string",
                                        "description": "新闻原文链接，无链接时返回空字符串",
                                    },
                                    "timestamp": {
                                        "type": "string",
                                        "description": "新闻发布时间，格式 HH:MM，未知时返回空字符串",
                                    },
                                },
                                "required": ["title", "source", "url", "timestamp"],
                            },
                        },
                    },
                    "required": [
                        "cluster_title",
                        "cluster_summary",
                        "impact_tag",
                        "sources",
                    ],
                },
            },
            "analysis": {
                "type": "object",
                "additionalProperties": False,
                "description": "市场分析 (所有分析内容集中在此)",
                "properties": {
                    "market_sentiment": {
                        "type": "string",
                        "description": "市场情绪判断，30-60字要点式",
                    },
                    "price_outlook": {
                        "type": "string",
                        "description": "走势预判，30-60字要点式",
                    },
                    "risk_factors": {
                        "type": "string",
                        "description": "风险因素，30-60字要点式",
                    },
                    "trading_suggestion": {
                        "type": "string",
                        "description": "操作建议，30-60字要点式",
                    },
                },
                "required": [
                    "market_sentiment",
                    "price_outlook",
                    "risk_factors",
                    "trading_suggestion",
                ],
            },
        },
        "required": ["subject", "news_clusters", "analysis"],
    },
}
```

**Step 2: 提交**

```bash
git add utils/digest_controller.py
git commit -m "替换 JSON Schema：key_news+other_news → news_clusters"
```

---

### Task 4: 新增 `_render_news_clusters` 渲染方法

**Files:**
- Modify: `utils/digest_controller.py:528-578` (替换 `_render_news_list`)

**Step 1: 新增 `_render_news_clusters` 方法**

在 `_render_news_list` 方法之后（或替换它），新增：

```python
def _render_news_clusters(self, clusters: List[Dict[str, Any]]) -> str:
    """渲染新闻综述组HTML (内联样式，Gmail兼容)"""
    if not clusters:
        return '<div style="padding: 14px 0; color: #64748b; font-size: 14px;">暂无相关新闻</div>'

    items = []
    for i, cluster in enumerate(clusters):
        cluster_title = cluster.get("cluster_title", "无标题")
        cluster_summary = cluster.get("cluster_summary", "")
        impact_tag = cluster.get("impact_tag", "Neutral")
        sources = cluster.get("sources", [])

        # 最后一组不加底部边框
        border_style = (
            "border-bottom: 1px solid #e2e8f0; margin-bottom: 16px; padding-bottom: 16px;"
            if i < len(clusters) - 1
            else ""
        )

        # impact_tag 彩色标签
        impact_tag_map = {
            "Bullish": ("利多", "#166534", "#dcfce7"),
            "Bearish": ("利空", "#991b1b", "#fee2e2"),
            "Neutral": ("中性", "#475569", "#e2e8f0"),
        }
        tag_text, tag_color, tag_bg = impact_tag_map.get(
            impact_tag, ("中性", "#6c757d", "#e9ecef")
        )
        impact_tag_html = (
            f'<span style="display: inline-block; padding: 2px 8px; '
            f"border-radius: 12px; font-size: 12px; font-weight: 600; "
            f"color: {tag_color}; background-color: {tag_bg}; "
            f'margin-right: 8px; vertical-align: middle;">{tag_text}</span>'
        )

        # 综述标题
        title_html = (
            f'<span style="font-size: 16px; font-weight: 600; '
            f'color: #0f172a; line-height: 1.5;">{cluster_title}</span>'
        )

        # 综述摘要
        summary_html = ""
        if cluster_summary:
            summary_html = (
                f'<div style="font-size: 14px; color: #334155; '
                f'line-height: 1.7; margin: 8px 0 10px 0;">{cluster_summary}</div>'
            )

        # 原始新闻链接列表
        source_items = []
        for src in sources:
            src_title = src.get("title", "")
            src_source = src.get("source", "")
            src_url = src.get("url", "")
            src_timestamp = src.get("timestamp", "")

            # 来源和时间
            meta_parts = []
            if src_source:
                meta_parts.append(src_source)
            if src_timestamp:
                meta_parts.append(src_timestamp)
            meta_str = " · ".join(meta_parts)

            if src_url:
                link_html = (
                    f'<a href="{src_url}" style="color: #2563eb; '
                    f'text-decoration: none; font-size: 13px;" '
                    f'target="_blank">{src_title}</a>'
                )
            else:
                link_html = (
                    f'<span style="color: #475569; font-size: 13px;">'
                    f'{src_title}</span>'
                )

            meta_html = ""
            if meta_str:
                meta_html = (
                    f'<span style="color: #94a3b8; font-size: 12px; '
                    f'margin-left: 6px;">({meta_str})</span>'
                )

            source_items.append(
                f'<div style="padding: 3px 0 3px 12px;">'
                f'<span style="color: #94a3b8; margin-right: 6px;">·</span>'
                f'{link_html}{meta_html}</div>'
            )

        sources_html = "\n".join(source_items) if source_items else ""

        cluster_html = f"""<div style="{border_style}">
            <div style="margin-bottom: 6px;">{impact_tag_html}{title_html}</div>
            {summary_html}
            {sources_html}
        </div>"""
        items.append(cluster_html)

    return "\n".join(items)
```

**Step 2: 提交**

```bash
git add utils/digest_controller.py
git commit -m "新增 _render_news_clusters 综述组渲染方法"
```

---

### Task 5: 修改 `render_email_html` 和 HTML 模板

**Files:**
- Modify: `utils/digest_controller.py:318-527` (render_email_html)
- Modify: `utils/digest_controller.py:992-1099` (EMAIL_TEMPLATE)

**Step 1: 修改 render_email_html 中的新闻渲染调用**

将原来的两行：
```python
key_news_html = self._render_news_list(digest_data.get("key_news", []))
other_news_html = self._render_news_list(digest_data.get("other_news", []))
```

替换为：
```python
news_clusters_html = self._render_news_clusters(digest_data.get("news_clusters", []))
```

**Step 2: 修改 `html = EMAIL_TEMPLATE.format(...)` 调用**

将 `key_news=key_news_html, other_news=other_news_html` 替换为 `news_clusters=news_clusters_html`。

**Step 3: 修改 EMAIL_TEMPLATE**

将原来的两个板块（"重点新闻" Section 2 + "其他新闻" Section 3）合并为一个 "新闻综述" 板块：

```html
<!-- Section 2: News Clusters -->
<tr>
    <td style="padding: 0 16px 20px 16px;">
        <div style="border: 1px solid #e2e8f0; border-radius: 10px; overflow: hidden; background-color: #ffffff;">
            <div style="background-color: #1e293b; padding: 11px 14px; border-bottom: 1px solid #334155;">
                <span style="display: inline-block; width: 3px; height: 18px; background-color: #ca8a04; margin-right: 8px; vertical-align: middle;"></span>
                <span style="font-size: 17px; font-weight: 600; color: #f8fafc; vertical-align: middle;">新闻综述</span>
            </div>
            <div style="padding: 10px 16px;">
                {news_clusters}
            </div>
        </div>
    </td>
</tr>
```

**Step 4: 提交**

```bash
git add utils/digest_controller.py
git commit -m "合并重点/其他新闻板块为新闻综述板块"
```

---

### Task 6: 更新 `main.py` 中的 system_prompt 和日志

**Files:**
- Modify: `main.py:532-552` (system_prompt)
- Modify: `main.py:579-583` (日志)

**Step 1: 替换 system_prompt**

将 `main.py` 第 533-552 行的 system_prompt 替换为：

```python
system_prompt = """你是一位专业的金融分析师，专注于黄金白银市场。
请根据提供的数据，返回结构化的JSON数据。

你的任务:
1. 生成邮件标题 (subject)
2. 将所有新闻按事件/主题进行语义聚合，生成新闻综述组 (news_clusters)
   - 报道同一事件的不同角度新闻合并到同一个 cluster
   - 独立新闻单独成组
   - cluster 按重要性排序，每个 cluster 内 sources 也按重要性排序
3. 撰写精简的市场分析 (analysis) — 每项30-60字，用要点式

重要规则:
- 所有英文新闻标题和摘要必须翻译成中文
- 新闻综述只陈述事实，不要添加任何分析性语言
- 所有分析、判断、建议必须放在analysis字段
- 每个 cluster 包含: cluster_title, cluster_summary, impact_tag, sources[]
- 每个 source 包含: title, source, url, timestamp
- url和timestamp若原始数据中无，则填空字符串
- 使用中文，专业但易懂
- 严格按照JSON Schema返回结果"""
```

**Step 2: 修改日志输出**

将 `main.py` 第 579-583 行的日志：
```python
logger.debug(
    f"LLM返回数据: subject={digest_data.get('subject', 'N/A')[:50]}, "
    f"key_news={len(digest_data.get('key_news', []))}, "
    f"other_news={len(digest_data.get('other_news', []))}"
)
```

替换为：
```python
logger.debug(
    f"LLM返回数据: subject={digest_data.get('subject', 'N/A')[:50]}, "
    f"news_clusters={len(digest_data.get('news_clusters', []))}"
)
```

**Step 3: 提交**

```bash
git add main.py
git commit -m "更新 main.py 的 system_prompt 和日志适配新闻综述格式"
```

---

### Task 7: 更新测试文件

**Files:**
- Modify: `tests/utils/test_digest_price_table.py`
- Modify: `tests/utils/test_digest_to_file.py`
- Modify: `tests/utils/test_openrouter_digest.py`

**Step 1: 修改 test_digest_price_table.py**

将 `digest_data` 中的 `key_news` + `other_news` 替换为 `news_clusters`:

```python
digest_data = {
    "subject": "测试邮件",
    "news_clusters": [],
    "analysis": {},
}
```

**Step 2: 修改 test_digest_to_file.py**

将第 94-109 行的 system_prompt 更新为新版（与 Task 6 中 main.py 的一致）。

**Step 3: 修改 test_openrouter_digest.py**

检查并更新该文件中对 `key_news` / `other_news` 的引用为 `news_clusters`。

**Step 4: 运行测试验证**

运行: `python run_tests.py utils`
预期: 所有 utils 测试通过

**Step 5: 提交**

```bash
git add tests/
git commit -m "更新测试文件适配 news_clusters 新格式"
```

---

### Task 8: 端到端验证

**Step 1: 运行 test_digest_to_file 生成预览**

运行: `python -m tests.utils.test_digest_to_file`
预期: 生成 HTML 文件，打开后可见"新闻综述"板块，每个 cluster 含标题 + 摘要 + impact 标签 + 可点击的原始新闻链接

**Step 2: 运行完整测试**

运行: `python run_tests.py`
预期: 所有测试通过

**Step 3: 提交最终状态（如有修复）**

```bash
git add -A
git commit -m "新闻综述聚合功能完成：LLM驱动的语义聚合 + 综述组渲染"
```
