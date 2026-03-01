"""
测试 OpenRouter 摘要生成功能（mock 版）
"""

import json
import pytest
from datetime import datetime

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


FAKE_DIGEST = {
    "subject": "【黄金市场】联储信号引发波动，黄金稳守高位",
    "key_news": [
        {
            "title": "黄金在联储指引前保持平稳",
            "source": "Reuters",
            "summary": "黄金价格变化不大，市场等待联储评论。",
            "url": "https://example.com/gold-fed",
            "impact_tag": "#Neutral",
        }
    ],
    "other_news": [
        {
            "title": "白银工业需求上升",
            "source": "Bloomberg",
            "summary": "白银随工业需求前景改善而走强。",
            "url": "https://example.com/silver-demand",
            "impact_tag": "#Bullish",
        }
    ],
    "analysis": {
        "market_sentiment": "市场情绪谨慎偏多",
        "price_outlook": "黄金短线维持强势",
        "risk_factors": "联储政策不确定性",
        "trading_suggestion": "关注支撑位2030美元",
    },
}


@pytest.fixture
def mock_openrouter(mocker):
    """mock OpenRouter API，返回预构造的 JSON 响应"""
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(FAKE_DIGEST),
                    "role": "assistant",
                }
            }
        ]
    }
    mock_response.raise_for_status = mocker.MagicMock()

    mock_session = mocker.MagicMock()
    mock_session.post.return_value = mock_response
    mocker.patch("utils.openrouter_client.requests.Session", return_value=mock_session)
    return mock_session


@pytest.fixture
def sample_multi_window():
    now = datetime.now()
    flash = FlashWindowData(
        news=[
            NewsItem(
                title="Gold steadies as traders await Fed guidance",
                source="Reuters",
                summary="Gold prices were little changed.",
                url="https://example.com/gold-fed",
                timestamp=now,
            ),
        ],
        price_records=[
            {"ticker": "GC=F", "ticker_name": "Gold Futures", "price": 2050.12, "change_percent": 0.8},
        ],
    )
    cycle = CycleWindowData(
        news=[
            NewsItem(
                title="Fed signals patience on rate cuts",
                source="CNBC",
                summary="Federal Reserve officials indicated no rush to cut rates.",
                url="https://example.com/fed-rates",
                timestamp=now,
            ),
        ],
        economic_records=[{"indicator": "CPI", "value": 3.2, "change_pct": 0.1}],
    )
    trend = TrendWindowData(news=[])
    return MultiWindowData(flash=flash, cycle=cycle, trend=trend)


@pytest.fixture
def sample_signal():
    return MarketSignal(
        vix_value=18.5,
        vix_alert_level=AlertLevel.WARNING,
        dxy_value=104.2,
        us10y_value=4.25,
        macro_bias=MacroBias.BULLISH,
    )


def test_openrouter_digest_response_schema(mock_openrouter, sample_multi_window, sample_signal):
    """OpenRouter 响应应符合 schema：subject 为字符串"""
    client = OpenRouterClient(api_key="dummy", model="claude-3-haiku")
    resp = client.chat_completions(
        system_prompt="你是分析师",
        user_prompt="分析市场",
        temperature=0.2,
        max_tokens=1200,
    )

    content = resp.get("choices", [{}])[0].get("message", {}).get("content")
    data = json.loads(content)

    assert isinstance(data.get("subject"), str) and data["subject"].strip()


def test_openrouter_digest_key_news_fields(mock_openrouter, sample_multi_window, sample_signal):
    """key_news 中每条记录应有 title、source、summary"""
    client = OpenRouterClient(api_key="dummy", model="claude-3-haiku")
    resp = client.chat_completions(system_prompt="", user_prompt="")

    content = resp["choices"][0]["message"]["content"]
    data = json.loads(content)

    for item in data.get("key_news", []):
        assert isinstance(item.get("title"), str) and item["title"].strip()
        assert isinstance(item.get("source"), str) and item["source"].strip()
        assert isinstance(item.get("summary"), str)


def test_openrouter_digest_analysis_fields(mock_openrouter, sample_multi_window, sample_signal):
    """analysis 应包含四个必要字段"""
    client = OpenRouterClient(api_key="dummy", model="claude-3-haiku")
    resp = client.chat_completions(system_prompt="", user_prompt="")

    content = resp["choices"][0]["message"]["content"]
    data = json.loads(content)

    analysis = data.get("analysis", {})
    for key in ("market_sentiment", "price_outlook", "risk_factors", "trading_suggestion"):
        assert isinstance(analysis.get(key), str) and analysis[key].strip()


def test_digest_controller_render_html(mock_openrouter, sample_multi_window, sample_signal):
    """DigestController.render_email_html 应生成有效 HTML"""
    controller = DigestController()
    html, _ = controller.render_email_html(
        digest_data=FAKE_DIGEST,
        signal=sample_signal,
        data=sample_multi_window,
    )
    assert isinstance(html, str) and html.strip()
    assert "<html" in html.lower() or "<!doctype" in html.lower()
