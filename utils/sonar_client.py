"""
Perplexity Sonar 搜索客户端 (via OpenRouter)

专用于调用 Perplexity Sonar 模型进行新闻搜索，
解析 citations 返回结构化的搜索结果。
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import requests


class SonarError(Exception):
    """Sonar API 错误"""

    pass


@dataclass
class Citation:
    """引用来源"""

    url: str
    title: Optional[str] = None


@dataclass
class SonarSearchResult:
    """Sonar 搜索结果"""

    answer: str  # Sonar 的回答摘要
    citations: List[Citation] = field(default_factory=list)  # 引用来源列表
    raw_response: Optional[Dict[str, Any]] = None  # 原始响应 (调试用)


class SonarClient:
    """
    Perplexity Sonar 搜索客户端 (via OpenRouter)

    使用 OpenRouter API 调用 Perplexity Sonar 模型，
    执行带引用的新闻搜索。
    """

    def __init__(
        self,
        api_key: str,
        model: str = "perplexity/sonar",
        *,
        base_url: str = "https://openrouter.ai/api/v1",
        timeout: int = 60,
        max_retries: int = 3,
        http_referer: Optional[str] = None,
        x_title: Optional[str] = None,
    ) -> None:
        """
        初始化 Sonar 客户端

        Args:
            api_key: OpenRouter API 密钥
            model: Sonar 模型名称 (默认: perplexity/sonar)
            base_url: OpenRouter API 基础 URL
            timeout: 请求超时秒数
            max_retries: 最大重试次数
            http_referer: HTTP Referer 头 (可选)
            x_title: X-Title 头 (可选)
        """
        if not api_key:
            raise ValueError("api_key 未配置")

        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.http_referer = http_referer
        self.x_title = x_title

        self.session = requests.Session()
        self.logger = logging.getLogger("utils.sonar_client")

    def _headers(self) -> Dict[str, str]:
        """构建请求头"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self.http_referer:
            headers["HTTP-Referer"] = self.http_referer
        if self.x_title:
            headers["X-Title"] = self.x_title
        return headers

    def _build_payload(self, query: str, max_tokens: int) -> Dict[str, Any]:
        system_prompt = (
            "你是一个新闻搜索助手。请搜索最新的相关新闻，"
            "简要总结关键信息，并提供来源链接。"
            "必须返回 citations 引用链接，仅使用权威新闻来源。"
        )
        return {
            "model": self.model,
            "temperature": 0.1,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query},
            ],
        }

    def search(self, query: str, max_tokens: int = 1024) -> SonarSearchResult:
        """
        执行搜索查询

        Args:
            query: 搜索查询字符串
            max_tokens: 最大返回 token 数

        Returns:
            SonarSearchResult: 包含回答和引用的搜索结果
        """
        url = f"{self.base_url}/chat/completions"
        payload = self._build_payload(query, max_tokens)

        last_error: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                self.logger.debug(f"Sonar 搜索 (尝试 {attempt}): {query[:50]}...")

                resp = self.session.post(
                    url,
                    headers=self._headers(),
                    data=json.dumps(payload),
                    timeout=self.timeout,
                )

                # 处理速率限制和服务器错误
                if resp.status_code in {429, 500, 502, 503, 504}:
                    wait_s = min(2 ** (attempt - 1), 8)
                    self.logger.warning(
                        f"Sonar API {resp.status_code}, 等待 {wait_s}s 后重试..."
                    )
                    time.sleep(wait_s)
                    continue

                # 处理认证错误
                if resp.status_code in {401, 402, 403}:
                    raise SonarError(
                        f"Sonar 认证/额度错误: {resp.status_code} {resp.text}"
                    )

                resp.raise_for_status()
                return self._parse_response(resp.json())

            except requests.exceptions.RequestException as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    break
                wait_s = min(2 ** (attempt - 1), 8)
                self.logger.warning(
                    f"请求失败: {exc}, 等待 {wait_s}s 后重试...",
                    exc_info=True,
                )
                time.sleep(wait_s)

        raise SonarError(f"Sonar 请求失败: {last_error}")

    def _parse_response(self, response: Dict[str, Any]) -> SonarSearchResult:
        """
        解析 Sonar API 响应

        Perplexity Sonar 通过 OpenRouter 返回的格式:
        {
          "choices": [{
            "message": {
              "content": "回答内容...",
              "citations": ["https://...", "https://..."]  # 可能存在
            }
          }]
        }

        Args:
            response: API 原始响应

        Returns:
            SonarSearchResult: 解析后的结果
        """
        try:
            choice = response.get("choices", [{}])[0]
            message = choice.get("message", {})

            # 提取回答内容
            answer = message.get("content", "")

            # 提取 citations (Perplexity 特有字段)
            # 注意：在 OpenRouter 的 Perplexity 响应中，citations 往往在顶层或 message 中
            raw_citations = message.get("citations") or response.get("citations") or []

            # 解析 citations
            citations: List[Citation] = []
            for item in raw_citations:
                if isinstance(item, str):
                    # 简单 URL 字符串
                    citations.append(Citation(url=item))
                elif isinstance(item, dict):
                    # 可能是 {url: ..., title: ...} 格式
                    citations.append(
                        Citation(
                            url=item.get("url", ""),
                            title=item.get("title"),
                        )
                    )

            self.logger.debug(
                f"Sonar 响应解析: {len(answer)} 字符, {len(citations)} 个引用"
            )

            return SonarSearchResult(
                answer=answer,
                citations=citations,
                raw_response=response,
            )

        except Exception as e:
            self.logger.error(f"Sonar 响应解析失败: {e}", exc_info=True)
            return SonarSearchResult(
                answer="",
                citations=[],
                raw_response=response,
            )
