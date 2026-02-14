"""
FinNews - 黄金白银走势分析数据管道
主程序入口 - 单次执行，输出6段式邮件摘要
"""

import sys
import json
import time
from datetime import datetime
from typing import Optional

from utils.logger import setup_logger
from utils.pipeline_monitor import PipelineMonitor
from scrapers import (
    TavilyScraper,
    YFinanceScraper,
    RSSFeedScraper,
    FREDScraper,
    AlphaVantageScraper,
    EtfScraper,
    ComexScraper,
    DuckDuckGoScraper,
    StooqScraper,
    SonarScraper,
)
from scrapers.content_fetcher import ContentFetcher
from processors import DataCleaner, Deduplicator
from storage import JSONStorage
from config.config import Config
from analyzers.rule_engine import RuleEngine
from analyzers.market_analyzer import MarketAnalyzer
from utils.digest_controller import DigestController, DIGEST_JSON_SCHEMA
from utils.mailer import GmailSmtpMailer
from utils.openrouter_client import OpenRouterClient
from utils.price_cache_manager import PriceCacheManager


def send_email_with_retry(
    mailer: GmailSmtpMailer,
    subject: str,
    email_from: str,
    to_list: list,
    max_retries: int = 3,
    logger=None,
    html_body: Optional[str] = None,
    plain_body: Optional[str] = None,
    images=None,
) -> bool:
    """
    带重试的邮件发送（支持纯文本和HTML两种模式）

    Args:
        mailer: 邮件发送器实例
        subject: 邮件标题
        email_from: 发件人
        to_list: 收件人列表
        max_retries: 最大重试次数
        logger: 日志记录器
        html_body: HTML正文（可选）
        plain_body: 纯文本正文（可选）
        images: 内嵌图片字典 {id: base64_data}（仅用于HTML邮件）

    Returns:
        发送是否成功
    """
    # 确定邮件类型
    if plain_body and not html_body:
        mail_type = "plain"
    elif html_body:
        mail_type = "html"
    else:
        raise ValueError("必须提供 html_body 或 plain_body 之一")

    for attempt in range(1, max_retries + 1):
        try:
            if mail_type == "plain":
                assert plain_body is not None
                mailer.send_plain(
                    subject=subject,
                    plain_body=plain_body,
                    email_from=email_from,
                    to_list=to_list,
                )
            else:  # mail_type == "html"
                assert html_body is not None
                mailer.send_html(
                    subject=subject,
                    html_body=html_body,
                    email_from=email_from,
                    to_list=to_list,
                    images=images,
                )
            if logger:
                logger.info(f"📧 {mail_type.upper()}邮件发送成功: to={len(to_list)}")
            return True
        except Exception as e:
            if logger:
                logger.warning(f"邮件发送失败 (尝试 {attempt}/{max_retries}): {e}")
            if attempt < max_retries:
                wait_time = 2**attempt  # 指数退避: 2, 4, 8 秒
                time.sleep(wait_time)
            else:
                if logger:
                    logger.error(f"邮件发送最终失败，已重试{max_retries}次")
                return False
    return False


