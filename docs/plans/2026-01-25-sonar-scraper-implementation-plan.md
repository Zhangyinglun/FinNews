# Sonar 数据源补强 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为 Sonar 数据源补齐引用质量控制、记录元数据与日志统计，提升稳定性与可观测性。

**Architecture:** Sonar 继续作为并行数据源，新增可选可信域过滤与记录字段，同时优化提示词与统计日志。主流水线保持不变，仅在 SonarClient/SonarScraper/Config 与对应测试中改动。

**Tech Stack:** Python 3.10+, requests, dataclasses, 自定义测试脚本 (run_tests.py)

---

**前置说明**
- 测试脚本要求 `sys.path.insert(0, "D:\\Projects\\FinNews")`，路径硬编码为主工作区。
- 计划执行时，若需要在 worktree 内运行测试，请确保该路径指向当前实现代码。

---

### Task 1: SonarClient 提示词构建与测试

**Files:**
- Create: `D:\Projects\FinNews\tests\utils\test_sonar_client.py`
- Modify: `D:\Projects\FinNews\utils\sonar_client.py`

**Step 1: Write the failing test**

```python
"""
测试 SonarClient 提示词与 payload 构建
"""

import sys

sys.path.insert(0, "D:\\Projects\\FinNews")

from utils.sonar_client import SonarClient


def test_build_payload_contains_citations_requirement():
    """系统提示词必须明确要求 citations 引用"""
    client = SonarClient(api_key="dummy")
    payload = client._build_payload("gold news", max_tokens=128)
    system_prompt = payload["messages"][0]["content"]
    assert "citation" in system_prompt.lower() or "引用" in system_prompt, "提示词未强调引用链接"


if __name__ == "__main__":
    test_build_payload_contains_citations_requirement()
```

**Step 2: Run test to verify it fails**

Run: `python tests/utils/test_sonar_client.py`

Expected: 失败，提示 `_build_payload` 未定义或断言不成立。

**Step 3: Write minimal implementation**

在 `D:\Projects\FinNews\utils\sonar_client.py` 中新增 `_build_payload` 并让 `search` 复用：

```python
    def _build_payload(self, query: str, max_tokens: int) -> Dict[str, Any]:
        system_prompt = (
            "你是一个新闻搜索助手。请搜索最新的相关新闻，"
            "简要总结关键信息，并提供来源链接。"
            "必须返回 citations 引用链接，仅使用权威新闻来源。"
        )
        return {
            "model": self.model,
            "temperature": 0.1,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query},
            ],
        }

    def search(self, query: str, max_tokens: int = 1024) -> SonarSearchResult:
        url = f"{self.base_url}/chat/completions"
        payload = self._build_payload(query, max_tokens)
```

**Step 4: Run test to verify it passes**

Run: `python tests/utils/test_sonar_client.py`

Expected: PASS

**Step 5: Commit**

```bash
git add D:\Projects\FinNews\utils\sonar_client.py D:\Projects\FinNews\tests\utils\test_sonar_client.py
git commit -m "补强 Sonar 提示词构建与测试"
```

---

### Task 2: SonarScraper 引用过滤与元数据字段

**Files:**
- Create: `D:\Projects\FinNews\tests\scrapers\test_sonar_scraper.py`
- Modify: `D:\Projects\FinNews\scrapers\sonar_scraper.py`
- Modify: `D:\Projects\FinNews\config\config.py`
- Modify: `D:\Projects\FinNews\.env.example`

**Step 1: Write the failing test**

