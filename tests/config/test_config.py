"""
测试 Config 配置模块
"""

from pathlib import Path
import sys
import os
import importlib

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from config.config import Config
from utils.logger import setup_logger


def _apply_env_overrides(
    env_overrides: dict[str, str],
    unset_keys: list[str],
) -> dict[str, str | None]:
    original_env = {}
    for key in set(unset_keys) | set(env_overrides.keys()):
        original_env[key] = os.environ.get(key)
    for key in unset_keys:
        os.environ.pop(key, None)
    for key, value in env_overrides.items():
        os.environ[key] = value
    return original_env


def _restore_env_overrides(original_env: dict[str, str | None]) -> None:
    for key, value in original_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


def _reload_config() -> type[Config]:
    import config.config as config_module

    reloaded_module = importlib.reload(config_module)
    globals()["Config"] = reloaded_module.Config
    return reloaded_module.Config


def test_sonar_config_defaults() -> None:
    """Sonar 配置项默认值正确"""
    assert hasattr(Config, "ENABLE_SONAR")
    assert hasattr(Config, "SONAR_MODEL")
    assert hasattr(Config, "SONAR_USE_TRUSTED_DOMAINS")

    original_env = _apply_env_overrides(
        {
            "ENABLE_SONAR": "",
            "SONAR_MODEL": "",
            "SONAR_USE_TRUSTED_DOMAINS": "",
        },
        [],
    )
    try:
        config_class = _reload_config()
        assert config_class.ENABLE_SONAR is False
        assert config_class.SONAR_MODEL == "perplexity/sonar"
        assert config_class.SONAR_USE_TRUSTED_DOMAINS is False
    finally:
        _restore_env_overrides(original_env)
        _reload_config()


def test_sonar_config_env_override() -> None:
    """Sonar 配置项支持环境变量覆盖"""
    original_env = _apply_env_overrides(
        {
            "ENABLE_SONAR": "true",
            "SONAR_MODEL": "perplexity/sonar-pro",
            "SONAR_USE_TRUSTED_DOMAINS": "true",
        },
        [],
    )
    try:
        config_class = _reload_config()
        assert config_class.ENABLE_SONAR is True
        assert config_class.SONAR_MODEL == "perplexity/sonar-pro"
        assert config_class.SONAR_USE_TRUSTED_DOMAINS is True
    finally:
        _restore_env_overrides(original_env)
        _reload_config()


def test_config_values():
    """测试配置值是否正确加载"""
    setup_logger()

    print("=" * 80)
    print("正在测试 Config 配置...")
    print("=" * 80)

    # 测试基础配置
    print("\n【基础配置】")
    print(f"输出目录: {Config.OUTPUT_DIR}")
    print(f"原始数据目录: {Config.RAW_DIR}")
    print(f"处理数据目录: {Config.PROCESSED_DIR}")
    print(f"日志目录: {Config.LOG_DIR}")

    assert Config.OUTPUT_DIR.exists(), "输出目录应该存在"
    assert Config.RAW_DIR.exists(), "原始数据目录应该存在"
    assert Config.PROCESSED_DIR.exists(), "处理数据目录应该存在"
    assert Config.LOG_DIR.exists(), "日志目录应该存在"

    # 测试数据源配置
    print("\n【数据源配置】")
    print(f"Tavily启用: {Config.ENABLE_TAVILY}")
    print(f"YFinance启用: {Config.ENABLE_YFINANCE}")
    print(f"RSS启用: {Config.ENABLE_RSS}")
    print(f"FRED启用: {Config.ENABLE_FRED}")
    print(f"AlphaVantage启用: {Config.ENABLE_ALPHA_VANTAGE}")

    # 测试关键词配置
    print("\n【关键词过滤】")
    print(f"白名单关键词数量: {len(Config.WHITELIST_KEYWORDS)}")
    print(f"黑名单关键词数量: {len(Config.BLACKLIST_KEYWORDS)}")
    print(f"白名单示例: {Config.WHITELIST_KEYWORDS[:3]}")
    print(f"黑名单示例: {Config.BLACKLIST_KEYWORDS[:3]}")

    assert len(Config.WHITELIST_KEYWORDS) > 0, "应该有白名单关键词"
    assert len(Config.BLACKLIST_KEYWORDS) > 0, "应该有黑名单关键词"

    # 测试其他配置
    print("\n【其他配置】")
    print(f"去重时间窗口: {Config.DEDUPLICATION_WINDOW_HOURS} 小时")
    print(f"摘要时间窗口: {Config.DIGEST_WINDOW_HOURS} 小时")

    assert Config.DEDUPLICATION_WINDOW_HOURS > 0, "去重时间窗口应该大于0"
    assert Config.DIGEST_WINDOW_HOURS > 0, "摘要时间窗口应该大于0"

    print("\n✅ 配置测试通过！")


