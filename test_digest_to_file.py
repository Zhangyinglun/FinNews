"""生成摘要并保存为HTML文件（不发送邮件）

使用当前 outputs/processed 目录中的最新数据生成摘要。

Prereqs:
- Set OPENROUTER_API_KEY in .env
- Run `python main.py --mode once` first to generate data

Run:
  python test_digest_to_file.py
"""

import json
from pathlib import Path
from datetime import datetime

from config.config import Config
from utils.digest_controller import DIGEST_JSON_SCHEMA, DailyDigestController
from utils.openrouter_client import OpenRouterClient


def load_latest_processed_data():
    """从 outputs/raw 加载最新的原始 JSON 数据"""
    raw_dir = Config.RAW_DIR
    json_files = sorted(
        raw_dir.glob("raw_*.json"), key=lambda p: p.stat().st_mtime, reverse=True
    )

    if not json_files:
        raise FileNotFoundError(
            "No raw data found. Run 'python main.py --mode once' first."
        )

    latest_file = json_files[0]
    print(f"Loading data from: {latest_file}")

    with open(latest_file, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    if not Config.OPENROUTER_API_KEY:
        raise SystemExit("Missing OPENROUTER_API_KEY in .env")

    # 加载最新数据
    records = load_latest_processed_data()
    print(f"Loaded {len(records)} records")

    # 创建摘要控制器
    controller = DailyDigestController(window_hours=Config.DIGEST_WINDOW_HOURS)
    stats = controller.update(records)

    print(f"Window: {stats.window_hours}h | Records in window: {stats.total_records}")
    print(f"Counts by type: {stats.counts_by_type}")
    print(f"Counts by source: {stats.counts_by_source}")

    # 构建 LLM 输入
    user_prompt, _ = controller.build_llm_input(
        include_full_content=Config.DIGEST_INCLUDE_FULL_CONTENT,
        max_full_content_chars_per_article=Config.DIGEST_FULL_CONTENT_MAX_CHARS_PER_ARTICLE,
    )

    print(f"\nPrompt size: {len(user_prompt)} chars")
    print("Calling OpenRouter...")

    # 调用 OpenRouter
    client = OpenRouterClient(
        api_key=Config.OPENROUTER_API_KEY,
        model=Config.OPENROUTER_MODEL,
        timeout=Config.OPENROUTER_TIMEOUT,
        max_retries=Config.OPENROUTER_MAX_RETRIES,
        http_referer=Config.OPENROUTER_HTTP_REFERER,
        x_title=Config.OPENROUTER_X_TITLE,
    )

    system_prompt = (
        "You are a financial analyst writing an HTML email digest focused on gold and silver price trends. "
        "Output MUST be in Chinese (中文). "
        "Structure the email in EXACTLY 4 sections:\n\n"
        "1) 市场指数与数据 - Current prices, economic indicators, FX rates (factual summary only)\n"
        "2) 重点新闻 - Top 5-8 most important news items (title + brief description, NO analysis)\n"
        "3) 其他新闻 - Remaining news items (title + brief description, NO analysis)\n"
        "4) 市场分析 - Deep analysis of how ALL the above news and data will impact gold (XAU) and silver (XAG) prices. "
        "Discuss bullish/bearish factors, correlations, technical levels, safe-haven demand, inflation expectations, USD strength, geopolitical risks, etc.\n\n"
        "IMPORTANT: Sections 2 and 3 should ONLY contain factual news summaries without analysis. "
        "ALL analysis must be in Section 4. "
        "Use professional HTML formatting suitable for Gmail with clear headings. "
        "All content must be in Chinese."
    )

    resp = client.chat_completions(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=Config.OPENROUTER_TEMPERATURE,
        max_tokens=Config.OPENROUTER_MAX_TOKENS,
        response_format={"type": "json_schema", "json_schema": DIGEST_JSON_SCHEMA},
        reasoning_effort="high",
    )

    print("OpenRouter call completed")

    # 解析响应
    content = resp.get("choices", [{}])[0].get("message", {}).get("content")
    if not isinstance(content, str):
        raise SystemExit(f"Unexpected response content: {content}")

    digest = json.loads(content)

    subject = digest.get("subject", "FinNews Digest")
    html_body = digest.get("html_body", "<p>No content</p>")

    # 保存为 HTML 文件
    output_file = (
        Config.OUTPUT_DIR
        / f"digest_preview_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    )

    # 包装完整的 HTML 文档
    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{subject}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .email-container {{
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
        }}
        .metadata {{
            color: #7f8c8d;
            font-size: 0.9em;
            margin-bottom: 20px;
        }}
    </style>
</head>
<body>
    <div class="email-container">
        <h1>{subject}</h1>
        <div class="metadata">
            Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}<br>
            Window: {stats.window_hours} hours | Records: {stats.total_records}
        </div>
        {html_body}
    </div>
</body>
</html>"""

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(full_html)

    print(f"\n✅ Digest saved to: {output_file}")
    print(f"Subject: {subject}")
    print(f"HTML body size: {len(html_body)} chars")
    print(f"\nOpen in browser: file:///{output_file.absolute()}")


if __name__ == "__main__":
    main()
