"""
集成测试 - 测试完整的数据管道
"""

import sys

sys.path.insert(0, "D:\\Projects\\FinNews")

from scrapers import YFinanceScraper, FREDScraper
from processors import DataCleaner, Deduplicator
from storage import JSONStorage
from utils.logger import setup_logger
from datetime import datetime


def test_full_pipeline():
    """测试完整的数据管道流程"""
    setup_logger()

    print("=" * 80)
    print("开始集成测试 - 完整数据管道")
    print("=" * 80)

    # 1. 数据抓取
    print("\n【步骤 1/5】数据抓取...")
    print("-" * 80)

    scrapers = []

    # 使用YFinance和FRED作为测试数据源（不需要API密钥）
    try:
        scrapers.append(YFinanceScraper())
        print("✅ YFinanceScraper 初始化成功")
    except Exception as e:
        print(f"⚠️ YFinanceScraper 初始化失败: {e}")

    try:
        scrapers.append(FREDScraper())
        print("✅ FREDScraper 初始化成功")
    except Exception as e:
        print(f"⚠️ FREDScraper 初始化失败: {e}")

    if not scrapers:
        print("❌ 没有可用的数据源，跳过测试")
        return

    all_data = []
    for scraper in scrapers:
        try:
            data = scraper.run()
            all_data.extend(data)
            print(f"✅ {scraper.name}: 获取 {len(data)} 条数据")
        except Exception as e:
            print(f"⚠️ {scraper.name}: 抓取失败 - {e}")

    print(f"\n总计抓取: {len(all_data)} 条原始数据")

    if len(all_data) == 0:
        print("❌ 没有抓取到任何数据，测试终止")
        return

    # 2. 数据清洗
    print("\n【步骤 2/5】数据清洗...")
    print("-" * 80)

    cleaner = DataCleaner()
    cleaned_data = cleaner.clean(all_data)

    print(f"✅ 清洗完成: {len(all_data)} -> {len(cleaned_data)} 条")
    print(f"过滤掉: {len(all_data) - len(cleaned_data)} 条")

    # 3. 数据去重
    print("\n【步骤 3/5】数据去重...")
    print("-" * 80)

    deduplicator = Deduplicator()
    unique_data = deduplicator.deduplicate(cleaned_data)

    print(f"✅ 去重完成: {len(cleaned_data)} -> {len(unique_data)} 条")
    print(f"重复数据: {len(cleaned_data) - len(unique_data)} 条")

    # 4. 数据统计
    print("\n【步骤 4/5】数据统计...")
    print("-" * 80)

    # 按类型分组
    news_items = [
        r
        for r in unique_data
        if r.get("type") not in ["price_data", "economic_data", "fx_data"]
    ]
    price_items = [r for r in unique_data if r.get("type") == "price_data"]
    econ_items = [r for r in unique_data if r.get("type") == "economic_data"]

    print(f"新闻数据: {len(news_items)} 条")
    print(f"价格数据: {len(price_items)} 条")
    print(f"经济数据: {len(econ_items)} 条")

    # 按来源统计
    sources = {}
    for item in unique_data:
        source = item.get("source", "Unknown")
        sources[source] = sources.get(source, 0) + 1

    print(f"\n按来源统计:")
    for source, count in sorted(sources.items(), key=lambda x: x[1], reverse=True):
        print(f"  {source}: {count} 条")

    # 5. 数据存储
    print("\n【步骤 5/5】数据存储...")
    print("-" * 80)

    storage = JSONStorage()

    # 保存原始数据
    raw_filename = (
        f"integration_test_raw_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    storage.save_raw(all_data, filename=raw_filename)
    print(f"✅ 原始数据已保存: {raw_filename}")

    # 保存处理后数据
    processed_filename = (
        f"integration_test_processed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    )
    storage.save_processed(unique_data, filename=processed_filename)
    print(f"✅ 处理数据已保存: {processed_filename}")

    # 6. 最终验证
    print("\n【最终验证】")
    print("=" * 80)

    # 验证文件存在
    raw_file = storage.raw_dir / raw_filename
    processed_file = storage.processed_dir / processed_filename

    assert raw_file.exists(), "原始数据文件应该存在"
    assert processed_file.exists(), "处理数据文件应该存在"

    print("✅ 文件存在性验证通过")

    # 验证数据量
    assert len(unique_data) > 0, "应该有最终数据"
    assert len(unique_data) <= len(all_data), "最终数据不应该多于原始数据"

    print("✅ 数据量验证通过")

    # 验证数据质量
    for item in unique_data:
        assert "source" in item, "每条记录应该有source字段"
        assert "timestamp" in item, "每条记录应该有timestamp字段"

    print("✅ 数据质量验证通过")

    print("\n" + "=" * 80)
    print("🎉 集成测试全部通过！")
    print("=" * 80)

    print(f"\n测试摘要:")
    print(f"  原始数据: {len(all_data)} 条")
    print(
        f"  清洗后: {len(cleaned_data)} 条 (过滤 {len(all_data) - len(cleaned_data)} 条)"
    )
    print(
        f"  去重后: {len(unique_data)} 条 (去重 {len(cleaned_data) - len(unique_data)} 条)"
    )
    print(f"  最终保留率: {len(unique_data) / len(all_data) * 100:.1f}%")


if __name__ == "__main__":
    test_full_pipeline()
