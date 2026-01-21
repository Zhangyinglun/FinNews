"""
测试 FRED 数据源
"""

import sys

sys.path.insert(0, "D:\\Projects\\FinNews")

from scrapers.fred_scraper import FREDScraper
from utils.logger import setup_logger
import json

# 初始化
setup_logger()
scraper = FREDScraper()

# 抓取数据
print("=" * 80)
print("正在抓取 FRED 经济数据...")
print("=" * 80)

data = scraper.run()

print(f"\n✅ 抓取完成！共获取 {len(data)} 条经济指标\n")

# 显示详细数据
print("📊 经济指标详情:")
for idx, item in enumerate(data, 1):
    print(f"\n【指标 {idx}】")
    print(f"名称: {item.get('indicator', 'N/A')}")
    print(f"代码: {item.get('series_id', 'N/A')}")
    print(f"最新值: {item.get('value', 'N/A')}")

    change = item.get("change")
    change_pct = item.get("change_pct")
    if change is not None and change_pct is not None:
        direction = "📈" if change > 0 else "📉" if change < 0 else "➡️"
        print(f"变化: {direction} {change:+.4f} ({change_pct:+.2f}%)")

    print(f"数据日期: {item.get('timestamp', 'N/A')}")
    print(f"抓取时间: {item.get('fetched_at', 'N/A')}")
    print("-" * 80)

# 保存为 JSON 方便查看
output_file = "D:\\Projects\\FinNews\\test_fred_output.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2, default=str)

print(f"\n💾 详细数据已保存到: {output_file}")
