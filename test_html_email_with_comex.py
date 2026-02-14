"""
测试 HTML 邮件生成和 COMEX 折线图
验证修改后 HTML 模式是否正常工作
"""

import sys

sys.path.insert(0, "D:\\Projects\\FinNews")

from config.config import Config
from utils.digest_controller import DigestController
from models.market_data import (
    MultiWindowData,
    FlashWindowData,
    CycleWindowData,
    TrendWindowData,
    NewsItem,
)
from models.analysis import (
    MarketSignal,
    ComexSignal,
    ComexAlertLevel,
    AlertLevel,
    MacroBias,
)
from datetime import datetime
import json

print("=" * 60)
print("HTML 邮件生成测试（含 COMEX 折线图）")
print("=" * 60)

# 1. 验证配置
print("\n[1/6] 验证配置...")
print(f"   EMAIL_CONTENT_TYPE: {Config.EMAIL_CONTENT_TYPE}")
assert Config.EMAIL_CONTENT_TYPE == "html", (
    f"配置错误！当前值: {Config.EMAIL_CONTENT_TYPE}"
)
print("   ✓ 配置正确：html 模式")

# 2. 创建测试数据
print("\n[2/6] 创建测试数据...")

# MarketSignal
market_signal = MarketSignal(
    vix_value=22.5,
    vix_prev_close=21.0,
    vix_change_percent=7.14,
    vix_alert_level=AlertLevel.WARNING,
    dxy_value=105.2,
    dxy_change_percent=0.5,
    us10y_value=4.25,
    us10y_change_percent=0.1,
    gold_price=2650.0,
    gold_change_percent=1.25,
    silver_price=31.5,
    silver_change_percent=2.1,
    macro_bias=MacroBias.BULLISH,
    sentiment_score=0.6,
    is_urgent=False,
)

# COMEX Signal（包含模拟的 base64 图表）
# 实际运行时这些 base64 数据由 ComexChartGenerator 生成
comex_signal = ComexSignal(
    silver_registered=105000000,
    silver_registered_million=105.0,
    silver_total=280000000,
    silver_alert_level=ComexAlertLevel.YELLOW,
    silver_alert_message="警戒线",
    silver_recommendation="密切关注白银库存变化",
    silver_daily_change_pct=-1.2,
    silver_weekly_change_pct=-3.5,
    gold_registered=8500000,
    gold_registered_million=8.5,
    gold_total=25000000,
    gold_alert_level=ComexAlertLevel.SAFE,
    gold_alert_message="安全",
    gold_recommendation="",
    gold_daily_change_pct=0.2,
    gold_weekly_change_pct=1.0,
    # 模拟 base64 图表数据（实际应该是真实的 PNG base64）
    silver_chart_base64="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
    gold_chart_base64="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
    report_date=datetime.now(),
)

# MultiWindowData（简化版）
flash_data = FlashWindowData(
    vix_value=22.5,
    vix_change_percent=7.14,
    gold_price=2650.0,
    gold_change_percent=1.25,
    silver_price=31.5,
    silver_change_percent=2.1,
    news=[
        NewsItem(
            title="美联储维持利率不变",
            summary="联邦公开市场委员会决定维持5.25%-5.5%利率区间",
            source="Reuters",
            impact_tag="#Neutral",
            relevance_score=0.9,
        ),
        NewsItem(
            title="黄金突破历史新高",
            summary="国际金价突破2650美元，创历史新高",
            source="Bloomberg",
            impact_tag="#Bullish",
            relevance_score=0.95,
        ),
    ],
)

cycle_data = CycleWindowData(
    cpi_actual=3.2,
    pce_actual=2.8,
    nfp_actual=250000,
    fed_rate=5.5,
    news=[],
)

trend_data = TrendWindowData(
    central_bank_buying="各国央行持续净购金",
    etf_flows="黄金ETF流入20吨",
    news=[],
)

multi_window_data = MultiWindowData(
    flash=flash_data,
    cycle=cycle_data,
    trend=trend_data,
)

print("   ✓ 测试数据创建完成")

# 3. 模拟 LLM 返回数据
print("\n[3/6] 模拟 LLM 返回数据...")
digest_data = {
    "subject": "【市场警戒】02/14 VIX 22.5 ⚠️ | 黄金创新高 +1.25%",
    "key_news": [
        {
            "title": "黄金突破历史新高",
            "summary": "国际金价突破2650美元",
            "source": "Bloomberg",
        },
        {
            "title": "美联储维持利率不变",
            "summary": "维持5.25%-5.5%利率区间",
            "source": "Reuters",
        },
    ],
    "other_news": [],
    "analysis": {
        "flash_analysis": "VIX指数上涨7.14%，市场恐慌情绪升温",
        "cycle_analysis": "CPI数据符合预期，通胀压力缓解",
        "trend_analysis": "央行持续购金，长期利好黄金",
        "conclusion": "短期市场波动加大，黄金避险需求上升",
    },
}
print("   ✓ LLM 数据模拟完成")

# 4. 渲染 HTML 邮件
print("\n[4/6] 渲染 HTML 邮件...")
digest_controller = DigestController()

try:
    email_html, email_images = digest_controller.render_email_html(
        digest_data=digest_data,
        signal=market_signal,
        data=multi_window_data,
        comex_signal=comex_signal,
    )
    print(f"   ✓ HTML 渲染成功: {len(email_html)} 字符")
    print(f"   ✓ 图片数量: {len(email_images)} 张")

    # 检查图片
    if email_images:
        print("\n   图片列表:")
        for cid, base64_data in email_images.items():
            print(f"     - {cid}: {len(base64_data)} 字节 base64")
    else:
        print("   ⚠️ 警告: 没有图片数据！")

except Exception as e:
    print(f"   ✗ HTML 渲染失败: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)

# 5. 验证 COMEX 区块
print("\n[5/6] 验证 COMEX 区块...")
if "COMEX" in email_html or "comex" in email_html.lower():
    print("   ✓ COMEX 区块存在")
else:
    print("   ✗ 警告: 未找到 COMEX 区块！")

if "silver_chart" in email_html or "gold_chart" in email_html:
    print("   ✓ COMEX 图表引用存在")
else:
    print("   ✗ 警告: 未找到 COMEX 图表引用！")

if "cid:silver_chart" in email_html or "cid:gold_chart" in email_html:
    print("   ✓ CID 图片引用正确")
else:
    print("   ✗ 警告: CID 引用格式错误！")

# 6. 保存预览
print("\n[6/6] 保存预览文件...")
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_file = f"outputs/html_email_test_{timestamp}.html"

with open(output_file, "w", encoding="utf-8") as f:
    f.write(email_html)

print(f"   ✓ HTML 预览已保存: {output_file}")

# 保存图片信息
if email_images:
    image_info_file = f"outputs/html_email_images_{timestamp}.json"
    image_info = {cid: f"{len(data)} bytes" for cid, data in email_images.items()}
    with open(image_info_file, "w", encoding="utf-8") as f:
        json.dump(image_info, f, indent=2, ensure_ascii=False)
    print(f"   ✓ 图片信息已保存: {image_info_file}")

print("\n" + "=" * 60)
print("✅ 测试完成！")
print("=" * 60)
print(f"\n请在浏览器中打开查看: {output_file}")
print("\n注意事项:")
print("1. 图片使用 cid: 协议引用，在浏览器中可能不显示")
print("2. 在真实邮件客户端中图片会正常显示")
print("3. 如需真实的 COMEX 折线图，需运行完整流程生成 comex_history.json")
