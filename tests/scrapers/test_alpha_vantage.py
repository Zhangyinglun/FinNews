"""
测试 Alpha Vantage 数据源
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scrapers.alpha_vantage_scraper import AlphaVantageScraper
from utils.logger import setup_logger
import json


def test_alpha_vantage_scraper():
    """测试 Alpha Vantage Scraper 数据抓取"""
    # 初始化
    setup_logger()

    try:
        scraper = AlphaVantageScraper()
    except (ImportError, ValueError) as e:
        print(f"⚠️ Alpha Vantage 不可用: {e}")
        print("跳过测试")
        return

    # 抓取数据
    print("=" * 80)
    print("正在抓取 Alpha Vantage 数据...")
    print("=" * 80)

    data = scraper.run()

    print(f"\n✅ 抓取完成！共获取 {len(data)} 条记录\n")

    # 显示详细数据
    if data:
        print("📊 数据详情:")
        for idx, item in enumerate(data, 1):
            print(f"\n【记录 {idx}】")
            print(f"货币对: {item.get('pair', 'N/A')}")
            print(f"收盘价: {item.get('close', 'N/A')}")
            print(f"数据类型: {item.get('type', 'N/A')}")
            print(f"数据时间: {item.get('timestamp', 'N/A')}")
            print(f"抓取时间: {item.get('fetched_at', 'N/A')}")
            print("-" * 80)

        # 保存为 JSON 方便查看
        output_file = (
            "str(Path(__file__).resolve().parent / 'output_alpha_vantage.json')"
        )
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

        print(f"\n💾 详细数据已保存到: {output_file}")

        # 断言基本验证
        assert len(data) > 0, "应该获取到至少一条数据"
        assert "pair" in data[0], "记录应该包含pair字段"
        assert "type" in data[0], "记录应该包含type字段"
    else:
        print("⚠️ 未获取到数据（可能是API配额已用完）")


if __name__ == "__main__":
    test_alpha_vantage_scraper()
