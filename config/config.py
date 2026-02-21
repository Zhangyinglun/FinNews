"""
统一配置管理
支持环境变量和默认值
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


def _clean_env_value(value: str | None) -> str:
    """
    清理环境变量值，移除 BOM 和首尾空格

    Args:
        value: 环境变量值

    Returns:
        清理后的字符串
    """
    if value is None:
        return ""
    # 移除 BOM (Byte Order Mark) 字符和首尾空格
    return value.strip("\ufeff").strip()


def _getenv_int(key: str, default: str) -> int:
    """
    安全地获取整数类型的环境变量

    Args:
        key: 环境变量键名
        default: 默认值（字符串形式）

    Returns:
        整数值
    """
    value = os.getenv(key, default)
    return int(_clean_env_value(value))


def _getenv_float(key: str, default: str) -> float:
    """
    安全地获取浮点数类型的环境变量

    Args:
        key: 环境变量键名
        default: 默认值（字符串形式）

    Returns:
        浮点数值
    """
    value = os.getenv(key, default)
    return float(_clean_env_value(value))


def _getenv_bool(key: str, default: str) -> bool:
    """
    安全地获取布尔类型的环境变量

    Args:
        key: 环境变量键名
        default: 默认值（字符串形式）

    Returns:
        布尔值
    """
    value = os.getenv(key, default)
    return _clean_env_value(value).lower() == "true"


def _getenv_str(key: str, default: str = "") -> str:
    """
    安全地获取字符串类型的环境变量

    Args:
        key: 环境变量键名
        default: 默认值（如果为空字符串,返回原始 None）

    Returns:
        清理后的字符串（如果有默认值则保证非 None）
    """
    value = os.getenv(key)
    if value is None or value == "":
        return default
    return _clean_env_value(value)


def _getenv_str_optional(key: str) -> str | None:
    """
    安全地获取可选的字符串类型的环境变量（可能返回 None）

    Args:
        key: 环境变量键名

    Returns:
        清理后的字符串或 None
    """
    value = os.getenv(key)
    if value is None or value == "":
        return None
    return _clean_env_value(value)


class Config:
    """全局配置类"""

    # ========================================
    # 项目路径
    # ========================================
    BASE_DIR = Path(__file__).resolve().parent.parent
    OUTPUT_DIR = BASE_DIR / "outputs"
    RAW_DIR = OUTPUT_DIR / "raw"
    PROCESSED_DIR = OUTPUT_DIR / "processed"
    LOG_DIR = OUTPUT_DIR / "logs"
    STORAGE_DIR = OUTPUT_DIR / "storage"

    # ========================================
    # API密钥
    # ========================================
    TAVILY_API_KEY = _getenv_str_optional("TAVILY_API_KEY")
    FRED_API_KEY = _getenv_str_optional("FRED_API_KEY")
    ALPHA_VANTAGE_API_KEY = _getenv_str_optional("ALPHA_VANTAGE_API_KEY")

    # ========================================
    # 数据源开关
    # ========================================
    ENABLE_TAVILY = _getenv_bool("ENABLE_TAVILY", "true")
    ENABLE_DDG = _getenv_bool("ENABLE_DDG", "true")
    DDG_REGION = _getenv_str("DDG_REGION", "us-en")
    DDG_BACKEND = _getenv_str("DDG_BACKEND", "auto")
    DDG_MAX_RESULTS = _getenv_int("DDG_MAX_RESULTS", "5")
    ENABLE_YFINANCE = _getenv_bool("ENABLE_YFINANCE", "true")
    ENABLE_RSS = _getenv_bool("ENABLE_RSS", "true")
    ENABLE_FRED = _getenv_bool("ENABLE_FRED", "true")
    ENABLE_ALPHA_VANTAGE = _getenv_bool("ENABLE_ALPHA_VANTAGE", "false")
    ENABLE_ETF = _getenv_bool("ENABLE_ETF", "true")

    # ========================================
    # 多时间窗口配置
    # ========================================
    FLASH_WINDOW_HOURS = _getenv_int("FLASH_WINDOW_HOURS", "12")  # 即时窗口(12小时)

    CYCLE_WINDOW_DAYS = _getenv_int("CYCLE_WINDOW_DAYS", "7")  # 周度窗口(7天)
    TREND_WINDOW_DAYS = _getenv_int("TREND_WINDOW_DAYS", "30")  # 月度窗口(30天)

    # ========================================
    # RSS订阅源配置
    # ========================================
    RSS_FEEDS = {
        "mining_com": "https://www.mining.com/feed/",
        "fxstreet_commodities": "https://www.fxstreet.com/rss/news/commodities/gold",
        "investing_commodities": "https://www.investing.com/rss/commodities.rss",
        "zerohedge": "http://feeds.feedburner.com/zerohedge/feed",
        "kitco_gold": "https://www.kitco.com/rss/category/commodities/gold",
        "cnbc_commodities": "https://www.cnbc.com/id/10000086/device/rss/rss.html",
        "dailyfx_market_news": "https://www.dailyfx.com/feeds/market-news",
    }

    # ========================================
    # yfinance监控股票代码 (含VIX)
    # ========================================
    YFINANCE_TICKERS = {
        "vix": "^VIX",  # VIX恐慌指数 (新增)
        "dollar_index": "DX-Y.NYB",  # 美元指数
        "treasury_10y": "^TNX",  # 10年期国债收益率
        "gold_futures": "GC=F",  # 黄金期货
        "silver_futures": "SI=F",  # 白银期货
    }

    # ========================================
    # Stooq Tickers (兜底数据源)
    # ========================================
    STOOQ_TICKERS = {
        "vix": "^VIX",  # VIX恐慌指数
        "dollar_index": "DX.F",  # 美元指数 (Stooq格式)
        "treasury_10y": "10USY.B",  # 10年期国债收益率 (Stooq格式)
        "gold_futures": "GC.F",  # 黄金期货
        "silver_futures": "SI.F",  # 白银期货
    }

    # ========================================
    # 规则引擎阈值配置
    # ========================================
    VIX_ALERT_THRESHOLD = _getenv_float("VIX_ALERT_THRESHOLD", "20")  # VIX绝对值警戒线
    VIX_SPIKE_PERCENT = _getenv_float("VIX_SPIKE_PERCENT", "5")  # VIX暴涨百分比阈值
    DXY_CHANGE_THRESHOLD = _getenv_float(
        "DXY_CHANGE_THRESHOLD", "0.5"
    )  # DXY显著变化阈值(%)
    US10Y_CHANGE_THRESHOLD = _getenv_float(
        "US10Y_CHANGE_THRESHOLD", "2"
    )  # 10Y收益率变化阈值(%)

    # ========================================
    # COMEX库存监控配置
    # ========================================
    ENABLE_COMEX = _getenv_bool("ENABLE_COMEX", "true")

    # 白银三级预警阈值 (单位: 盎司)
    # 🟢 安全: >= 40M oz
    # 🟡 警戒线: < 40M oz (市场紧张)
    # 🔴 生死线: < 30M oz (脱钩风险)
    # ⚫ 熔断线: < 20M oz (系统性风险)
    COMEX_SILVER_YELLOW_THRESHOLD = _getenv_int(
        "COMEX_SILVER_YELLOW_THRESHOLD", "40000000"
    )  # 4000万盎司
    COMEX_SILVER_RED_THRESHOLD = _getenv_int(
        "COMEX_SILVER_RED_THRESHOLD", "30000000"
    )  # 3000万盎司
    COMEX_SILVER_FAILURE_THRESHOLD = _getenv_int(
        "COMEX_SILVER_FAILURE_THRESHOLD", "20000000"
    )  # 2000万盎司

    # 黄金三级预警阈值 (单位: 盎司)
    COMEX_GOLD_YELLOW_THRESHOLD = _getenv_int(
        "COMEX_GOLD_YELLOW_THRESHOLD", "10000000"
    )  # 1000万盎司
    COMEX_GOLD_RED_THRESHOLD = _getenv_int(
        "COMEX_GOLD_RED_THRESHOLD", "5000000"
    )  # 500万盎司
    COMEX_GOLD_FAILURE_THRESHOLD = _getenv_int(
        "COMEX_GOLD_FAILURE_THRESHOLD", "2000000"
    )  # 200万盎司

    # ========================================
    # 邮件格式配置
    # ========================================
    # 邮件内容类型: "plain_text" (纯文本) | "html" (HTML邮件 + LLM摘要)
    EMAIL_CONTENT_TYPE = _getenv_str("EMAIL_CONTENT_TYPE", "html")

    # 纯文本邮件配置
    EMAIL_FORMAT_MODE = _getenv_str("EMAIL_FORMAT_MODE", "full")  # "brief" | "full"
    EMAIL_TOP_NEWS_COUNT = _getenv_int("EMAIL_TOP_NEWS_COUNT", "5")
    EMAIL_MAX_SUMMARY_LENGTH = _getenv_int("EMAIL_MAX_SUMMARY_LENGTH", "80")

    # ========================================
    # Tavily搜索关键词池 - 按时间窗口分组
    # ========================================
    # Flash Window (12小时) - 即时突发

    TAVILY_FLASH_QUERIES = [
        "breaking news geopolitical tension gold silver precious metals",
        "VIX volatility spike market fear risk off",
        "Federal Reserve emergency statement dollar",
    ]

    # Cycle Window (7天) - 周度数据
    TAVILY_CYCLE_QUERIES = [
        "US CPI inflation data release this week",
        "Non-Farm Payrolls NFP employment report",
        "Federal Reserve FOMC interest rate decision",
        "PCE inflation data personal consumption expenditure",
    ]

    # Trend Window (30天) - 月度趋势
    TAVILY_TREND_QUERIES = [
        "Central Bank gold buying reserves monthly",
        "Gold ETF inflows outflows GLD IAU",
        "Silver industrial demand solar panel EV",
        "COMEX gold silver futures positioning",
    ]

    # 可信新闻源域名(用于Tavily过滤)
    TRUSTED_DOMAINS = [
        "reuters.com",
        "bloomberg.com",
        "wsj.com",
        "ft.com",
        "cnbc.com",
        "marketwatch.com",
        "investing.com",
        "kitco.com",
        "fxstreet.com",
    ]

    # Sonar 配置
    ENABLE_SONAR = _getenv_bool("ENABLE_SONAR", "false")
    SONAR_MODEL = _getenv_str("SONAR_MODEL", "perplexity/sonar")
    SONAR_USE_TRUSTED_DOMAINS = _getenv_bool("SONAR_USE_TRUSTED_DOMAINS", "false")

    # ========================================
    # FRED经济指标系列ID
    # ========================================
    FRED_SERIES = {
        # 通胀指标
        "cpi": "CPIAUCSL",  # 消费者价格指数
        "core_cpi": "CPILFESL",  # 核心CPI(除食品能源)
        "pce": "PCEPI",  # 个人消费支出价格指数
        "core_pce": "PCEPILFE",  # 核心PCE
        # 就业指标
        "nonfarm_payroll": "PAYEMS",  # 非农就业人数
        "unemployment": "UNRATE",  # 失业率
        # 利率与国债
        "fed_funds": "FEDFUNDS",  # 联邦基金利率
        "treasury_2y": "DGS2",  # 2年期国债收益率
        "real_interest_rate": "DFII10",  # 10年期实际利率
    }

    # ========================================
    # 关键词过滤配置
    # ========================================

    # 白名单关键词(包含任一即保留)
    WHITELIST_KEYWORDS = [
        # 金融术语
        "inflation",
        "deflation",
        "rates",
        "interest rate",
        "federal reserve",
        "fed",
        "central bank",
        "monetary policy",
        "yield",
        "treasury",
        "bond",
        # 地缘政治
        "geopolitical",
        "war",
        "conflict",
        "sanctions",
        "tension",
        "crisis",
        # 贵金属相关
        "gold",
        "silver",
        "precious metals",
        "bullion",
        "xau",
        "xag",
        "demand",
        "supply",
        # 宏观经济
        "dollar",
        "usd",
        "dxy",
        "currency",
        "gdp",
        "employment",
        "unemployment",
        "cpi",
        "pce",
        "nfp",
        # 市场情绪
        "safe haven",
        "risk off",
        "risk on",
        "volatility",
        "uncertainty",
        "vix",
    ]

    # 黑名单关键词(包含任一即过滤)
    BLACKLIST_KEYWORDS = [
        # 广告/商业
        "jewelry",
        "jewellery",
        "wedding",
        "engagement ring",
        "buy now",
        "discount",
        "sale",
        "promotion",
        # 个股/矿企(非宏观)
        "mining stock",
        "gold stock",
        "equity",
        # 技术图表(LLM难读取)
        "technical chart",
        "candlestick pattern",
        "fibonacci",
        "rsi",
        "macd",
        # 加密货币(干扰项)
        "bitcoin",
        "btc",
        "cryptocurrency",
        "crypto",
        "ethereum",
        "eth",
    ]

    # ========================================
    # 网络配置
    # ========================================
    MAX_RETRIES = _getenv_int("MAX_RETRIES", "3")
    REQUEST_TIMEOUT = _getenv_int("REQUEST_TIMEOUT", "30")

    # ========================================
    # 数据处理配置
    # ========================================
    DEDUPLICATION_WINDOW_HOURS = _getenv_int("DEDUPLICATION_WINDOW_HOURS", "12")

    # ========================================
    # Email Digest (OpenRouter -> Gmail SMTP)
    # ========================================
    DIGEST_WINDOW_HOURS = _getenv_int("DIGEST_WINDOW_HOURS", "12")

    DIGEST_INCLUDE_FULL_CONTENT = _getenv_bool("DIGEST_INCLUDE_FULL_CONTENT", "false")
    DIGEST_FULL_CONTENT_MAX_CHARS_PER_ARTICLE = _getenv_int(
        "DIGEST_FULL_CONTENT_MAX_CHARS_PER_ARTICLE", "2000"
    )

    OPENROUTER_API_KEY = _getenv_str_optional("OPENROUTER_API_KEY")
    OPENROUTER_MODEL = _getenv_str("OPENROUTER_MODEL", "google/gemini-3-pro-preview")
    OPENROUTER_TEMPERATURE = _getenv_float("OPENROUTER_TEMPERATURE", "0.3")
    OPENROUTER_MAX_TOKENS = _getenv_int("OPENROUTER_MAX_TOKENS", "8192")
    OPENROUTER_TIMEOUT = _getenv_int("OPENROUTER_TIMEOUT", "120")
    OPENROUTER_MAX_RETRIES = _getenv_int("OPENROUTER_MAX_RETRIES", "3")
    # 总时限默认使用「单次超时 * 重试次数 + 缓冲」，避免单次请求耗尽全部预算
    OPENROUTER_TOTAL_TIMEOUT = _getenv_int(
        "OPENROUTER_TOTAL_TIMEOUT",
        str(OPENROUTER_TIMEOUT * OPENROUTER_MAX_RETRIES + 10),
    )
    OPENROUTER_REASONING_EFFORT = _getenv_str("OPENROUTER_REASONING_EFFORT", "medium")
    OPENROUTER_HTTP_REFERER = _getenv_str_optional("OPENROUTER_HTTP_REFERER")
    OPENROUTER_X_TITLE = _getenv_str_optional("OPENROUTER_X_TITLE")

    SMTP_HOST = _getenv_str("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = _getenv_int("SMTP_PORT", "587")
    SMTP_USERNAME = _getenv_str_optional("SMTP_USERNAME")
    SMTP_PASSWORD = _getenv_str_optional("SMTP_PASSWORD")
    SMTP_USE_TLS = _getenv_bool("SMTP_USE_TLS", "true")

    EMAIL_FROM = _getenv_str_optional("EMAIL_FROM")
    EMAIL_TO = _getenv_str("EMAIL_TO", "")

    # ========================================
    # 日志配置
    # ========================================
    LOG_LEVEL = _getenv_str("LOG_LEVEL", "INFO")

    # ========================================
    # 初始化方法
    # ========================================
    @classmethod
    def create_directories(cls):
        """创建必要的目录结构"""
        for directory in [cls.RAW_DIR, cls.PROCESSED_DIR, cls.LOG_DIR]:
            directory.mkdir(parents=True, exist_ok=True)

    @classmethod
    def validate(cls):
        """验证配置有效性"""
        errors = []

        # 检查必需的API密钥
        if cls.ENABLE_TAVILY and not cls.TAVILY_API_KEY:
            errors.append("TAVILY_API_KEY未配置(已启用Tavily)")

        if cls.ENABLE_FRED and not cls.FRED_API_KEY:
            errors.append("FRED_API_KEY未配置(已启用FRED)")

        if cls.ENABLE_ALPHA_VANTAGE and not cls.ALPHA_VANTAGE_API_KEY:
            errors.append("ALPHA_VANTAGE_API_KEY未配置(已启用Alpha Vantage)")

        # Email digest 配置 (必需)
        if not cls.OPENROUTER_API_KEY:
            errors.append("OPENROUTER_API_KEY未配置(邮件摘要必需)")

        if not cls.SMTP_USERNAME:
            errors.append("SMTP_USERNAME未配置(邮件发送必需)")
        if not cls.SMTP_PASSWORD:
            errors.append("SMTP_PASSWORD未配置(邮件发送必需)")
        if not cls.EMAIL_FROM:
            errors.append("EMAIL_FROM未配置(邮件发送必需)")

        # 检查 EMAIL_TO
        if not cls.EMAIL_TO:
            errors.append("EMAIL_TO未配置或为空(邮件发送必需)")
        else:
            to_list = [
                email.strip() for email in cls.EMAIL_TO.split(",") if email.strip()
            ]
            if not to_list:
                errors.append("EMAIL_TO未配置或为空(邮件发送必需)")

        if errors:
            raise ValueError(f"配置错误:\n" + "\n".join(f"  - {e}" for e in errors))

        return True


# 初始化目录
Config.create_directories()
