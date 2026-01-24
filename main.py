"""
FinNews - 黄金白银走势分析数据管道
主程序入口 - 单次执行，输出6段式邮件摘要
"""

import sys
import json
import time
from datetime import datetime

from utils.logger import setup_logger
from scrapers import (
    TavilyScraper,
    YFinanceScraper,
    RSSFeedScraper,
    FREDScraper,
    AlphaVantageScraper,
    EtfScraper,
    ComexScraper,
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


def send_email_with_retry(
    mailer: GmailSmtpMailer,
    subject: str,
    html_body: str,
    email_from: str,
    to_list: list,
    max_retries: int = 3,
    logger=None,
    images=None,
) -> bool:
    """
    带重试的邮件发送

    Args:
        mailer: 邮件发送器实例
        subject: 邮件标题
        html_body: HTML正文
        email_from: 发件人
        to_list: 收件人列表
        max_retries: 最大重试次数
        logger: 日志记录器
        images: 内嵌图片字典 {id: base64_data}

    Returns:
        发送是否成功
    """
    for attempt in range(1, max_retries + 1):
        try:
            mailer.send_html(
                subject=subject,
                html_body=html_body,
                email_from=email_from,
                to_list=to_list,
                images=images,
            )
            if logger:
                logger.info(f"📧 邮件发送成功: to={len(to_list)}")
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
    logger.info("🚀 FinNews 数据管道启动...")
    logger.info(f"⏰ 执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # ========================================
    # 1. 验证配置
    # ========================================
    try:
        Config.validate()
        logger.info("✅ 配置验证通过")
    except ValueError as e:
        logger.error(f"❌ 配置错误: {e}")
        logger.error("请检查.env文件中的API密钥和邮件配置")
        sys.exit(1)

    # ========================================
    # 2. 初始化数据源
    # ========================================
    scrapers = []

    if Config.ENABLE_TAVILY:
        try:
            scrapers.append(TavilyScraper())
            logger.info("  ✓ Tavily 爬虫就绪")
        except Exception as e:
            logger.warning(f"  ✗ Tavily爬虫初始化失败: {e}")

    if Config.ENABLE_YFINANCE:
        try:
            scrapers.append(YFinanceScraper())
            logger.info("  ✓ YFinance 爬虫就绪")
        except Exception as e:
            logger.warning(f"  ✗ YFinance爬虫初始化失败: {e}")

    if Config.ENABLE_RSS:
        try:
            scrapers.append(RSSFeedScraper())
            logger.info("  ✓ RSS 爬虫就绪")
        except Exception as e:
            logger.warning(f"  ✗ RSS爬虫初始化失败: {e}")

    if Config.ENABLE_FRED:
        try:
            scrapers.append(FREDScraper())
            logger.info("  ✓ FRED 爬虫就绪")
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
    # 3. 数据采集
    # ========================================
    logger.info("=" * 50)
    logger.info("📥 开始数据采集...")
    all_data = []

    for scraper in scrapers:
        try:
            data = scraper.run()
            all_data.extend(data)
            logger.info(f"  → {scraper.name}: {len(data)} 条记录")
        except Exception as e:
            logger.error(f"  → {scraper.name} 采集失败: {e}")

    logger.info(f"✅ 数据采集完成 - 总计 {len(all_data)} 条原始记录")

    # ========================================
    # 4. 数据清洗和去重
    # ========================================
    logger.info("=" * 50)
    logger.info("🧹 数据清洗和去重...")

    cleaner = DataCleaner()
    deduplicator = Deduplicator()

    cleaned_data = cleaner.clean(all_data)
    logger.info(f"  → 清洗后: {len(cleaned_data)} 条")

    unique_data = deduplicator.deduplicate(cleaned_data)
    logger.info(f"  → 去重后: {len(unique_data)} 条")

    # 抓取完整新闻内容
    content_fetcher = ContentFetcher()
    logger.info(f"🔍 抓取 {len(unique_data)} 条新闻的完整内容...")
    enriched_data = content_fetcher.enrich_articles(unique_data)

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
    market_signal = rule_engine.analyze(price_data)

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
    multi_window_data = market_analyzer.organize_data(enriched_data, market_signal)

    logger.info(
        f"  → Flash新闻: {len(multi_window_data.flash.news)} 条 "
        f"| Cycle新闻: {len(multi_window_data.cycle.news)} 条 "
        f"| Trend新闻: {len(multi_window_data.trend.news)} 条"
    )

    # ========================================
    # 7. 构建LLM输入并生成邮件
    # ========================================
    logger.info("=" * 50)
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
2. 从新闻中筛选5-8条最重要的作为重点新闻 (key_news)
3. 将其他相关新闻放入其他新闻 (other_news)  
4. 撰写市场分析 (analysis)

重要规则:
- 所有英文新闻标题和摘要必须翻译成中文
- 新闻只陈述事实，不要添加任何分析性语言
- 所有分析、判断、建议必须放在analysis字段
- 使用中文，专业但易懂
- 严格按照JSON Schema返回结果"""

    try:
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
        email_images = None
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

    except Exception as e:
        logger.error(f"LLM调用失败: {e}", exc_info=True)
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
        email_images = None

    # ========================================
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

    # ========================================
    # 9. 完成
    # ========================================
    logger.info("=" * 50)

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
