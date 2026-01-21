"""
APScheduler定时任务
支持: 定时运行、错误恢复
"""

from datetime import datetime
import logging
import json

try:
    from apscheduler.schedulers.blocking import BlockingScheduler
    from apscheduler.triggers.interval import IntervalTrigger

    APSCHEDULER_AVAILABLE = True
except ImportError:
    BlockingScheduler = None
    IntervalTrigger = None
    APSCHEDULER_AVAILABLE = False

from scrapers import (
    TavilyScraper,
    YFinanceScraper,
    RSSFeedScraper,
    FREDScraper,
    AlphaVantageScraper,
)
from processors import DataCleaner, Deduplicator
from storage import JSONStorage
from config.config import Config
from scrapers.content_fetcher import ContentFetcher
from utils.digest_controller import DailyDigestController, DIGEST_JSON_SCHEMA
from utils.mailer import GmailSmtpMailer
from utils.openrouter_client import OpenRouterClient

logger = logging.getLogger("scheduler")


class JobScheduler:
    """任务调度器"""

    def __init__(self):
        if not APSCHEDULER_AVAILABLE:
            raise ImportError("APScheduler未安装。请运行: pip install APScheduler")

        if BlockingScheduler is None:
            raise ImportError("APScheduler未正确加载")

        self.scheduler = BlockingScheduler()

        # 初始化爬虫(仅添加已启用的)
        self.scrapers = []
        if Config.ENABLE_TAVILY:
            try:
                self.scrapers.append(TavilyScraper())
            except Exception as e:
                logger.warning(f"Tavily爬虫初始化失败: {e}")

        if Config.ENABLE_YFINANCE:
            try:
                self.scrapers.append(YFinanceScraper())
            except Exception as e:
                logger.warning(f"YFinance爬虫初始化失败: {e}")

        if Config.ENABLE_RSS:
            try:
                self.scrapers.append(RSSFeedScraper())
            except Exception as e:
                logger.warning(f"RSS爬虫初始化失败: {e}")

        if Config.ENABLE_FRED:
            try:
                self.scrapers.append(FREDScraper())
            except Exception as e:
                logger.warning(f"FRED爬虫初始化失败: {e}")

        if Config.ENABLE_ALPHA_VANTAGE:
            try:
                self.scrapers.append(AlphaVantageScraper())
            except Exception as e:
                logger.warning(f"AlphaVantage爬虫初始化失败: {e}")

        self.cleaner = DataCleaner()
        self.deduplicator = Deduplicator()
        self.storage = JSONStorage()
        self.content_fetcher = ContentFetcher()

        self.digest_controller = None
        if Config.ENABLE_EMAIL_DIGEST:
            self.digest_controller = DailyDigestController(
                window_hours=Config.DIGEST_WINDOW_HOURS
            )

    def run_pipeline(self):
        """执行完整数据管道"""
        logger.info("=" * 60)
        logger.info(f"开始数据采集 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60)

        all_data = []

        # 1. 抓取所有数据源
        for scraper in self.scrapers:
            data = scraper.run()
            all_data.extend(data)

        logger.info(f"数据抓取完成 - 总计 {len(all_data)} 条原始记录")

        # 2. 清洗
        cleaned_data = self.cleaner.clean(all_data)

        # 3. 去重
        unique_data = self.deduplicator.deduplicate(cleaned_data)

        # 4. 抓取完整新闻内容(与 once 模式保持一致)
        logger.info(f"🔍 开始抓取 {len(unique_data)} 条新闻的完整内容...")
        enriched_data = self.content_fetcher.enrich_articles(unique_data)

        # 5. 存储
        self.storage.save_raw(all_data)
        self.storage.save_processed(enriched_data)

        if Config.ENABLE_EMAIL_DIGEST and self.digest_controller is not None:
            try:
                stats = self.digest_controller.update(enriched_data)
                user_prompt, _ = self.digest_controller.build_llm_input(
                    include_full_content=Config.DIGEST_INCLUDE_FULL_CONTENT,
                    max_full_content_chars_per_article=Config.DIGEST_FULL_CONTENT_MAX_CHARS_PER_ARTICLE,
                )

                logger.info(
                    f"📧 邮件摘要: window={stats.window_hours}h records={stats.total_records}"
                )

                if not Config.OPENROUTER_API_KEY:
                    raise ValueError("OPENROUTER_API_KEY is required")
                if not Config.SMTP_USERNAME or not Config.SMTP_PASSWORD:
                    raise ValueError("SMTP_USERNAME/SMTP_PASSWORD is required")
                if not Config.EMAIL_FROM:
                    raise ValueError("EMAIL_FROM is required")

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

        logger.info("=" * 60)
        logger.info(f"数据管道完成 - 最终记录数: {len(enriched_data)}")
        logger.info("=" * 60)

    def start(self):
        """启动调度器"""
        # 立即执行一次
        logger.info("执行初始数据采集...")
        self.run_pipeline()

        # 添加定时任务
        if IntervalTrigger is None:
            raise ImportError("APScheduler IntervalTrigger未正确加载")

        self.scheduler.add_job(
            self.run_pipeline,
            trigger=IntervalTrigger(hours=Config.SCHEDULE_INTERVAL_HOURS),
            id="news_scraper",
            name="Financial News Scraper",
            replace_existing=True,
        )

        logger.info(f"⏰ 调度器已启动 - 每{Config.SCHEDULE_INTERVAL_HOURS}小时运行一次")
        logger.info("按 Ctrl+C 停止")

        try:
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("调度器已停止")
