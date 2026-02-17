"""
测试 COMEX 库存数据爬虫和查询函数
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scrapers.comex_scraper import ComexScraper
from utils.comex_query import get_comex_snapshot, get_comex_summary
from analyzers.rule_engine import RuleEngine
from utils.logger import setup_logger
import json

# 初始化
setup_logger()

print("=" * 80)
print("COMEX 库存监控测试")
print("=" * 80)

# ==========================================
# 测试1: ComexScraper 直接抓取
# ==========================================
print("\n【测试1】ComexScraper 直接抓取\n")

try:
    scraper = ComexScraper()
    data = scraper.run()

    print(f"✅ 抓取完成！共获取 {len(data)} 条记录\n")

    for item in data:
        metal = item.get("metal", "unknown")
        registered = item.get("registered_million")
        total = item.get("total_million")
        report_date = item.get("report_date")
        weekly_change = item.get("registered_weekly_change_pct")

        print(f"【{metal.upper()}】")
        print(f"  报告日期: {report_date}")
        print(f"  Registered: {registered}M oz")
        print(f"  Total: {total}M oz")
        if weekly_change is not None:
            print(f"  周变化: {weekly_change:+.1f}%")
        print()

except Exception as e:
    print(f"❌ ComexScraper 测试失败: {e}")
    import traceback

    traceback.print_exc()

# ==========================================
# 测试2: RuleEngine COMEX分析
# ==========================================
print("\n" + "=" * 80)
print("【测试2】RuleEngine COMEX分析\n")

try:
    rule_engine = RuleEngine()
    comex_signal = rule_engine.analyze_comex(data)

    print("白银分析结果:")
    print(f"  Registered: {comex_signal.silver_registered_million}M oz")
    print(f"  预警级别: {comex_signal.silver_alert_level.value}")
    print(f"  警报消息: {comex_signal.silver_alert_message}")
    print(f"  投资建议: {comex_signal.silver_recommendation}")
    print()

    print("黄金分析结果:")
    print(f"  Registered: {comex_signal.gold_registered_million}M oz")
    print(f"  预警级别: {comex_signal.gold_alert_level.value}")
    print(f"  警报消息: {comex_signal.gold_alert_message}")
    print(f"  投资建议: {comex_signal.gold_recommendation}")
    print()

    print(f"最高预警级别: {comex_signal.get_worst_alert_level().value}")
    print(f"预警Emoji: {comex_signal.get_alert_emoji()}")
    print(f"紧急状态: {'是' if comex_signal.has_emergency else '否'}")

except Exception as e:
    print(f"❌ RuleEngine 测试失败: {e}")
    import traceback

    traceback.print_exc()

# ==========================================
# 测试3: get_comex_snapshot 便捷函数
# ==========================================
print("\n" + "=" * 80)
print("【测试3】get_comex_snapshot 便捷函数\n")

try:
    silver_snapshot = get_comex_snapshot("silver")

    print("白银快照:")
    print(f"  success: {silver_snapshot.get('success')}")
    print(f"  registered: {silver_snapshot.get('registered_million')}M oz")
    print(f"  alert_level: {silver_snapshot.get('alert_level')}")
    print(f"  alert_message: {silver_snapshot.get('alert_message')}")
    print(f"  recommendation: {silver_snapshot.get('recommendation')}")
    if silver_snapshot.get("weekly_change_message"):
        print(f"  weekly_change: {silver_snapshot.get('weekly_change_message')}")
    print()

    gold_snapshot = get_comex_snapshot("gold")

    print("黄金快照:")
    print(f"  success: {gold_snapshot.get('success')}")
    print(f"  registered: {gold_snapshot.get('registered_million')}M oz")
    print(f"  alert_level: {gold_snapshot.get('alert_level')}")
    print(f"  alert_message: {gold_snapshot.get('alert_message')}")
    print(f"  recommendation: {gold_snapshot.get('recommendation')}")

except Exception as e:
    print(f"❌ get_comex_snapshot 测试失败: {e}")
    import traceback

    traceback.print_exc()

# ==========================================
# 测试4: get_comex_summary 摘要函数
# ==========================================
print("\n" + "=" * 80)
print("【测试4】get_comex_summary 摘要函数\n")

try:
    summary = get_comex_summary()
    print(summary)

except Exception as e:
    print(f"❌ get_comex_summary 测试失败: {e}")
    import traceback

    traceback.print_exc()

# ==========================================
# 保存测试结果
# ==========================================
print("\n" + "=" * 80)
print("保存测试结果\n")

output_file = Path(__file__).resolve().parent.parent.parent / "test_comex_output.json"
try:
    output_data = {
        "scraper_data": data,
        "silver_snapshot": get_comex_snapshot("silver"),
        "gold_snapshot": get_comex_snapshot("gold"),
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2, default=str)

    print(f"💾 测试结果已保存到: {output_file}")

except Exception as e:
    print(f"❌ 保存失败: {e}")

print("\n" + "=" * 80)
print("测试完成!")
print("=" * 80)