```python
"""
测试 SonarScraper 引用过滤与元数据字段
"""

import os
import sys

os.environ["OPENROUTER_API_KEY"] = "dummy"

sys.path.insert(0, "D:\\Projects\\FinNews")

from config.config import Config
from scrapers.sonar_scraper import SonarScraper
from utils.sonar_client import SonarSearchResult, Citation


class FakeClient:
    def search(self, query: str):
        return SonarSearchResult(
            answer="summary",
            citations=[
                Citation(url="https://reuters.com/article/abc", title="Reuters"),
                Citation(url="https://example.com/x", title="Example"),
            ],
        )


def test_sonar_scraper_trusted_domain_filter_and_fields():
    """仅保留可信域引用并附加元数据字段"""
    Config.SONAR_USE_TRUSTED_DOMAINS = True
    Config.TRUSTED_DOMAINS = ["reuters.com"]

    scraper = SonarScraper()
    scraper.client = FakeClient()

    results = scraper._fetch_window(["gold"], "flash")
    assert len(results) == 1, "可信域过滤应只保留 1 条"

    record = results[0]
    assert record.get("sonar_citations_count") == 2, "应记录原始引用数量"
    assert record.get("sonar_model"), "应记录 sonar_model"
    assert record.get("sonar_answer") == "summary", "应记录 sonar_answer"
    assert record.get("window_type") == "flash", "应记录 window_type"
    assert record.get("query") == "gold", "应记录 query"


if __name__ == "__main__":
    test_sonar_scraper_trusted_domain_filter_and_fields()
```

**Step 2: Run test to verify it fails**

Run: `python tests/scrapers/test_sonar_scraper.py`

Expected: 失败（字段缺失或过滤未实现）。

**Step 3: Write minimal implementation**

在 `D:\Projects\FinNews\config\config.py` 增加开关：

```python
    # Sonar 引用过滤开关
    SONAR_USE_TRUSTED_DOMAINS = _getenv_bool("SONAR_USE_TRUSTED_DOMAINS", "false")
```

在 `D:\Projects\FinNews\scrapers\sonar_scraper.py` 增加过滤与字段：

```python
from urllib.parse import urlparse

    def __init__(self):
        super().__init__("Sonar")
        self.sonar_model = getattr(Config, "SONAR_MODEL", "perplexity/sonar")
        self.client = SonarClient(
            api_key=Config.OPENROUTER_API_KEY,
            model=self.sonar_model,
            ...
        )

    @staticmethod
    def _is_trusted_domain(url: str, trusted_domains: List[str]) -> bool:
        domain = urlparse(url).netloc.lower()
        return any(domain == d or domain.endswith("." + d) for d in trusted_domains)

    def _fetch_window(...):
        ...
        for query in queries:
            ...
            response = self.client.search(query)
            citations_count = len(response.citations)
            for citation in response.citations:
                if not citation.url:
                    continue
                if Config.SONAR_USE_TRUSTED_DOMAINS and Config.TRUSTED_DOMAINS:
                    if not self._is_trusted_domain(citation.url, Config.TRUSTED_DOMAINS):
                        continue
                record = self._create_base_record(...)
                record["sonar_citations_count"] = citations_count
                record["sonar_model"] = self.sonar_model
                ...
```

在 `.env.example` 补充：

```bash
# Sonar 引用过滤
SONAR_USE_TRUSTED_DOMAINS=false
```

**Step 4: Run test to verify it passes**

Run: `python tests/scrapers/test_sonar_scraper.py`

Expected: PASS

**Step 5: Commit**

```bash
git add D:\Projects\FinNews\scrapers\sonar_scraper.py D:\Projects\FinNews\config\config.py D:\Projects\FinNews\.env.example D:\Projects\FinNews\tests\scrapers\test_sonar_scraper.py
git commit -m "补强 Sonar 引用过滤与元数据字段"
```

---

### Task 3: 运行快速测试与冒烟验证

**Files:**
- Test: `D:\Projects\FinNews\run_tests.py`

**Step 1: Run quick tests**

Run: `python run_tests.py --quick`

Expected: 通过或提示缺失依赖（若失败，先补齐依赖再重试）。

**Step 2: 手工冒烟验证（可选）**

Run: `python main.py`

Expected: 日志包含 Sonar 窗口统计与引用数量，且不影响其他数据源。

**Step 3: Commit**

```bash
git status
```

说明: 如果只有测试运行，无新增修改则无需提交。
