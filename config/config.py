"""
统一配置管理
支持环境变量和默认值
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


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

    # ========================================
    # API密钥
    # ========================================
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
    FRED_API_KEY = os.getenv("FRED_API_KEY")
    ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")

    # ========================================
    # 数据源开关
    # ========================================
    ENABLE_TAVILY = os.getenv("ENABLE_TAVILY", "true").lower() == "true"
    ENABLE_YFINANCE = os.getenv("ENABLE_YFINANCE", "true").lower() == "true"
    ENABLE_RSS = os.getenv("ENABLE_RSS", "true").lower() == "true"
    ENABLE_FRED = os.getenv("ENABLE_FRED", "true").lower() == "true"
    ENABLE_ALPHA_VANTAGE = os.getenv("ENABLE_ALPHA_VANTAGE", "false").lower() == "true"
    ENABLE_ETF = os.getenv("ENABLE_ETF", "true").lower() == "true"

    # ========================================
    # 多时间窗口配置
    # ========================================
    FLASH_WINDOW_HOURS = int(os.getenv("FLASH_WINDOW_HOURS", "12"))  # 即时窗口(12小时)

    CYCLE_WINDOW_DAYS = int(os.getenv("CYCLE_WINDOW_DAYS", "7"))  # 周度窗口(7天)
    TREND_WINDOW_DAYS = int(os.getenv("TREND_WINDOW_DAYS", "30"))  # 月度窗口(30天)

    # ========================================
    # RSS订阅源配置
    # ========================================
    RSS_FEEDS = {
        "kitco_gold": "https://www.kitco.com/rss/KitcoGold.xml",
        "fxstreet_commodities": "https://www.fxstreet.com/rss/news/commodities/gold",
        "investing_commodities": "https://www.investing.com/rss/commodities.rss",
        "zerohedge": "http://feeds.feedburner.com/zerohedge/feed",
        "oilprice": "https://oilprice.com/rss/main",
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
    # 规则引擎阈值配置
    # ========================================
    VIX_ALERT_THRESHOLD = float(
        os.getenv("VIX_ALERT_THRESHOLD", "20")
    )  # VIX绝对值警戒线
    VIX_SPIKE_PERCENT = float(os.getenv("VIX_SPIKE_PERCENT", "5"))  # VIX暴涨百分比阈值
    DXY_CHANGE_THRESHOLD = float(
        os.getenv("DXY_CHANGE_THRESHOLD", "0.5")
    )  # DXY显著变化阈值(%)
    US10Y_CHANGE_THRESHOLD = float(
        os.getenv("US10Y_CHANGE_THRESHOLD", "2")
    )  # 10Y收益率变化阈值(%)

    # ========================================
    # COMEX库存监控配置
    # ========================================
    ENABLE_COMEX = os.getenv("ENABLE_COMEX", "true").lower() == "true"

    # 白银三级预警阈值 (单位: 盎司)
    # 🟢 安全: >= 40M oz
    # 🟡 警戒线: < 40M oz (市场紧张)
    # 🔴 生死线: < 30M oz (脱钩风险)
    # ⚫ 熔断线: < 20M oz (系统性风险)
    COMEX_SILVER_YELLOW_THRESHOLD = int(
        os.getenv("COMEX_SILVER_YELLOW_THRESHOLD", "40000000")
    )  # 4000万盎司
    COMEX_SILVER_RED_THRESHOLD = int(
        os.getenv("COMEX_SILVER_RED_THRESHOLD", "30000000")
    )  # 3000万盎司
    COMEX_SILVER_FAILURE_THRESHOLD = int(
        os.getenv("COMEX_SILVER_FAILURE_THRESHOLD", "20000000")
    )  # 2000万盎司

    # 黄金三级预警阈值 (单位: 盎司)
    COMEX_GOLD_YELLOW_THRESHOLD = int(
        os.getenv("COMEX_GOLD_YELLOW_THRESHOLD", "10000000")
    )  # 1000万盎司
    COMEX_GOLD_RED_THRESHOLD = int(
        os.getenv("COMEX_GOLD_RED_THRESHOLD", "5000000")
    )  # 500万盎司
    COMEX_GOLD_FAILURE_THRESHOLD = int(
        os.getenv("COMEX_GOLD_FAILURE_THRESHOLD", "2000000")
    )  # 200万盎司

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
        "treasury_10y": "DGS10",  # 10年期国债收益率
        "treasury_2y": "DGS2",  # 2年期国债收益率
        "real_interest_rate": "DFII10",  # 10年期实际利率
        # 货币供应
        "m1": "M1SL",  # M1货币供应
        "m2": "M2SL",  # M2货币供应
        # 其他
        "gdp": "GDP",  # GDP
        "dxy": "DTWEXBGS",  # 美元指数(FRED版)
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
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
    REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))

    # ========================================
    # 数据处理配置
    # ========================================
    DEDUPLICATION_WINDOW_HOURS = int(os.getenv("DEDUPLICATION_WINDOW_HOURS", "12"))

    # ========================================
    # Email Digest (OpenRouter -> Gmail SMTP)
    # ========================================
    DIGEST_WINDOW_HOURS = int(os.getenv("DIGEST_WINDOW_HOURS", "12"))

    DIGEST_INCLUDE_FULL_CONTENT = (
        os.getenv("DIGEST_INCLUDE_FULL_CONTENT", "false").lower() == "true"
    )
    DIGEST_FULL_CONTENT_MAX_CHARS_PER_ARTICLE = int(
        os.getenv("DIGEST_FULL_CONTENT_MAX_CHARS_PER_ARTICLE", "2000")
    )

    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-3-pro-preview")
    OPENROUTER_TEMPERATURE = float(os.getenv("OPENROUTER_TEMPERATURE", "0.3"))
    OPENROUTER_MAX_TOKENS = int(os.getenv("OPENROUTER_MAX_TOKENS", "8192"))
    OPENROUTER_TIMEOUT = int(os.getenv("OPENROUTER_TIMEOUT", "120"))
    OPENROUTER_MAX_RETRIES = int(os.getenv("OPENROUTER_MAX_RETRIES", "3"))
    OPENROUTER_HTTP_REFERER = os.getenv("OPENROUTER_HTTP_REFERER")
    OPENROUTER_X_TITLE = os.getenv("OPENROUTER_X_TITLE")

    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
    SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

    EMAIL_FROM = os.getenv("EMAIL_FROM")
    EMAIL_TO = os.getenv("EMAIL_TO", "")

    # ========================================
    # 日志配置
    # ========================================
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

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

        to_list = [email.strip() for email in cls.EMAIL_TO.split(",") if email.strip()]
        if not to_list:
            errors.append("EMAIL_TO未配置或为空(邮件发送必需)")

        if errors:
            raise ValueError(f"配置错误:\n" + "\n".join(f"  - {e}" for e in errors))

        return True


# 初始化目录
Config.create_directories()
