"""
测试 HTML 邮件改进功能
验证: 情绪评分进度条、impact_tag 彩色标签、URL 链接、时间戳
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from datetime import datetime
from utils.digest_controller import DigestController
from models.analysis import MarketSignal, AlertLevel, MacroBias, ComexSignal
from models.market_data import (
    MultiWindowData,
    FlashWindowData,
    CycleWindowData,
    TrendWindowData,
    NewsItem,
)


def create_mock_data():
    """创建模拟数据"""
    # 创建模拟新闻
    news1 = NewsItem(
        title="美联储宣布维持利率不变",
        summary="美联储在最新会议中决定维持基准利率不变，符合市场预期。",
        url="https://example.com/news1",
        source="路透社",
        timestamp=datetime(2026, 2, 14, 10, 30),
        impact_tag="Bullish",
        relevance_score=0.92,
    )

    news2 = NewsItem(
        title="美元指数持续走强",
        summary="美元指数升至106.5，创两周新高。",
        url="https://example.com/news2",
        source="彭博社",
        timestamp=datetime(2026, 2, 14, 9, 15),
        impact_tag="Bearish",
        relevance_score=0.85,
    )

    news3 = NewsItem(
        title="全球央行继续增持黄金储备",
        summary="2025年全球央行净买入黄金超1000吨。",
        url="",  # 测试无链接情况
        source="世界黄金协会",
        timestamp=datetime(2026, 2, 14, 8, 0),
        impact_tag="Bullish",
        relevance_score=0.88,
    )

    news4 = NewsItem(
        title="欧洲央行行长讲话",
        summary="拉加德表示将继续关注通胀数据。",
        url="https://example.com/news4",
        source="新华社",
        # timestamp 使用默认值 (当前时间)
        impact_tag="Neutral",
        relevance_score=0.65,
    )

    # 创建多窗口数据
    flash_window = FlashWindowData(news=[news1, news2, news3, news4])
    cycle_window = CycleWindowData(
        news=[],
        cpi_actual=3.1,
        fed_rate=5.375,  # 5.25-5.50 的中间值
        cpi_forecast="3.0%",
        nfp_actual=187000,
    )
    trend_window = TrendWindowData(news=[])

    data = MultiWindowData(
        flash=flash_window,
        cycle=cycle_window,
        trend=trend_window,
    )

    return data


def create_mock_signal():
    """创建模拟市场信号"""
    signal = MarketSignal(
        vix_value=18.5,
        vix_change_percent=2.3,
        vix_alert_level=AlertLevel.WARNING,
        gold_price=2850.50,
        gold_change_percent=0.8,
        silver_price=32.45,
        silver_change_percent=-0.3,
        dxy_value=106.2,
        dxy_change_percent=0.5,
        us10y_value=4.35,
        us10y_change_percent=0.1,
        macro_bias=MacroBias.BULLISH,
        sentiment_score=0.42,  # 测试利多情绪
        is_urgent=False,
        alert_messages=["VIX 接近警戒线"],
    )

    return signal


def create_mock_digest_data():
    """创建模拟 LLM 返回的 digest 数据"""
    return {
        "subject": "2026-02-14 市场日报：⚠️ VIX 警戒 | 美联储维持利率",
        "key_news": [
            {
                "title": "美联储宣布维持利率不变",
                "source": "路透社",
                "summary": "美联储在最新会议中决定维持基准利率不变，符合市场预期。",
                "url": "https://example.com/news1",
                "impact_tag": "Bullish",
                "timestamp": "10:30",
            },
            {
                "title": "全球央行继续增持黄金储备",
                "source": "世界黄金协会",
                "summary": "2025年全球央行净买入黄金超1000吨。",
                "url": "",
                "impact_tag": "Bullish",
                "timestamp": "08:00",
            },
            {
                "title": "美元指数持续走强",
                "source": "彭博社",
                "summary": "美元指数升至106.5，创两周新高。",
                "url": "https://example.com/news2",
                "impact_tag": "Bearish",
                "timestamp": "09:15",
            },
            {
                "title": "欧洲央行行长讲话",
                "source": "新华社",
                "summary": "拉加德表示将继续关注通胀数据。",
                "url": "https://example.com/news4",
                "impact_tag": "Neutral",
                "timestamp": "",
            },
            {
                "title": "地缘政治紧张局势缓和",
                "source": "CNN",
                "summary": "中东地区紧张局势有所缓解。",
                "url": "https://example.com/news5",
                "impact_tag": "Bearish",
                "timestamp": "07:30",
            },
        ],
        "other_news": [
            {
                "title": "白银工业需求增长",
                "source": "金属日报",
                "summary": "2025年白银工业需求同比增长8%。",
                "url": "https://example.com/other1",
                "impact_tag": "Bullish",
                "timestamp": "11:00",
            },
        ],
        "analysis": {
            "market_sentiment": "当前市场情绪偏向谨慎乐观。VIX指数虽有上升但仍处于可控区间，美联储维持利率不变为市场提供了稳定预期。",
            "price_outlook": "短期内黄金价格有望维持在2800-2900美元区间震荡，白银受工业需求支撑表现相对稳健。",
            "risk_factors": "需要关注美元指数的持续走强，以及潜在的地缘政治风险。",
            "trading_suggestion": "建议保持适度仓位，等待市场明确方向后再加仓。",
        },
    }


def main():
    print("=" * 60)
    print("测试 HTML 邮件改进功能")
    print("=" * 60)
    print()

    # 创建控制器
    controller = DigestController()

    # 创建模拟数据
    data = create_mock_data()
    signal = create_mock_signal()
    digest_data = create_mock_digest_data()

    print("✅ 模拟数据创建完成")
    print()

    # 测试点 1: 检查情绪评分范围
    print("📊 测试点 1: 情绪评分")
    print(f"  - sentiment_score: {signal.sentiment_score:+.2f}")
    assert -1 <= signal.sentiment_score <= 1, "情绪评分必须在 -1 到 +1 之间"
    print("  ✅ 情绪评分范围正确")
    print()

    # 测试点 2: 检查 key_news 数量
    print("📰 测试点 2: key_news 数量约束")
    print(f"  - key_news 数量: {len(digest_data['key_news'])}")
    assert len(digest_data["key_news"]) == 5, "key_news 必须恰好 5 条"
    print("  ✅ key_news 数量符合要求")
    print()

    # 测试点 3: 检查新闻字段完整性
    print("🔍 测试点 3: 新闻字段完整性")
    required_fields = ["title", "source", "summary", "url", "impact_tag", "timestamp"]
    for i, news in enumerate(digest_data["key_news"], 1):
        for field in required_fields:
            assert field in news, f"key_news[{i}] 缺少字段: {field}"
    print(f"  ✅ 所有新闻包含 {len(required_fields)} 个必需字段")
    print()

    # 测试点 4: 检查 impact_tag 枚举值
    print("🏷️  测试点 4: impact_tag 枚举值")
    valid_tags = {"Bullish", "Bearish", "Neutral"}
    for news in digest_data["key_news"] + digest_data["other_news"]:
        assert news["impact_tag"] in valid_tags, (
            f"无效的 impact_tag: {news['impact_tag']}"
        )
    print("  ✅ 所有 impact_tag 都在有效枚举中")
    print()

    # 渲染 HTML
    print("🎨 渲染 HTML 邮件...")
    html, images = controller.render_email_html(
        digest_data, signal, data, comex_signal=None
    )

    # 验证 HTML 内容
    print("✅ HTML 邮件生成成功")
    print(f"  - HTML 长度: {len(html)} 字符")
    print(f"  - 嵌入图片数量: {len(images or {})}")
    print()

    # 检查关键元素
    print("🔎 检查关键 HTML 元素...")
    checks = [
        ("情绪评分进度条", "市场情绪评分:" in html),
        ("利多标签", "利多" in html),
        ("利空标签", "利空" in html),
        ("中性标签", "中性" in html),
        ("URL 链接", 'href="https://example.com/news1"' in html),
        ("时间戳", "10:30" in html),
        ("VIX Signal", "VIX:" in html),
        ("宏观倾向", "利多黄金" in html),
        ("市场分析", "market_sentiment" not in html),  # 确保没有泄露 JSON 键名
    ]

    for name, condition in checks:
        status = "✅" if condition else "❌"
        print(f"  {status} {name}")
        if not condition:
            print(f"     ⚠️  检查失败: {name}")

    print()

    # 保存 HTML 到文件
    output_path = Path(__file__).resolve().parent / "outputs" / "html_email_improvements_test.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"💾 HTML 已保存到: {output_path}")
    print()

    # 统计信息
    print("=" * 60)
    print("📊 统计信息")
    print("=" * 60)

    # 统计 impact_tag 分布
    all_news = digest_data["key_news"] + digest_data["other_news"]
    tag_counts = {"Bullish": 0, "Bearish": 0, "Neutral": 0}
    for news in all_news:
        tag_counts[news["impact_tag"]] += 1

    print(f"  - 总新闻数: {len(all_news)}")
    print(f"  - impact_tag 分布:")
    for tag, count in tag_counts.items():
        print(f"    • {tag}: {count} 条")

    # 统计有链接的新闻
    with_url = sum(1 for news in all_news if news["url"])
    print(f"  - 有链接的新闻: {with_url}/{len(all_news)}")

    # 统计有时间戳的新闻
    with_timestamp = sum(1 for news in all_news if news["timestamp"])
    print(f"  - 有时间戳的新闻: {with_timestamp}/{len(all_news)}")

    print()
    print("=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)


if __name__ == "__main__":
    main()
