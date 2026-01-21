"""OpenRouter Chat Completions client.

Minimal dependency implementation using `requests`.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, Optional

import requests


class OpenRouterError(Exception):
    pass


class OpenRouterClient:
    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        base_url: str = "https://openrouter.ai/api/v1",
        timeout: int = 60,
        max_retries: int = 3,
        http_referer: Optional[str] = None,
        x_title: Optional[str] = None,
    ):
        if not api_key:
            raise ValueError("api_key is required")

        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.http_referer = http_referer
        self.x_title = x_title

        self.session = requests.Session()

    def _headers(self) -> Dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self.http_referer:
            headers["HTTP-Referer"] = self.http_referer
        if self.x_title:
            headers["X-Title"] = self.x_title
        return headers

    def chat_completions(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        response_format: Optional[Dict[str, Any]] = None,
        reasoning_effort: Optional[str] = None,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/chat/completions"
        payload: Dict[str, Any] = {
            "model": self.model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        if response_format is not None:
            payload["response_format"] = response_format
        if reasoning_effort is not None:
            payload["reasoning_effort"] = reasoning_effort

        last_error: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                resp = self.session.post(
                    url,
                    headers=self._headers(),
                    data=json.dumps(payload),
                    timeout=self.timeout,
                )

                if resp.status_code in {429, 500, 502, 503, 504}:
                    wait_s = min(2 ** (attempt - 1), 8)
                    time.sleep(wait_s)
                    continue

                if resp.status_code in {401, 402, 403}:
                    raise OpenRouterError(
                        f"OpenRouter auth/credit error: {resp.status_code} {resp.text}"
                    )

                resp.raise_for_status()
                return resp.json()

            except requests.exceptions.RequestException as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    break
                wait_s = min(2 ** (attempt - 1), 8)
                time.sleep(wait_s)

        raise OpenRouterError(f"OpenRouter request failed: {last_error}")
