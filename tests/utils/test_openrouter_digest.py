"""
测试 OpenRouter 摘要生成功能（mock 版）
"""

import json
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from main import (
    build_llm_fallback_email_html,
    build_llm_fallback_subject,
    parse_digest_response,
)
from models.analysis import AlertLevel, MacroBias, MarketSignal
from models.market_data import (
    CycleWindowData,
    FlashWindowData,
    MultiWindowData,
    NewsItem,
    TrendWindowData,
)
from utils.digest_controller import DigestController
from utils.openrouter_client import OpenRouterClient


FAKE_DIGEST = {
    "subject": "【黄金市场】联储信号引发波动，黄金稳守高位",
    "news_clusters": [
        {
            "cluster_title": "联储信号前市场观望",
            "cluster_summary": "黄金价格基本持平，市场等待联储评论，风险偏好暂未明显切换。",
            "impact_tag": "Neutral",
            "sources": [
                {
                    "title": "黄金在联储指引前保持平稳",
                    "source": "Reuters",
                    "url": "https://example.com/gold-fed",
                    "timestamp": "09:30",
                }
            ],
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
def mock_openrouter(monkeypatch):
    """mock OpenRouter API，返回预构造的 JSON 响应"""
    mock_response = MagicMock()
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
    mock_response.raise_for_status = MagicMock()

    mock_session = MagicMock()
    mock_session.post.return_value = mock_response
    monkeypatch.setattr(
        "utils.openrouter_client.requests.Session", lambda: mock_session
    )
    return mock_session


@pytest.fixture
def mock_session_factory(monkeypatch):
    def _build(message_payload):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "gen-test",
            "model": "deepseek/deepseek-v3.2",
            "provider": "test-provider",
            "usage": {
                "completion_tokens": 12,
                "completion_tokens_details": {"reasoning_tokens": 8},
            },
            "choices": [{"message": message_payload, "finish_reason": "stop"}],
        }
        mock_response.raise_for_status = MagicMock()
        mock_session = MagicMock()
        mock_session.post.return_value = mock_response
        monkeypatch.setattr(
            "utils.openrouter_client.requests.Session", lambda: mock_session
        )
        return mock_session

    return _build


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
            {
                "ticker": "GC=F",
                "ticker_name": "Gold Futures",
                "price": 2050.12,
                "change_percent": 0.8,
            },
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


def test_openrouter_digest_response_schema(
    mock_openrouter, sample_multi_window, sample_signal
):
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


def test_openrouter_digest_news_clusters_fields(
    mock_openrouter, sample_multi_window, sample_signal
):
    """news_clusters 中每条记录应有标题、摘要、方向和来源"""
    client = OpenRouterClient(api_key="dummy", model="claude-3-haiku")
    resp = client.chat_completions(system_prompt="", user_prompt="")

    content = resp["choices"][0]["message"]["content"]
    data = json.loads(content)

    for item in data.get("news_clusters", []):
        assert (
            isinstance(item.get("cluster_title"), str) and item["cluster_title"].strip()
        )
        assert isinstance(item.get("cluster_summary"), str)
        assert item.get("impact_tag") in {"Bullish", "Bearish", "Neutral"}
        assert isinstance(item.get("sources"), list)


def test_openrouter_digest_analysis_fields(
    mock_openrouter, sample_multi_window, sample_signal
):
    """analysis 应包含四个必要字段"""
    client = OpenRouterClient(api_key="dummy", model="claude-3-haiku")
    resp = client.chat_completions(system_prompt="", user_prompt="")

    content = resp["choices"][0]["message"]["content"]
    data = json.loads(content)

    analysis = data.get("analysis", {})
    for key in (
        "market_sentiment",
        "price_outlook",
        "risk_factors",
        "trading_suggestion",
    ):
        assert isinstance(analysis.get(key), str) and analysis[key].strip()


def test_digest_controller_render_html(
    mock_openrouter, sample_multi_window, sample_signal
):
    """DigestController.render_email_html 应生成有效 HTML"""
    controller = DigestController()
    html, _ = controller.render_email_html(
        digest_data=FAKE_DIGEST,
        signal=sample_signal,
        data=sample_multi_window,
    )
    assert isinstance(html, str) and html.strip()
    assert "<html" in html.lower() or "<!doctype" in html.lower()


def test_openrouter_request_enables_json_guardrails(mock_openrouter):
    """请求应显式开启 json_schema、response-healing 和 require_parameters"""
    client = OpenRouterClient(api_key="dummy", model="deepseek/deepseek-v3.2")

    client.chat_completions(
        system_prompt="你是分析师",
        user_prompt="分析市场",
        response_format={
            "type": "json_schema",
            "json_schema": {"name": "x", "schema": {}},
        },
    )

    _, kwargs = client.session.post.call_args
    payload = json.loads(kwargs["data"])

    assert payload["response_format"]["type"] == "json_schema"
    assert payload["plugins"] == [{"id": "response-healing"}]
    assert payload["provider"] == {"require_parameters": True}


def test_parse_digest_response_reports_empty_content(mock_session_factory):
    """content 为空时应给出 empty_content 原因码"""
    mock_session_factory({"role": "assistant", "content": None})
    client = OpenRouterClient(api_key="dummy", model="deepseek/deepseek-v3.2")
    resp = client.chat_completions(system_prompt="", user_prompt="")

    parsed = parse_digest_response(resp)

    assert parsed["digest_data"] is None
    assert parsed["error_code"] == "empty_content"
    assert parsed["meta"]["has_refusal"] is False
    assert parsed["meta"]["message_keys"] == ["content", "role"]
    assert parsed["meta"]["choice_keys"] == ["finish_reason", "message"]
    assert parsed["meta"]["raw_message_preview"]
    assert parsed["meta"]["tool_calls_count"] == 0


def test_parse_digest_response_reports_json_decode_error(mock_session_factory):
    """坏 JSON 应返回 json_decode_error"""
    mock_session_factory(
        {"role": "assistant", "content": '```json\n{"subject": "x"}\n```'}
    )
    client = OpenRouterClient(api_key="dummy", model="deepseek/deepseek-v3.2")
    resp = client.chat_completions(system_prompt="", user_prompt="")

    parsed = parse_digest_response(resp)

    assert parsed["digest_data"] is None
    assert parsed["error_code"] == "json_decode_error"
    assert parsed["meta"]["content_type"] == "str"


def test_parse_digest_response_reports_refusal_or_empty(mock_session_factory):
    """有 refusal 且 content 为空时应给出 refusal_or_empty"""
    mock_session_factory(
        {
            "role": "assistant",
            "content": None,
            "refusal": "无法完成这个请求",
        }
    )
    client = OpenRouterClient(api_key="dummy", model="deepseek/deepseek-v3.2")
    resp = client.chat_completions(system_prompt="", user_prompt="")

    parsed = parse_digest_response(resp)

    assert parsed["digest_data"] is None
    assert parsed["error_code"] == "refusal_or_empty"
    assert parsed["meta"]["has_refusal"] is True
    assert parsed["meta"]["message_keys"] == ["content", "refusal", "role"]


def test_parse_digest_response_records_reasoning_and_tool_calls(mock_session_factory):
    """content 缺失时也应记录 reasoning 和 tool_calls 诊断信息"""
    mock_session_factory(
        {
            "role": "assistant",
            "content": None,
            "reasoning": "先整理市场数据，再按 schema 输出。",
            "reasoning_details": [{"type": "summary", "text": "先做聚合"}],
            "tool_calls": [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": "noop", "arguments": "{}"},
                }
            ],
        }
    )
    client = OpenRouterClient(api_key="dummy", model="deepseek/deepseek-v3.2")
    resp = client.chat_completions(system_prompt="", user_prompt="")

    parsed = parse_digest_response(resp)

    assert parsed["digest_data"] is None
    assert parsed["error_code"] == "empty_content"
    assert parsed["meta"]["has_reasoning"] is True
    assert parsed["meta"]["tool_calls_count"] == 1
    assert "先整理市场数据" in parsed["meta"]["reasoning_preview"]
    assert "先做聚合" in parsed["meta"]["reasoning_details_preview"]
    assert parsed["meta"]["raw_choice_preview"]


def test_llm_fallback_helpers_include_reason_code(sample_signal):
    """fallback 标题和正文应带上原因码，方便排查。"""
    subject = build_llm_fallback_subject("测试日报", "empty_content")
    html = build_llm_fallback_email_html(sample_signal, "empty_content")

    assert "[fallback:empty_content]" in subject
    assert "原因码" in html
    assert "empty_content" in html
