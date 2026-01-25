"""
测试 SonarClient 提示词与 payload 构建
"""

import sys

sys.path.insert(0, "D:\\Projects\\FinNews")

from utils.sonar_client import SonarClient


def test_build_payload_contains_citations_requirement():
    """系统提示词必须明确要求 citations 引用"""
    client = SonarClient(api_key="dummy")
    payload = client._build_payload("gold news", max_tokens=128)
    system_prompt = payload["messages"][0]["content"]
    assert "citation" in system_prompt.lower() or "引用" in system_prompt, (
        "提示词未强调引用链接"
    )


if __name__ == "__main__":
    test_build_payload_contains_citations_requirement()
