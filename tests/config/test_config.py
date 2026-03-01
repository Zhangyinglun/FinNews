"""
测试 Config 配置模块
"""

import importlib

from config.config import Config


def _reload_config(monkeypatch_or_none=None) -> type:
    """重新加载 config 模块以反映环境变量变化"""
    import config.config as config_module
    reloaded = importlib.reload(config_module)
    return reloaded.Config


def test_sonar_config_defaults(monkeypatch) -> None:
    """Sonar 配置项默认值正确"""
    assert hasattr(Config, "ENABLE_SONAR")
    assert hasattr(Config, "SONAR_MODEL")
    assert hasattr(Config, "SONAR_USE_TRUSTED_DOMAINS")

    monkeypatch.setenv("ENABLE_SONAR", "")
    monkeypatch.setenv("SONAR_MODEL", "")
    monkeypatch.setenv("SONAR_USE_TRUSTED_DOMAINS", "")

    config_class = _reload_config()
    try:
        assert config_class.ENABLE_SONAR is False
        assert config_class.SONAR_MODEL == "perplexity/sonar"
        assert config_class.SONAR_USE_TRUSTED_DOMAINS is False
    finally:
        _reload_config()  # 还原


def test_sonar_config_env_override(monkeypatch) -> None:
    """Sonar 配置项支持环境变量覆盖"""
    monkeypatch.setenv("ENABLE_SONAR", "true")
    monkeypatch.setenv("SONAR_MODEL", "perplexity/sonar-pro")
    monkeypatch.setenv("SONAR_USE_TRUSTED_DOMAINS", "true")

    config_class = _reload_config()
    try:
        assert config_class.ENABLE_SONAR is True
        assert config_class.SONAR_MODEL == "perplexity/sonar-pro"
        assert config_class.SONAR_USE_TRUSTED_DOMAINS is True
    finally:
        _reload_config()  # 还原


def test_config_values() -> None:
    """测试配置值是否正确加载"""
    assert Config.OUTPUT_DIR.exists(), "输出目录应该存在"
    assert Config.RAW_DIR.exists(), "原始数据目录应该存在"
    assert Config.PROCESSED_DIR.exists(), "处理数据目录应该存在"
    assert Config.LOG_DIR.exists(), "日志目录应该存在"

    assert len(Config.WHITELIST_KEYWORDS) > 0, "应该有白名单关键词"
    assert len(Config.BLACKLIST_KEYWORDS) > 0, "应该有黑名单关键词"

    assert Config.DEDUPLICATION_WINDOW_HOURS > 0, "去重时间窗口应该大于0"
    assert Config.DIGEST_WINDOW_HOURS > 0, "摘要时间窗口应该大于0"


def test_rss_feeds() -> None:
    """测试RSS源配置"""
    assert len(Config.RSS_FEEDS) > 0, "应该至少有一个RSS源"
    for name, url in Config.RSS_FEEDS.items():
        assert url.startswith("http"), f"RSS源应该是有效的URL: {name} -> {url}"


def test_ticker_symbols() -> None:
    """测试股票代码配置"""
    assert len(Config.YFINANCE_TICKERS) > 0, "应该至少有一个股票代码"
    assert "gold_futures" in Config.YFINANCE_TICKERS, "应该包含黄金期货"
    assert "silver_futures" in Config.YFINANCE_TICKERS, "应该包含白银期货"
    assert Config.YFINANCE_TICKERS["gold_futures"] == "GC=F", "黄金期货代码应为GC=F"
    assert Config.YFINANCE_TICKERS["silver_futures"] == "SI=F", "白银期货代码应为SI=F"


def test_fred_series() -> None:
    """测试FRED系列配置"""
    assert len(Config.FRED_SERIES) > 0, "应该至少有一个FRED系列"
    assert "cpi" in Config.FRED_SERIES, "应该包含CPI指标"
    assert "fed_funds" in Config.FRED_SERIES, "应该包含联邦基金利率"
