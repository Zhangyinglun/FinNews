"""Standalone test: OpenRouter digest generation with new 4-section format.

Prereqs:
- Set OPENROUTER_API_KEY in .env
- Optionally set OPENROUTER_MODEL

Run:
  python -m tests.utils.test_openrouter_digest
"""

import sys
import json
from datetime import datetime

sys.path.insert(0, "D:\\Projects\\FinNews")

from config.config import Config
from utils.digest_controller import DIGEST_JSON_SCHEMA, DigestController
from utils.openrouter_client import OpenRouterClient
from models.market_data import (
    MultiWindowData,
    FlashWindowData,
    CycleWindowData,
    TrendWindowData,
    NewsItem,
)
from models.analysis import MarketSignal, AlertLevel, MacroBias


def test_openrouter_digest():
    """测试 OpenRouter 摘要生成功能"""
    if not Config.OPENROUTER_API_KEY:
        raise SystemExit("Missing OPENROUTER_API_KEY")

    # 创建示例数据
    now = datetime.now()

    # Flash窗口数据 (12小时)
    flash = FlashWindowData(
        news=[
            NewsItem(
                title="Gold steadies as traders await Fed guidance",
                source="Reuters",
                summary="Gold prices were little changed as markets awaited commentary from the Federal Reserve.",
                url="https://example.com/gold-fed",
                timestamp=now,
            ),
            NewsItem(
                title="Silver prices rise on industrial demand",
                source="Bloomberg",
                summary="Silver gained 0.5% as industrial demand outlook improved.",
                url="https://example.com/silver-demand",
                timestamp=now,
            ),
        ],
        price_records=[
            {
                "ticker": "GC=F",
                "ticker_name": "Gold Futures",
                "price": 2050.12,
                "change_percent": 0.8,
            },
            {
                "ticker": "SI=F",
                "ticker_name": "Silver Futures",
                "price": 23.45,
                "change_percent": 0.5,
            },
        ],
    )

    # Cycle窗口数据 (7天)
    cycle = CycleWindowData(
        news=[
            NewsItem(
                title="Fed signals patience on rate cuts",
                source="CNBC",
                summary="Federal Reserve officials indicated they are in no rush to cut interest rates.",
                url="https://example.com/fed-rates",
                timestamp=now,
            ),
        ],
        economic_records=[
            {"indicator": "CPI", "value": 3.2, "change_pct": 0.1},
            {"indicator": "PCE", "value": 2.8, "change_pct": -0.1},
        ],
        cpi_actual=3.2,
        pce_actual=2.8,
    )

    # Trend窗口数据 (30天)
    trend = TrendWindowData(
        news=[
            NewsItem(
                title="Central banks continue gold purchases",
                source="World Gold Council",
                summary="Central bank gold buying remained strong in Q4 2025.",
                url="https://example.com/cb-gold",
                timestamp=now,
            ),
        ],
    )

    # 组合多窗口数据
    multi_window_data = MultiWindowData(flash=flash, cycle=cycle, trend=trend)

    # 创建市场信号
    market_signal = MarketSignal(
        vix_value=18.5,
        vix_prev_close=17.2,
        vix_change_percent=7.56,
        vix_alert_level=AlertLevel.WARNING,
        dxy_value=104.2,
        dxy_change_percent=-0.3,
        us10y_value=4.25,
        us10y_change_percent=0.1,
        gold_price=2050.12,
        gold_change_percent=0.8,
        silver_price=23.45,
        silver_change_percent=0.5,
        macro_bias=MacroBias.BULLISH,
        sentiment_score=0.3,
        is_urgent=False,
        alert_messages=["VIX上升7.56%，市场波动性增加"],
    )

    # 创建摘要控制器
    controller = DigestController()
    user_prompt, stats = controller.build_llm_prompt(multi_window_data, market_signal)

    print(
        f"Flash news: {stats['flash_news_count']} | Cycle news: {stats['cycle_news_count']} | Trend news: {stats['trend_news_count']}"
    )
    print(f"Total records: {stats['total_records_count']}")
    print(
        f"Counts by type: price={stats.get('price_records_count', 0)}, economic={stats.get('economic_records_count', 0)}"
    )

    client = OpenRouterClient(
        api_key=Config.OPENROUTER_API_KEY,
        model=Config.OPENROUTER_MODEL,
        timeout=Config.OPENROUTER_TIMEOUT,
        max_retries=Config.OPENROUTER_MAX_RETRIES,
        http_referer=Config.OPENROUTER_HTTP_REFERER,
        x_title=Config.OPENROUTER_X_TITLE,
    )

    # 4段式系统提示
    system_prompt = """你是一位专业的金融分析师，专注于黄金白银市场。
请根据提供的多窗口数据，生成一份结构化的HTML邮件摘要。

邮件必须包含以下4个板块:
1. 市场指数与数据 - 顶部显示VIX信号灯(圆圈样式🟢/⚠️/🔴)，然后是价格表和经济指标
2. 重点新闻 - 5-8条最重要的新闻，仅陈述事实，不要添加任何分析内容
3. 其他新闻 - 剩余新闻，仅陈述事实，不要添加任何分析内容
4. 市场分析 - 所有分析内容集中在此板块

输出要求:
- 所有内容必须使用中文
- HTML格式，适合Gmail邮件客户端
- 严格按照JSON Schema返回结果"""

    print("\nCalling OpenRouter API...")
    resp = client.chat_completions(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=Config.OPENROUTER_TEMPERATURE,
        max_tokens=Config.OPENROUTER_MAX_TOKENS,
        response_format={"type": "json_schema", "json_schema": DIGEST_JSON_SCHEMA},
        reasoning_effort="high",
    )

    content = resp.get("choices", [{}])[0].get("message", {}).get("content")
    if not isinstance(content, str):
        raise SystemExit(f"Unexpected response content: {content}")

    data = json.loads(content)

    assert isinstance(data.get("subject"), str) and data["subject"].strip()
    assert isinstance(data.get("html_body"), str) and data["html_body"].strip()

    print("\n✅ OK: schema-like response received")
    print(f"Subject: {data['subject']}")
    print(f"HTML body length: {len(data['html_body'])} characters")


if __name__ == "__main__":
    test_openrouter_digest()
