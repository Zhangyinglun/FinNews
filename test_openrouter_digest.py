"""Standalone test: OpenRouter digest generation.

Prereqs:
- Set OPENROUTER_API_KEY in .env
- Optionally set OPENROUTER_MODEL

Run:
  python test_openrouter_digest.py
"""

import json

from config.config import Config
from utils.digest_controller import DIGEST_JSON_SCHEMA, DailyDigestController
from utils.openrouter_client import OpenRouterClient


def main():
    if not Config.OPENROUTER_API_KEY:
        raise SystemExit("Missing OPENROUTER_API_KEY")

    controller = DailyDigestController(window_hours=24)

    sample_records = [
        {
            "source": "FRED",
            "type": "economic_data",
            "indicator": "cpi",
            "value": 3.2,
            "change_pct": 0.1,
            "timestamp": "2026-01-20T10:00:00",
        },
        {
            "source": "YFinance_Price",
            "type": "price_data",
            "ticker": "GC=F",
            "ticker_name": "gold_futures",
            "price": 2050.12,
            "change_percent": 0.8,
            "timestamp": "2026-01-20T15:00:00",
        },
        {
            "source": "Reuters",
            "title": "Gold steadies as traders await Fed guidance",
            "summary": "Gold prices were little changed as markets awaited commentary from the Federal Reserve.",
            "url": "https://example.com/gold-fed",
            "timestamp": "2026-01-20T14:30:00",
            "impact_tag": "#Neutral",
        },
    ]

    controller.update(sample_records)
    prompt, stats = controller.build_llm_input(include_full_content=False)
    print(f"Window hours: {stats.window_hours} | Records: {stats.total_records}")

    client = OpenRouterClient(
        api_key=Config.OPENROUTER_API_KEY,
        model=Config.OPENROUTER_MODEL,
        timeout=Config.OPENROUTER_TIMEOUT,
        max_retries=Config.OPENROUTER_MAX_RETRIES,
        http_referer=Config.OPENROUTER_HTTP_REFERER,
        x_title=Config.OPENROUTER_X_TITLE,
    )

    resp = client.chat_completions(
        system_prompt=(
            "You are a financial analyst writing an HTML email digest focused on gold and silver price trends. "
            "Structure the email in EXACTLY 4 sections:\n\n"
            "1) Market Indices & Data - Current prices, economic indicators, FX rates (factual summary only)\n"
            "2) Key News - Top 5-8 most important news items (title + brief description, NO analysis)\n"
            "3) Other News - Remaining news items (title + brief description, NO analysis)\n"
            "4) Market Analysis - Deep analysis of how ALL the above news and data will impact gold (XAU) and silver (XAG) prices. "
            "Discuss bullish/bearish factors, correlations, technical levels, safe-haven demand, inflation expectations, USD strength, geopolitical risks, etc.\n\n"
            "IMPORTANT: Sections 2 and 3 should ONLY contain factual news summaries without analysis. "
            "ALL analysis must be in Section 4. "
            "Use professional HTML formatting suitable for Gmail with clear headings."
        ),
        user_prompt=prompt,
        temperature=Config.OPENROUTER_TEMPERATURE,
        max_tokens=Config.OPENROUTER_MAX_TOKENS,
        response_format={"type": "json_schema", "json_schema": DIGEST_JSON_SCHEMA},
    )

    content = resp.get("choices", [{}])[0].get("message", {}).get("content")
    if not isinstance(content, str):
        raise SystemExit(f"Unexpected response content: {content}")

    data = json.loads(content)

    assert isinstance(data.get("subject"), str) and data["subject"].strip()
    assert isinstance(data.get("html_body"), str) and data["html_body"].strip()
    print("OK: schema-like response received")
    print("Subject:", data["subject"])


if __name__ == "__main__":
    main()
