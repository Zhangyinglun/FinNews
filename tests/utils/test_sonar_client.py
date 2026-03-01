"""
测试 SonarClient 提示词、响应解析与异常日志
"""

from unittest.mock import Mock

import requests

from utils import sonar_client
from utils.sonar_client import SonarClient


def test_build_payload_contains_citations_requirement():
    """系统提示词必须明确要求 citations 引用"""
    client = SonarClient(api_key="dummy")
    payload = client._build_payload("gold news", max_tokens=128)
    system_prompt = payload["messages"][0]["content"]
    assert "citation" in system_prompt.lower() or "引用" in system_prompt, (
        "提示词未强调引用链接"
    )


def test_parse_response_citations_from_strings():
    """解析 citations 字符串数组"""
    client = SonarClient(api_key="dummy")
    response = {
        "choices": [
            {
                "message": {
                    "content": "摘要",
                    "citations": [
                        "https://example.com/a",
                        "https://example.com/b",
                    ],
                }
            }
        ]
    }
    result = client._parse_response(response)
    assert result.answer == "摘要"
    assert [c.url for c in result.citations] == [
        "https://example.com/a",
        "https://example.com/b",
    ]


def test_parse_response_citations_from_dicts():
    """解析 citations 字典数组"""
    client = SonarClient(api_key="dummy")
    response = {
        "choices": [
            {
                "message": {
                    "content": "摘要",
                    "citations": [
                        {"url": "https://example.com/a", "title": "A"},
                        {"url": "https://example.com/b", "title": "B"},
                    ],
                }
            }
        ]
    }
    result = client._parse_response(response)
    assert [c.url for c in result.citations] == [
        "https://example.com/a",
        "https://example.com/b",
    ]
    assert [c.title for c in result.citations] == ["A", "B"]


def test_parse_response_logs_exception_with_stack():
    """解析异常必须记录完整堆栈"""
    client = SonarClient(api_key="dummy")
    client.logger.error = Mock()
    response = {"choices": [None]}
    result = client._parse_response(response)
    assert result.answer == ""
    assert result.citations == []
    client.logger.error.assert_called_once()
    _, kwargs = client.logger.error.call_args
    assert kwargs.get("exc_info") is True


def test_search_logs_request_exception_with_stack():
    """请求异常必须记录完整堆栈"""
    client = SonarClient(api_key="dummy", max_retries=2)
    client.session.post = Mock(side_effect=requests.exceptions.RequestException("x"))
    client.logger.warning = Mock()
    sonar_client.time.sleep = Mock()
    try:
        client.search("gold news", max_tokens=8)
    except Exception:
        pass
    client.logger.warning.assert_called_once()
    _, kwargs = client.logger.warning.call_args
    assert kwargs.get("exc_info") is True
