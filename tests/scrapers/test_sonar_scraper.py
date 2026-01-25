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
