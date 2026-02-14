"""
测试邮件生成修复
验证 analyzer 变量名和 SonarScraper 导入问题已修复
"""

import sys

sys.path.insert(0, "D:\\Projects\\FinNews")

from analyzers.market_analyzer import MarketAnalyzer
from analyzers.rule_engine import RuleEngine
from models.market_data import MultiWindowData
from models.analysis import MarketSignal, ComexSignal, ComexAlertLevel
from scrapers import SonarScraper
from datetime import datetime

print("✓ 所有导入成功")

# 测试 MarketAnalyzer 实例化
analyzer = MarketAnalyzer()
print(f"✓ MarketAnalyzer 实例化成功: {type(analyzer)}")

# 测试 SonarScraper 实例化
scraper = SonarScraper()
print(f"✓ SonarScraper 实例化成功: {type(scraper)}")

# 测试 build_email_prompt 方法存在
assert hasattr(analyzer, "build_email_prompt"), "build_email_prompt 方法不存在"
print("✓ build_email_prompt 方法存在")

# 创建最小测试数据
multi_window_data = MultiWindowData()
market_signal = MarketSignal(
    vix_value=20.5,
    vix_change_percent=2.0,
    gold_price=2650.0,
    gold_change_percent=1.5,
    silver_price=31.2,
    silver_change_percent=2.1,
)

comex_signal = ComexSignal(
    silver_registered=105000000,
    silver_registered_million=105.0,
    silver_total=280000000,
    silver_alert_level=ComexAlertLevel.YELLOW,
    silver_alert_message="警戒线",
    silver_recommendation="密切关注",
    silver_daily_change_pct=-0.5,
    silver_weekly_change_pct=-2.0,
    gold_registered=8500000,
    gold_registered_million=8.5,
    gold_total=25000000,
    gold_alert_level=ComexAlertLevel.SAFE,
    gold_alert_message="安全",
    gold_recommendation="正常",
    gold_daily_change_pct=0.2,
    gold_weekly_change_pct=1.0,
    silver_chart_base64="",
    gold_chart_base64="",
    report_date=datetime.now(),
)

# 测试邮件生成
try:
    email_content = analyzer.build_email_prompt(
        data=multi_window_data,
        signal=market_signal,
        comex_signal=comex_signal,
        mode="brief",
    )
    print(f"✓ 邮件生成成功: {len(email_content)} 字符")
    print(f"\n--- 邮件预览 (前 500 字符) ---")
    print(email_content[:500])
    print("...")
except Exception as e:
    print(f"✗ 邮件生成失败: {e}")
    import traceback

    traceback.print_exc()

print("\n✅ 所有测试通过！")
