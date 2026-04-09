"""
测试摘要生成并保存为 HTML 文件（mock 版）
"""

import json
import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

from utils.digest_controller import DigestController
from utils.openrouter_client import OpenRouterClient
from analyzers.rule_engine import RuleEngine
from analyzers.market_analyzer import MarketAnalyzer
from models.market_data import MultiWindowData
from models.analysis import ComexSignal, ComexAlertLevel


FAKE_DIGEST = {
    "subject": "【黄金白银】市场观察日报",
    "news_clusters": [
        {
            "cluster_title": "黄金价格在联储信号前保持稳定",
            "cluster_summary": "黄金在等待联储官员讲话期间基本持平，市场情绪偏观望。",
            "impact_tag": "Neutral",
            "sources": [
                {
                    "title": "黄金价格在美联储信号前保持稳定",
                    "source": "Reuters",
                    "url": "https://example.com/1",
                    "timestamp": "10:20",
                }
            ],
        }
    ],
    "analysis": {
        "market_sentiment": "谨慎",
        "price_outlook": "中性偏多",
        "risk_factors": "联储政策",
        "trading_suggestion": "持仓观望",
    },
}

# 内联测试数据（不依赖真实 outputs/ 目录）
SAMPLE_RECORDS = [
    {
        "type": "price_data",
        "ticker_name": "gold_futures",
        "ticker": "GC=F",
        "price": 2050.12,
        "change_percent": 0.8,
        "source": "YFinance",
        "timestamp": datetime.now(),
    },
    {
        "type": "price_data",
        "ticker_name": "silver_futures",
        "ticker": "SI=F",
        "price": 23.45,
        "change_percent": 0.5,
        "source": "YFinance",
        "timestamp": datetime.now(),
    },
    {
        "type": "news",
        "title": "Gold steadies as traders await Fed guidance",
        "summary": "Gold prices were little changed as markets awaited commentary.",
        "url": "https://example.com/gold-fed",
        "source": "Reuters",
        "timestamp": datetime.now(),
    },
]


@pytest.fixture
def mock_openrouter(monkeypatch):
    """mock OpenRouter API 返回预构造 JSON"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": json.dumps(FAKE_DIGEST), "role": "assistant"}}]
    }
    mock_response.raise_for_status = MagicMock()

    mock_session = MagicMock()
    mock_session.post.return_value = mock_response
    monkeypatch.setattr("utils.openrouter_client.requests.Session", lambda: mock_session)
    return mock_session


def test_digest_pipeline_generates_html(mock_openrouter, tmp_path):
    """完整管道：数据 → 规则引擎 → 摘要控制器 → HTML 文件"""
    # 规则引擎分析
    price_data = [r for r in SAMPLE_RECORDS if r.get("type") == "price_data"]
    rule_engine = RuleEngine()
    market_signal = rule_engine.analyze(price_data)

    # 市场分析器组织数据
    market_analyzer = MarketAnalyzer()
    multi_window_data = market_analyzer.organize_data(SAMPLE_RECORDS, market_signal)

    # 创建 COMEX 示例数据
    comex_signal = ComexSignal(
        silver_registered=35_000_000.0,
        silver_registered_million=35.0,
        silver_total=280_000_000.0,
        silver_alert_level=ComexAlertLevel.YELLOW,
        silver_alert_message="⚠️ 白银Registered库存低于40M oz警戒线，当前35.00M oz",
        silver_recommendation="密切关注库存变化趋势，考虑逐步建仓",
        silver_daily_change_pct=-1.2,
        silver_weekly_change_pct=-3.5,
        gold_registered=8_500_000.0,
        gold_registered_million=8.50,
        gold_total=22_000_000.0,
        gold_alert_level=ComexAlertLevel.SAFE,
        gold_alert_message="",
        gold_recommendation="",
        gold_daily_change_pct=0.3,
        gold_weekly_change_pct=1.1,
        report_date=datetime(2026, 2, 28),
    )

    # 创建摘要控制器
    controller = DigestController()

    # 渲染 HTML
    email_html, _ = controller.render_email_html(
        digest_data=FAKE_DIGEST,
        signal=market_signal,
        data=multi_window_data,
        comex_signal=comex_signal,
    )

    assert isinstance(email_html, str) and email_html.strip(), "应生成有效的HTML邮件内容"

    # 保存为 HTML 文件
    output_file = tmp_path / "digest_preview.html"
    output_file.write_text(email_html, encoding="utf-8")

    assert output_file.exists(), "HTML 文件应被创建"
    assert output_file.stat().st_size > 100, "HTML 文件应有实际内容"


def test_digest_subject_from_signal(mock_openrouter):
    """摘要控制器应能从市场信号生成邮件标题"""
    price_data = [r for r in SAMPLE_RECORDS if r.get("type") == "price_data"]
    rule_engine = RuleEngine()
    market_signal = rule_engine.analyze(price_data)

    controller = DigestController()
    subject = controller.get_email_subject(market_signal)

    assert isinstance(subject, str) and subject.strip(), "应生成有效的邮件标题"
