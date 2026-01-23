"""生成摘要并保存为HTML文件（不发送邮件）

使用当前 outputs/raw 目录中的最新数据生成摘要。

Prereqs:
- Set OPENROUTER_API_KEY in .env
- Run `python main.py` first to generate data (or use sample data)

Run:
  python test_digest_to_file.py
"""

import json
from pathlib import Path
from datetime import datetime

from config.config import Config
from utils.digest_controller import DIGEST_JSON_SCHEMA, DigestController
from utils.openrouter_client import OpenRouterClient
from analyzers.rule_engine import RuleEngine
from analyzers.market_analyzer import MarketAnalyzer


def load_latest_processed_data():
    """从 outputs/raw 加载最新的原始 JSON 数据"""
    raw_dir = Config.RAW_DIR
    json_files = sorted(
        raw_dir.glob("raw_*.json"), key=lambda p: p.stat().st_mtime, reverse=True
    )

    if not json_files:
        raise FileNotFoundError("No raw data found. Run 'python main.py' first.")

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

    # 规则引擎分析
    price_data = [r for r in records if r.get("type") == "price_data"]
    rule_engine = RuleEngine()
    market_signal = rule_engine.analyze(price_data)

    print(f"VIX: {market_signal.vix_value or 'N/A'}")
    print(f"VIX Alert: {market_signal.vix_alert_level.value}")
    print(f"Macro Bias: {market_signal.macro_bias.value}")

    # 市场分析器组织数据
    market_analyzer = MarketAnalyzer()
    multi_window_data = market_analyzer.organize_data(records, market_signal)

    print(f"Flash news: {len(multi_window_data.flash.news)}")
    print(f"Cycle news: {len(multi_window_data.cycle.news)}")
    print(f"Trend news: {len(multi_window_data.trend.news)}")

    # 创建摘要控制器
    controller = DigestController()
    user_prompt, stats = controller.build_llm_prompt(multi_window_data, market_signal)

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

    # LLM系统提示 - 只返回结构化数据，不生成HTML
    system_prompt = """你是一位专业的金融分析师，专注于黄金白银市场。
请根据提供的数据，返回结构化的JSON数据。

你的任务:
1. 生成邮件标题 (subject)
2. 从新闻中筛选5-8条最重要的作为重点新闻 (key_news)
3. 将其他相关新闻放入其他新闻 (other_news)  
4. 撰写市场分析 (analysis)

重要规则:
- 所有英文新闻标题和摘要必须翻译成中文
- 新闻只陈述事实，不要添加任何分析性语言
- 所有分析、判断、建议必须放在analysis字段
- 使用中文，专业但易懂
- 严格按照JSON Schema返回结果"""

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

    digest_data = json.loads(content)

    # 使用模板渲染HTML
    subject = digest_data.get("subject", "FinNews Digest")
    html_body = controller.render_email_html(
        digest_data=digest_data,
        signal=market_signal,
        data=multi_window_data,
        comex_signal=None,  # 如果需要COMEX数据，需要从规则引擎获取
    )

    # 保存为 HTML 文件
    output_file = (
        Config.OUTPUT_DIR
        / f"digest_preview_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    )

    # 包装完整的 HTML 文档
    full_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{subject}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            font-size: 16px;
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
            font-size: 1.1em;
            margin-bottom: 20px;
        }}
    </style>
</head>
<body>
    <div class="email-container">
        <h1>{subject}</h1>
        <div class="metadata">
            Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}<br>
            Flash: {stats["flash_news_count"]} | Cycle: {stats["cycle_news_count"]} | Trend: {stats["trend_news_count"]}
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
