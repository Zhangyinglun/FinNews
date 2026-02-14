"""
测试邮件格式（包含 COMEX 数据）
手动构造包含 COMEX 信号的场景
"""

import sys

sys.path.insert(0, "D:\\Projects\\FinNews")

import json
from pathlib import Path
from datetime import datetime, timedelta
from models.analysis import (
    MarketSignal,
    ComexSignal,
    ComexAlertLevel,
    AlertLevel,
    MacroBias,
)
from analyzers.market_analyzer import MarketAnalyzer


def load_sample_articles():
    """加载示例新闻数据"""
    raw_file = Path("outputs/raw/raw_20260203_202100.json")
    with open(raw_file, "r", encoding="utf-8") as f:
        return json.load(f)


def create_mock_comex_signal() -> ComexSignal:
    """创建模拟的 COMEX 信号（紧急警报场景）"""
    now = datetime.now()

    # 白银：库存急剧下降，触发红色警报
    return ComexSignal(
        # 白银数据
        silver_registered=104879944.89,  # 约 1.05 亿盎司
        silver_registered_million=104.88,  # 1.0488 亿盎司
        silver_total=320450000.00,  # 总库存约 3.2 亿盎司
        silver_alert_level=ComexAlertLevel.RED,
        silver_alert_message="白银注册库存 7 天内骤降 12.27%，跌破 1.1 亿盎司心理关口",
        silver_recommendation="密切监控挤仓风险，关注白银期货持仓量变化",
        silver_daily_change_pct=-1.85,
        silver_weekly_change_pct=-12.27,
        # 黄金数据
        gold_registered=8234567.89,  # 约 823 万盎司
        gold_registered_million=8.23,  # 823 万盎司
        gold_total=25600000.00,  # 总库存约 2560 万盎司
        gold_alert_level=ComexAlertLevel.SAFE,
        gold_alert_message="黄金注册库存小幅下降 2.63%，仍处健康区间",
        gold_recommendation="继续观察，暂无异常",
        gold_daily_change_pct=-0.42,
        gold_weekly_change_pct=-2.63,
        # 整体状态
        has_emergency=True,
        report_date=now - timedelta(days=1),  # 昨日报告
        generated_at=now,
    )


def create_mock_market_signal(with_comex: bool = True) -> MarketSignal:
    """创建模拟的市场信号"""
    signal = MarketSignal(
        vix_value=22.5,
        vix_prev_close=18.3,
        vix_change_percent=22.95,  # VIX 暴涨
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
        sentiment_score=0.42,  # 偏乐观
        alert_messages=[
            "🔴 VIX 暴涨 22.95%，市场恐慌情绪急剧升温",
            "⚠️ VIX=22.5 超过警戒线 20.0",
        ],
        is_urgent=True,
    )

    return signal


def main():
    print("=" * 60)
    print("测试邮件格式（包含 COMEX 数据）")
    print("=" * 60)

    # 加载新闻数据
    articles = load_sample_articles()
    print(f"\n✅ 加载了 {len(articles)} 篇新闻")

    # 创建模拟信号
    signal = create_mock_market_signal(
        with_comex=False
    )  # MarketSignal 不包含 comex_signal
    comex_signal = create_mock_comex_signal()  # 单独创建 COMEX 信号

    print(f"✅ 创建了模拟市场信号")
    print(f"   - VIX 警报: {signal.vix_alert_level}")
    worst_level = comex_signal.get_worst_alert_level()
    print(f"   - COMEX 整体警报: {worst_level}")
    print(f"   - COMEX 白银警报: {comex_signal.silver_alert_level}")
    print(f"   - COMEX 黄金警报: {comex_signal.gold_alert_level}")

    # 生成邮件格式
    analyzer = MarketAnalyzer()

    # 先组织数据
    multi_window_data = analyzer.organize_data(articles, signal)

    # 生成邮件内容（传入 COMEX 信号）
    email_content = analyzer.build_email_prompt(
        data=multi_window_data, signal=signal, comex_signal=comex_signal, mode="full"
    )

    # 保存预览
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = Path(f"outputs/email_with_comex_{timestamp}.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(email_content)

    print(f"\n✅ 邮件预览已生成: {output_path}")
    print(f"   - 总字符数: {len(email_content):,}")
    print(f"   - 总行数: {email_content.count(chr(10)) + 1}")

    # 显示前 50 行预览
    lines = email_content.split("\n")
    print("\n" + "=" * 60)
    print("前 50 行预览:")
    print("=" * 60)
    for i, line in enumerate(lines[:50], 1):
        print(f"{i:3d} | {line}")

    print("\n" + "=" * 60)
    print(f"✅ 完整内容已保存到: {output_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
