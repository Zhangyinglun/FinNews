"""
测试纯文本邮件生成流程（不发送邮件）
验证 main.py 中的纯文本邮件分支是否正常工作
"""

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import json
from pathlib import Path
from datetime import datetime
from config.config import Config
from analyzers.market_analyzer import MarketAnalyzer
from models.analysis import (
    MarketSignal,
    ComexSignal,
    ComexAlertLevel,
    AlertLevel,
    MacroBias,
)


def load_latest_raw_data():
    """加载最新的 raw 数据"""
    raw_dir = Path("outputs/raw")
    files = sorted(raw_dir.glob("raw_*.json"), reverse=True)
    if not files:
        raise FileNotFoundError("未找到 raw 数据文件")

    with open(files[0], "r", encoding="utf-8") as f:
        return json.load(f)


def create_mock_signal():
    """创建模拟市场信号"""
    return MarketSignal(
        vix_value=22.5,
        vix_prev_close=18.3,
        vix_change_percent=22.95,
        vix_alert_level=AlertLevel.CRITICAL,
        gold_price=2678.40,
        gold_change_percent=1.25,
        silver_price=30.85,
        silver_change_percent=2.17,
        dxy_value=107.25,
        dxy_change_percent=0.45,
        us10y_value=4.52,
        us10y_change_percent=3.2,
        macro_bias=MacroBias.NEUTRAL,
        sentiment_score=0.42,
        alert_messages=[
            "🔴 VIX 暴涨 22.95%，市场恐慌情绪急剧升温",
            "⚠️ VIX=22.5 超过警戒线 20.0",
        ],
        is_urgent=True,
    )


def create_mock_comex():
    """创建模拟 COMEX 信号"""
    now = datetime.now()
    return ComexSignal(
        silver_registered=104879944.89,
        silver_registered_million=104.88,
        silver_total=320450000.00,
        silver_alert_level=ComexAlertLevel.RED,
        silver_alert_message="白银注册库存 7 天内骤降 12.27%，跌破 1.1 亿盎司心理关口",
        silver_recommendation="密切监控挤仓风险，关注白银期货持仓量变化",
        silver_daily_change_pct=-1.85,
        silver_weekly_change_pct=-12.27,
        gold_registered=8234567.89,
        gold_registered_million=8.23,
        gold_total=25600000.00,
        gold_alert_level=ComexAlertLevel.SAFE,
        gold_alert_message="黄金注册库存小幅下降 2.63%，仍处健康区间",
        gold_recommendation="继续观察，暂无异常",
        gold_daily_change_pct=-0.42,
        gold_weekly_change_pct=-2.63,
        has_emergency=True,
        report_date=now,
        generated_at=now,
    )


def test_plain_email_generation():
    """测试纯文本邮件生成"""
    print("=" * 70)
    print("测试纯文本邮件生成流程")
    print("=" * 70)

    # 1. 加载数据
    print("\n[1/5] 加载原始新闻数据...")
    articles = load_latest_raw_data()
    print(f"   ✓ 加载了 {len(articles)} 篇新闻")

    # 2. 创建信号
    print("\n[2/5] 创建市场信号和 COMEX 信号...")
    market_signal = create_mock_signal()
    comex_signal = create_mock_comex()
    print(
        f"   ✓ 市场信号: VIX={market_signal.vix_value}, 警报={market_signal.vix_alert_level}"
    )
    print(
        f"   ✓ COMEX 信号: 白银={comex_signal.silver_alert_level}, 黄金={comex_signal.gold_alert_level}"
    )

    # 3. 组织数据
    print("\n[3/5] 组织多窗口数据...")
    analyzer = MarketAnalyzer()
    multi_window_data = analyzer.organize_data(articles, market_signal)
    print(f"   ✓ Flash: {len(multi_window_data.flash.news)} 条")
    print(f"   ✓ Cycle: {len(multi_window_data.cycle.news)} 条")
    print(f"   ✓ Trend: {len(multi_window_data.trend.news)} 条")

    # 4. 生成邮件内容
    print("\n[4/5] 生成纯文本邮件内容...")
    email_plain = analyzer.build_email_prompt(
        data=multi_window_data,
        signal=market_signal,
        comex_signal=comex_signal,
        mode=Config.EMAIL_FORMAT_MODE,
    )
    print(
        f"   ✓ 生成成功: {len(email_plain)} 字符, {email_plain.count(chr(10)) + 1} 行"
    )

    # 5. 生成邮件标题
    print("\n[5/5] 生成邮件标题...")
    tag = market_signal.get_email_subject_tag()
    summary = market_signal.get_signal_summary()
    date_str = datetime.now().strftime("%m/%d")
    email_subject = f"{tag} {date_str} {summary}"
    print(f"   ✓ {email_subject}")

    # 保存预览
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = Path(f"outputs/plain_email_test_{timestamp}.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"标题: {email_subject}\n")
        f.write("=" * 70 + "\n\n")
        f.write(email_plain)

    print(f"\n{'=' * 70}")
    print(f"✅ 测试完成！")
    print(f"预览文件: {output_path}")
    print("=" * 70)

    # 显示前 40 行
    lines = email_plain.split("\n")
    print("\n邮件内容预览（前 40 行）:")
    print("-" * 70)
    for i, line in enumerate(lines[:40], 1):
        print(f"{i:3d} | {line}")
    print("-" * 70)

    return True


if __name__ == "__main__":
    try:
        test_plain_email_generation()
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