def test_api_keys():
    """测试API密钥配置"""
    print("\n" + "=" * 80)
    print("检查API密钥配置...")
    print("=" * 80)

    api_keys = {
        "TAVILY_API_KEY": Config.TAVILY_API_KEY,
        "FRED_API_KEY": Config.FRED_API_KEY,
        "ALPHA_VANTAGE_API_KEY": Config.ALPHA_VANTAGE_API_KEY,
        "OPENROUTER_API_KEY": Config.OPENROUTER_API_KEY,
    }

    for key_name, key_value in api_keys.items():
        status = "✅ 已配置" if key_value else "⚠️ 未配置"
        masked_value = key_value[:10] + "..." if key_value else "未设置"
        print(f"{key_name}: {status} ({masked_value})")

    print("\n注意: 至少需要配置 TAVILY_API_KEY 和 FRED_API_KEY 才能正常运行")


def test_validation():
    """测试配置验证功能"""
    print("\n" + "=" * 80)
    print("测试配置验证...")
    print("=" * 80)

    try:
        Config.validate()
        print("✅ 配置验证通过！所有必需的API密钥都已配置")
    except ValueError as e:
        print(f"⚠️ 配置验证失败: {e}")
        print("这是预期的，如果某些API密钥未配置")


def test_rss_feeds():
    """测试RSS源配置"""
    print("\n" + "=" * 80)
    print("测试RSS源配置...")
    print("=" * 80)

    print(f"\nRSS源数量: {len(Config.RSS_FEEDS)}")
    for idx, (name, url) in enumerate(Config.RSS_FEEDS.items(), 1):
        print(f"{idx}. {name}: {url}")

    assert len(Config.RSS_FEEDS) > 0, "应该至少有一个RSS源"
    for name, url in Config.RSS_FEEDS.items():
        assert url.startswith("http"), f"RSS源应该是有效的URL: {name} -> {url}"

    print("\n✅ RSS源配置正确！")


def test_ticker_symbols():
    """测试股票代码配置"""
    print("\n" + "=" * 80)
    print("测试股票代码配置...")
    print("=" * 80)

    print(f"\n股票代码数量: {len(Config.YFINANCE_TICKERS)}")
    for idx, (name, ticker) in enumerate(Config.YFINANCE_TICKERS.items(), 1):
        print(f"{idx}. {name} - {ticker}")

    assert len(Config.YFINANCE_TICKERS) > 0, "应该至少有一个股票代码"
    assert "gold_futures" in Config.YFINANCE_TICKERS, "应该包含黄金期货"
    assert "silver_futures" in Config.YFINANCE_TICKERS, "应该包含白银期货"
    assert Config.YFINANCE_TICKERS["gold_futures"] == "GC=F", "黄金期货代码应为GC=F"
    assert Config.YFINANCE_TICKERS["silver_futures"] == "SI=F", "白银期货代码应为SI=F"

    print("\n✅ 股票代码配置正确！")


def test_fred_series():
    """测试FRED系列配置"""
    print("\n" + "=" * 80)
    print("测试FRED系列配置...")
    print("=" * 80)

    print(f"\nFRED系列数量: {len(Config.FRED_SERIES)}")
    for idx, (name, series_id) in enumerate(Config.FRED_SERIES.items(), 1):
        print(f"{idx}. {name} - {series_id}")

    assert len(Config.FRED_SERIES) > 0, "应该至少有一个FRED系列"
    assert "cpi" in Config.FRED_SERIES, "应该包含CPI指标"
    assert "fed_funds" in Config.FRED_SERIES, "应该包含联邦基金利率"

    print("\n✅ FRED系列配置正确！")


if __name__ == "__main__":
    test_sonar_config_defaults()
    test_config_values()
    test_api_keys()
    test_validation()
    test_rss_feeds()
    test_ticker_symbols()
    test_fred_series()

    print("\n" + "=" * 80)
    print("所有配置测试完成！")
    print("=" * 80)
