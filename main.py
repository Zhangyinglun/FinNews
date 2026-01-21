"""
FinNews - 黄金白银走势分析数据管道
主程序入口
"""

import sys
import argparse
import json

from utils.logger import setup_logger
from schedulers import JobScheduler
from scrapers import (
    TavilyScraper,
    YFinanceScraper,
    RSSFeedScraper,
    FREDScraper,
    AlphaVantageScraper,
)
from scrapers.content_fetcher import ContentFetcher
from processors import DataCleaner, Deduplicator
from storage import JSONStorage
from config.config import Config
from utils.digest_controller import DailyDigestController, DIGEST_JSON_SCHEMA
from utils.mailer import GmailSmtpMailer
from utils.openrouter_client import OpenRouterClient


def run_once():
    """单次运行模式"""
    logger = setup_logger()
    logger.info("🚀 开始单次数据采集...")

    digest_controller = None
    if Config.ENABLE_EMAIL_DIGEST:
        digest_controller = DailyDigestController(
            window_hours=Config.DIGEST_WINDOW_HOURS
        )

    # 验证配置
    try:
        Config.validate()
    except ValueError as e:
        logger.error(f"配置错误: {e}")
        logger.error("请检查.env文件中的API密钥配置")
        sys.exit(1)

    # 初始化组件
    scrapers = []

    if Config.ENABLE_TAVILY:
        try:
            scrapers.append(TavilyScraper())
        except Exception as e:
            logger.warning(f"Tavily爬虫初始化失败: {e}")

    if Config.ENABLE_YFINANCE:
        try:
            scrapers.append(YFinanceScraper())
        except Exception as e:
            logger.warning(f"YFinance爬虫初始化失败: {e}")

    if Config.ENABLE_RSS:
        try:
            scrapers.append(RSSFeedScraper())
        except Exception as e:
            logger.warning(f"RSS爬虫初始化失败: {e}")

    if Config.ENABLE_FRED:
        try:
            scrapers.append(FREDScraper())
        except Exception as e:
            logger.warning(f"FRED爬虫初始化失败: {e}")

    if Config.ENABLE_ALPHA_VANTAGE:
        try:
            scrapers.append(AlphaVantageScraper())
        except Exception as e:
            logger.warning(f"AlphaVantage爬虫初始化失败: {e}")

    if not scrapers:
        logger.error("没有可用的数据源! 请检查配置和API密钥")
        sys.exit(1)

    cleaner = DataCleaner()
    deduplicator = Deduplicator()
    storage = JSONStorage()
    content_fetcher = ContentFetcher()

    # 执行管道
    all_data = []
    for scraper in scrapers:
        data = scraper.run()
        all_data.extend(data)

    logger.info(f"✅ 数据抓取完成 - 总计 {len(all_data)} 条原始记录")

    # 数据清洗和去重
    cleaned_data = cleaner.clean(all_data)
    unique_data = deduplicator.deduplicate(cleaned_data)

    # 抓取完整新闻内容
    logger.info(f"🔍 开始抓取 {len(unique_data)} 条新闻的完整内容...")
    enriched_data = content_fetcher.enrich_articles(unique_data)

    storage.save_raw(all_data)
    storage.save_processed(enriched_data)

    logger.info(f"✅ 完成! 最终数据: {len(enriched_data)} 条")
    logger.info(f"📁 输出目录: {Config.OUTPUT_DIR}")

    if Config.ENABLE_EMAIL_DIGEST and digest_controller is not None:
        try:
            stats = digest_controller.update(enriched_data)
            user_prompt, _ = digest_controller.build_llm_input(
                include_full_content=Config.DIGEST_INCLUDE_FULL_CONTENT,
                max_full_content_chars_per_article=Config.DIGEST_FULL_CONTENT_MAX_CHARS_PER_ARTICLE,
            )

            logger.info(
                f"📧 邮件摘要: window={stats.window_hours}h records={stats.total_records}"
            )

            if not Config.OPENROUTER_API_KEY:
                raise ValueError("OPENROUTER_API_KEY is required")

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
                response_format={
                    "type": "json_schema",
                    "json_schema": DIGEST_JSON_SCHEMA,
                },
                reasoning_effort="high",
            )

            content = (
                resp.get("choices", [{}])[0].get("message", {}).get("content")
                if isinstance(resp, dict)
                else None
            )

            digest = None
            if isinstance(content, str):
                try:
                    digest = json.loads(content)
                except Exception:
                    digest = None

            subject = "FinNews Digest"
            html_body = "<p>Digest generation failed.</p>"
            if isinstance(digest, dict):
                subject = str(digest.get("subject") or subject)
                html_body = str(digest.get("html_body") or html_body)

            if not Config.SMTP_USERNAME or not Config.SMTP_PASSWORD:
                raise ValueError("SMTP_USERNAME/SMTP_PASSWORD is required")
            if not Config.EMAIL_FROM:
                raise ValueError("EMAIL_FROM is required")

            to_list = [e.strip() for e in Config.EMAIL_TO.split(",") if e.strip()]
            mailer = GmailSmtpMailer(
                host=Config.SMTP_HOST,
                port=Config.SMTP_PORT,
                username=Config.SMTP_USERNAME,
                password=Config.SMTP_PASSWORD,
                use_tls=Config.SMTP_USE_TLS,
            )
            mailer.send_html(
                subject=subject,
                html_body=html_body,
                email_from=Config.EMAIL_FROM,
                to_list=to_list,
            )
            logger.info(f"📧 邮件摘要发送完成: to={len(to_list)}")

        except Exception as e:
            logger.error(f"邮件摘要发送失败: {e}", exc_info=True)


def run_scheduled():
    """定时调度运行模式"""
    logger = setup_logger()
    logger.info("⏰ 启动定时调度模式...")

    # 验证配置
    try:
        Config.validate()
    except ValueError as e:
        logger.error(f"配置错误: {e}")
        logger.error("请检查.env文件中的API密钥配置")
        sys.exit(1)

    try:
        scheduler = JobScheduler()
        scheduler.start()
    except ImportError as e:
        logger.error(f"依赖缺失: {e}")
        logger.error("请运行: pip install -r requirements.txt")
        sys.exit(1)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="FinNews - 黄金白银走势分析数据采集系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py --mode once        # 单次运行
  python main.py --mode scheduled   # 定时调度运行
        """,
    )

    parser.add_argument(
        "--mode",
        choices=["once", "scheduled"],
        default="once",
        help="运行模式: once(单次) 或 scheduled(定时)",
    )

    args = parser.parse_args()

    try:
        if args.mode == "once":
            run_once()
        else:
            run_scheduled()
    except KeyboardInterrupt:
        print("\n程序已终止")
        sys.exit(0)
    except Exception as e:
        print(f"\n错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
