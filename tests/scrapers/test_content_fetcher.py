"""
测试 ContentFetcher 完整内容抓取
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scrapers.content_fetcher import ContentFetcher
from utils.logger import setup_logger
import json


def test_content_fetcher():
    """测试 ContentFetcher 完整内容抓取"""
    # 初始化
    setup_logger()

    try:
        fetcher = ContentFetcher(max_retries=3, timeout=15)
    except ImportError as e:
        print(f"⚠️ ContentFetcher 不可用: {e}")
        print("请运行: pip install requests beautifulsoup4 lxml")
        return

    # 测试URL列表
    test_urls = [
        "https://www.kitco.com/news/article/2024-01-15/gold-price-rises-as-traders-assess-fed-outlook",
        "https://www.reuters.com/markets/commodities/gold-prices-rise-2024-01-15/",
        "https://www.fxstreet.com/news/gold-price-forecast-xau-usd-holds-gains-above-2050-20240115",
    ]

    print("=" * 80)
    print("正在测试 ContentFetcher...")
    print("=" * 80)

    results = []
    for idx, url in enumerate(test_urls, 1):
        print(f"\n【测试 {idx}/{len(test_urls)}】")
        print(f"URL: {url}")

        content = fetcher.fetch_full_content(url)

        result = {
            "url": url,
            "success": content is not None,
            "content_length": len(content) if content else 0,
            "preview": content[:200] if content else None,
        }
        results.append(result)

        if content:
            print(f"✅ 成功 - 获取 {len(content)} 字符")
            print(f"预览: {content[:200]}...")
        else:
            print(f"❌ 失败 - 无法获取内容")

        print("-" * 80)

    # 测试批量处理
    print("\n" + "=" * 80)
    print("测试批量enrichment...")
    print("=" * 80)

    sample_articles = [
        {
            "title": "Gold prices rise on Fed outlook",
            "summary": "Gold prices rose as traders assess Federal Reserve policy.",
            "url": test_urls[0],
            "source": "Kitco",
        },
        {
            "title": "Test article without URL",
            "summary": "This article has no URL",
            "source": "Test",
        },
    ]

    enriched = fetcher.enrich_articles(sample_articles)

    print(f"\n✅ 批量处理完成！处理 {len(enriched)} 篇文章")

    for idx, article in enumerate(enriched, 1):
        print(f"\n【文章 {idx}】")
        print(f"标题: {article.get('title')}")
        print(
            f"是否有完整内容: {'full_content' in article and article.get('content_length', 0) > 0}"
        )
        print(f"内容长度: {article.get('content_length', 0)} 字符")

    # 保存结果
    output_file = str(Path(__file__).resolve().parent / "output_content_fetcher.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(
            {"single_tests": results, "enriched_articles": enriched},
            f,
            ensure_ascii=False,
            indent=2,
            default=str,
        )

    print(f"\n💾 详细数据已保存到: {output_file}")

    # 断言基本验证
    success_count = sum(1 for r in results if r["success"])
    print(f"\n📊 成功率: {success_count}/{len(results)}")


if __name__ == "__main__":
    test_content_fetcher()
