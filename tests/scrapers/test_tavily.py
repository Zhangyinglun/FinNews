"""
测试 Tavily 数据源
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scrapers.tavily_scraper import TavilyScraper
from utils.logger import setup_logger
import json


def test_tavily_scraper():
    """测试 Tavily Scraper 数据抓取"""
    # 初始化
    setup_logger()
    scraper = TavilyScraper()

    # 抓取数据
    print("=" * 80)
    print("正在抓取 Tavily 数据...")
    print("=" * 80)

    data = scraper.run()

    print(f"\n✅ 抓取完成！共获取 {len(data)} 条记录\n")

    # 显示详细数据
    for idx, item in enumerate(data, 1):
        print(f"【记录 {idx}】")
        print(f"标题: {item.get('title', 'N/A')}")
        print(f"摘要: {item.get('summary', 'N/A')[:150]}...")
        print(f"URL: {item.get('url', 'N/A')}")
        print(f"时间: {item.get('timestamp', 'N/A')}")
        print(f"来源: {item.get('source', 'N/A')}")
        print(f"相关性评分: {item.get('relevance_score', 'N/A')}")
        print("-" * 80)

    # 保存为 JSON 方便查看
    output_file = str(Path(__file__).resolve().parent / "output_tavily.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n💾 详细数据已保存到: {output_file}")

    # 断言基本验证
    if len(data) == 0 and getattr(scraper, "quota_exceeded", False):
        print("⚠️ Tavily API 用量已达上限，本次跳过断言")
        return
    assert len(data) > 0, "应该获取到至少一条数据"
    assert "title" in data[0], "记录应该包含title字段"
    assert "source" in data[0], "记录应该包含source字段"


if __name__ == "__main__":
    test_tavily_scraper()