def main():
    """主函数 - 单次执行全流程"""
    logger = setup_logger()
    monitor = PipelineMonitor()
    logger.info("🚀 FinNews 数据管道启动...")
    logger.info(f"⏰ 执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # ========================================
    # 1. 验证配置
    # ========================================
    try:
        monitor.start_step("环境验证")
        start_time = time.time()
        Config.validate()
        logger.info("✅ 配置验证通过")
        monitor.report_module("配置验证", True, duration=time.time() - start_time)
    except ValueError as e:
        logger.error(f"❌ 配置错误: {e}")
        monitor.report_module("配置验证", False, error=str(e))
        logger.error("请检查.env文件中的API密钥和邮件配置")
        sys.exit(1)

    # ========================================
    monitor.start_step("初始化数据源")
    # 2. 初始化数据源
    # ========================================
    scrapers = []

    if Config.ENABLE_TAVILY:
        try:
            start_time = time.time()
            scrapers.append(TavilyScraper())
            logger.info("  ✓ Tavily 爬虫就绪")
            monitor.report_module(
                "Init_Tavily", True, duration=time.time() - start_time
            )
        except Exception as e:
            logger.warning(f"  ✗ Tavily爬虫初始化失败: {e}")

    if Config.ENABLE_DDG:
        try:
            start_time = time.time()
            scrapers.append(DuckDuckGoScraper())
            logger.info("  ✓ DuckDuckGo 爬虫就绪")
            monitor.report_module("Init_DDG", True, duration=time.time() - start_time)
        except Exception as e:
            logger.warning(f"  ✗ DuckDuckGo爬虫初始化失败: {e}")

    if Config.ENABLE_SONAR:
        try:
            start_time = time.time()
            scrapers.append(SonarScraper())
            logger.info("  ✓ Sonar 爬虫就绪")
            monitor.report_module("Init_Sonar", True, duration=time.time() - start_time)
        except Exception as e:
            logger.warning(f"  ✗ Sonar爬虫初始化失败: {e}")

    if Config.ENABLE_YFINANCE:
        try:
            start_time = time.time()
            scrapers.append(YFinanceScraper())
            logger.info("  ✓ YFinance 爬虫就绪")
            monitor.report_module(
                "Init_YFinance", True, duration=time.time() - start_time
            )
        except Exception as e:
            logger.warning(f"  ✗ YFinance爬虫初始化失败: {e}")

    if Config.ENABLE_RSS:
        try:
            start_time = time.time()
            scrapers.append(RSSFeedScraper())
            logger.info("  ✓ RSS 爬虫就绪")
            monitor.report_module("Init_RSS", True, duration=time.time() - start_time)
        except Exception as e:
            logger.warning(f"  ✗ RSS爬虫初始化失败: {e}")

    if Config.ENABLE_FRED:
        try:
            start_time = time.time()
            scrapers.append(FREDScraper())
            logger.info("  ✓ FRED 爬虫就绪")
            monitor.report_module("Init_FRED", True, duration=time.time() - start_time)
        except Exception as e:
            logger.warning(f"  ✗ FRED爬虫初始化失败: {e}")

    if Config.ENABLE_ALPHA_VANTAGE:
        try:
            scrapers.append(AlphaVantageScraper())
            logger.info("  ✓ AlphaVantage 爬虫就绪")
        except Exception as e:
            logger.warning(f"  ✗ AlphaVantage爬虫初始化失败: {e}")

    if Config.ENABLE_ETF:
        try:
            scrapers.append(EtfScraper())
            logger.info("  ✓ ETF 爬虫就绪")
        except Exception as e:
            logger.warning(f"  ✗ ETF爬虫初始化失败: {e}")

    # COMEX 爬虫单独处理 (用于库存预警，数据不混入新闻流)
    comex_scraper = None
    if getattr(Config, "ENABLE_COMEX", True):
        try:
            comex_scraper = ComexScraper()
            logger.info("  ✓ COMEX 爬虫就绪")
        except Exception as e:
            logger.warning(f"  ✗ COMEX爬虫初始化失败: {e}")

    if not scrapers:
        logger.error("❌ 没有可用的数据源! 请检查配置和API密钥")
        sys.exit(1)

    logger.info(f"📡 已初始化 {len(scrapers)} 个数据源")

    # ========================================
    monitor.start_step("数据采集")
    # 3. 数据采集
    # ========================================
    logger.info("=" * 50)
    logger.info("📥 开始数据采集...")
    all_data = []

    for scraper in scrapers:
        start_time = time.time()
        try:
            data = scraper.run()
            all_data.extend(data)
            logger.info(f"  → {scraper.name}: {len(data)} 条记录")
            monitor.report_module(
                scraper.name, True, count=len(data), duration=time.time() - start_time
            )
        except Exception as e:
            logger.error(f"  → {scraper.name} 采集失败: {e}")
            monitor.report_module(
                scraper.name, False, error=str(e), duration=time.time() - start_time
            )

    logger.info(f"✅ 数据采集完成 - 总计 {len(all_data)} 条原始记录")

    # ========================================
    monitor.start_step("价格数据补全")
    # 3.5 价格数据补全 (Failover Pipeline)
    # ========================================
    logger.info("=" * 50)
    logger.info("🛠️ 价格数据补全 (Failover)...")

    cache_manager = PriceCacheManager()
    required_tickers = list(Config.YFINANCE_TICKERS.keys())

    # 检查当前已获取的价格数据
    existing_prices = {
        r.get("ticker_name")
        for r in all_data
        if r.get("type") == "price_data" and r.get("price", 0) > 0
    }
    missing_tickers = [t for t in required_tickers if t not in existing_prices]

    if missing_tickers:
        logger.warning(f"  ⚠️ 缺失价格数据: {missing_tickers}，尝试 Stooq 兜底...")
        stooq = StooqScraper()
        # 修改 stooq 的 tickers 仅包含缺失的部分
        stooq.tickers = {
            k: v for k, v in Config.STOOQ_TICKERS.items() if k in missing_tickers
        }
        start_time = time.time()
        stooq_data = stooq.run()
        monitor.report_module(
            "Stooq_Fallback",
            True,
            count=len(stooq_data),
            duration=time.time() - start_time,
        )

        if stooq_data:
            all_data.extend(stooq_data)
            # 重新检查
            existing_prices.update(
                {
                    r.get("ticker_name")
                    for r in stooq_data
                    if r.get("type") == "price_data" and r.get("price", 0) > 0
                }
            )
            missing_tickers = [t for t in required_tickers if t not in existing_prices]

    if missing_tickers:
        logger.warning(f"  ⚠️ 仍缺失价格数据: {missing_tickers}，尝试本地缓存回退...")
        start_time = time.time()
        fallback_data = cache_manager.get_fallback_records(missing_tickers)
        monitor.report_module(
            "Cache_Fallback",
            True,
            count=len(fallback_data or []),
            duration=time.time() - start_time,
        )
        if fallback_data:
            all_data.extend(fallback_data)
            logger.info(f"  ✓ 已从缓存恢复 {len(fallback_data)} 条价格记录")
    else:
        logger.info("  ✓ 所有关键价格数据已就绪 (Real-time)")

    # 更新缓存 (使用本次运行中所有有效的实时数据)
    fresh_prices = [
        r
        for r in all_data
        if r.get("type") == "price_data" and not r.get("is_fallback")
    ]
    if fresh_prices:
        cache_manager.update(fresh_prices)

    # ========================================
    monitor.start_step("数据处理")
    # 4. 数据清洗和去重
    # ========================================

    logger.info("=" * 50)
    logger.info("🧹 数据清洗和去重...")

    cleaner = DataCleaner()
    deduplicator = Deduplicator()

    start_time = time.time()
    cleaned_data = cleaner.clean(all_data)
    monitor.report_module(
        "DataCleaner", True, count=len(cleaned_data), duration=time.time() - start_time
    )
    logger.info(f"  → 清洗后: {len(cleaned_data)} 条")

    start_time = time.time()
    unique_data = deduplicator.deduplicate(cleaned_data)
    monitor.report_module(
        "Deduplicator", True, count=len(unique_data), duration=time.time() - start_time
    )
    logger.info(f"  → 去重后: {len(unique_data)} 条")

    # 抓取完整新闻内容
    content_fetcher = ContentFetcher()
    logger.info(f"🔍 抓取 {len(unique_data)} 条新闻的完整内容...")
    start_time = time.time()
    enriched_data = content_fetcher.enrich_articles(unique_data)
    monitor.report_module(
        "ContentFetcher",
        True,
        count=len(enriched_data),
        duration=time.time() - start_time,
    )

    # 存储原始数据和处理后数据
    storage = JSONStorage()
    storage.save_raw(all_data)
    storage.save_processed(enriched_data)
    logger.info(f"💾 数据已保存至 {Config.OUTPUT_DIR}")

    # ========================================
    # 5. 规则引擎预处理
    # ========================================
    logger.info("=" * 50)
    logger.info("⚙️ 规则引擎分析...")

    # 提取价格数据供规则引擎使用
    price_data = [r for r in enriched_data if r.get("type") == "price_data"]

    rule_engine = RuleEngine()
    start_time = time.time()
    market_signal = rule_engine.analyze(price_data)
    monitor.report_module("RuleEngine", True, duration=time.time() - start_time)

    # 输出规则引擎结果
    logger.info(f"  → VIX: {market_signal.vix_value or 'N/A'}")
    logger.info(f"  → 黄金: ${market_signal.gold_price or 'N/A'}")
    logger.info(f"  → 白银: ${market_signal.silver_price or 'N/A'}")
    logger.info(f"  → 美元指数: {market_signal.dxy_value or 'N/A'}")
    logger.info(f"  → 10年期国债: {market_signal.us10y_value or 'N/A'}")
    logger.info(f"  → VIX警报: {market_signal.vix_alert_level.value}")
    logger.info(f"  → 宏观倾向: {market_signal.macro_bias.value}")
    logger.info(f"  → 情感评分: {market_signal.sentiment_score:.2f}")
    logger.info(f"  → 紧急警报: {'是' if market_signal.is_urgent else '否'}")

    if market_signal.alert_messages:
        logger.info("  → 警报消息:")
        for msg in market_signal.alert_messages:
            logger.info(f"      {msg}")

    # ========================================
    # 5.5. COMEX库存分析 (独立处理)
    # ========================================
    comex_signal = None
    if comex_scraper:
        logger.info("=" * 50)
        logger.info("🏦 COMEX库存分析...")
        try:
            comex_data = comex_scraper.run()
            if comex_data:
                comex_signal = rule_engine.analyze_comex(comex_data)
                logger.info(
                    f"  → 白银Registered: {comex_signal.silver_registered_million or 'N/A'}M oz"
                )
                logger.info(f"  → 白银预警: {comex_signal.silver_alert_level.value}")
                logger.info(
                    f"  → 黄金Registered: {comex_signal.gold_registered_million or 'N/A'}M oz"
                )
                logger.info(f"  → 黄金预警: {comex_signal.gold_alert_level.value}")
                if comex_signal.has_emergency:
                    logger.warning("  ⚠️ COMEX库存触发紧急警报!")
            else:
                logger.warning("  → COMEX数据获取失败")
        except Exception as e:
            logger.error(f"  → COMEX分析失败: {e}")

    # ========================================
    # 6. 市场分析器组织数据
    # ========================================
    logger.info("=" * 50)
    logger.info("📊 组织多窗口数据...")

    market_analyzer = MarketAnalyzer()
    start_time = time.time()
    multi_window_data = market_analyzer.organize_data(enriched_data, market_signal)
    monitor.report_module("MarketAnalyzer", True, duration=time.time() - start_time)

    logger.info(
        f"  → Flash新闻: {len(multi_window_data.flash.news)} 条 "
        f"| Cycle新闻: {len(multi_window_data.cycle.news)} 条 "
        f"| Trend新闻: {len(multi_window_data.trend.news)} 条"
    )

    # ========================================
    monitor.start_step("邮件生成")
    # 7. 构建LLM输入并生成邮件
    # ========================================
    logger.info("=" * 50)

    # 根据配置选择邮件内容类型
    email_content_type = Config.EMAIL_CONTENT_TYPE
    logger.info(f"📧 邮件内容类型: {email_content_type}")

    if email_content_type == "plain_text":
        # 使用纯文本格式（build_email_prompt）
        logger.info("📝 使用纯文本邮件格式（包含 COMEX ASCII 表格）...")

        try:
            start_time = time.time()

            # 生成纯文本邮件内容
            email_plain = market_analyzer.build_email_prompt(
                data=multi_window_data,
                signal=market_signal,
                comex_signal=comex_signal,
                mode=Config.EMAIL_FORMAT_MODE,
            )

            # 生成邮件标题
            tag = market_signal.get_email_subject_tag()
            summary = market_signal.get_signal_summary()
            date_str = datetime.now().strftime("%m/%d")
            email_subject = f"{tag} {date_str} {summary}"

            logger.info(f"✅ 纯文本邮件生成完成: {len(email_plain)} 字符")
            logger.info(f"   标题: {email_subject}")

            # 纯文本邮件不使用图片
            email_html = None
            email_images = None

            monitor.report_module(
                "EmailGenerator", True, duration=time.time() - start_time
            )

        except Exception as e:
            logger.error(f"纯文本邮件生成失败: {e}", exc_info=True)
            monitor.report_module(
                "EmailGenerator", False, error=str(e), duration=time.time() - start_time
            )

            # 备用方案
            email_subject = (
                f"【系统错误】FinNews {datetime.now().strftime('%m/%d')} 生成失败"
            )
            email_plain = f"""FinNews 系统错误

邮件生成失败: {str(e)}
时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

规则引擎信号:
- VIX: {market_signal.vix_value or "N/A"}
- 警报级别: {market_signal.vix_alert_level.value}
- 宏观倾向: {market_signal.macro_bias.value}
"""
            email_html = None
            email_images = None

    else:
        # 使用 HTML 格式（原有的 LLM + 模板方式）
        logger.info("🤖 调用LLM生成邮件内容...")

        digest_controller = DigestController()
        user_prompt, stats = digest_controller.build_llm_prompt(
            multi_window_data, market_signal
        )

        # 初始化OpenRouter客户端
        # Config.validate() 已确保 OPENROUTER_API_KEY 存在
        assert Config.OPENROUTER_API_KEY is not None
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
2. 从新闻中筛选恰好5条最重要的作为重点新闻 (key_news) - 注意是恰好5条，不多不少
3. 筛选最多5条其他值得关注的新闻 (other_news)，低相关性的直接丢弃
4. 撰写精简的市场分析 (analysis) — 每项30-60字，用要点式

重要规则:
- 所有英文新闻标题和摘要必须翻译成中文
- 新闻只陈述事实，不要添加任何分析性语言
- 所有分析、判断、建议必须放在analysis字段
- 每条新闻必须包含6个字段: title, source, summary, url, impact_tag, timestamp
- url和timestamp若原始数据中无，则填空字符串
- 使用中文，专业但易懂
- 严格按照JSON Schema返回结果"""

        try:
            start_time = time.time()
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

            # 解析LLM响应
            content = (
                resp.get("choices", [{}])[0].get("message", {}).get("content")
                if isinstance(resp, dict)
                else None
            )

            digest_data = None
            if isinstance(content, str):
                try:
                    digest_data = json.loads(content)
                    logger.debug(
                        f"LLM返回数据: subject={digest_data.get('subject', 'N/A')[:50]}, "
                        f"key_news={len(digest_data.get('key_news', []))}, "
                        f"other_news={len(digest_data.get('other_news', []))}"
                    )
                except json.JSONDecodeError as e:
                    logger.error(f"LLM响应JSON解析失败: {e}")

            # 使用模板渲染HTML
            if isinstance(digest_data, dict):
                email_subject = digest_data.get("subject", "")
                email_html, email_images = digest_controller.render_email_html(
                    digest_data=digest_data,
                    signal=market_signal,
                    data=multi_window_data,
                    comex_signal=comex_signal,
                )
            else:
                email_subject = ""
                email_html = ""
                email_images = None

            # 备用方案
            if not email_subject:
                email_subject = digest_controller.get_email_subject(market_signal)

            if not email_html:
                logger.warning("LLM数据解析失败，使用备用邮件内容")
                email_html = f"""<!DOCTYPE html>
<html><body style="font-family: Arial, sans-serif; padding: 20px;">
<h1>FinNews 邮件生成失败</h1>
<p>LLM未能生成有效的数据。</p>
<p>时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
<h2>规则引擎信号</h2>
<ul>
    <li>VIX: {market_signal.vix_value or "N/A"}</li>
    <li>警报级别: {market_signal.vix_alert_level.value}</li>
    <li>宏观倾向: {market_signal.macro_bias.value}</li>
</ul>
</body></html>"""
                email_images = None  # 备用模式无图片

            logger.info(f"✅ 邮件生成完成: {email_subject[:50]}...")

            # HTML 模式下，email_plain 设为 None
            email_plain = None

            monitor.report_module("LLM_Chat", True, duration=time.time() - start_time)

        except Exception as e:
            logger.error(f"LLM调用失败: {e}", exc_info=True)
            monitor.report_module(
                "LLM_Chat", False, error=str(e), duration=time.time() - start_time
            )
            # 生成错误通知邮件
            email_subject = (
                f"【系统错误】FinNews {datetime.now().strftime('%m/%d')} 生成失败"
            )
            email_html = f"""
            <html>
            <body>
            <h1>FinNews 系统错误</h1>
            <p>LLM调用失败: {str(e)}</p>
            <p>时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            </body>
            </html>
            """
            email_plain = None
            email_images = None

    # ========================================
    monitor.start_step("邮件发送")
    # 8. 发送邮件 (3次重试)
    # ========================================
    logger.info("=" * 50)
    logger.info("📧 发送邮件...")

    to_list = [e.strip() for e in Config.EMAIL_TO.split(",") if e.strip()]

    # Config.validate() 已确保 SMTP 和 EMAIL 配置存在
    assert Config.SMTP_USERNAME is not None
    assert Config.SMTP_PASSWORD is not None
    assert Config.EMAIL_FROM is not None

    mailer = GmailSmtpMailer(
        host=Config.SMTP_HOST,
        port=Config.SMTP_PORT,
        username=Config.SMTP_USERNAME,
        password=Config.SMTP_PASSWORD,
        use_tls=Config.SMTP_USE_TLS,
    )

    start_time = time.time()

    # 根据邮件内容类型选择发送方式
    if email_content_type == "plain_text":
        email_sent = send_email_with_retry(
            mailer=mailer,
            subject=email_subject,
            plain_body=email_plain,
            email_from=Config.EMAIL_FROM,
            to_list=to_list,
            max_retries=3,
            logger=logger,
        )
    else:  # html
        email_sent = send_email_with_retry(
            mailer=mailer,
            subject=email_subject,
            html_body=email_html,
            email_from=Config.EMAIL_FROM,
            to_list=to_list,
            max_retries=3,
            logger=logger,
            images=email_images,
        )

    monitor.report_module(
        "GmailSmtpMailer", email_sent, duration=time.time() - start_time
    )

    # ========================================
    # 9. 完成
    # ========================================
    logger.info("=" * 50)

    logger.info(monitor.get_summary())
    if email_sent:
        logger.info("🎉 FinNews 执行完成!")
        logger.info(f"📧 邮件已发送至: {', '.join(to_list)}")
        sys.exit(0)
    else:
        logger.error("❌ FinNews 执行失败 - 邮件发送失败")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n程序已终止")
        sys.exit(0)
    except Exception as e:
        print(f"\n致命错误: {e}")
        sys.exit(1)
