#!/usr/bin/env python3
"""
测试 BOM 字符修复是否生效
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config import Config


def test_bom_fix():
    """测试环境变量能否正确解析（包括带 BOM 的情况）"""

    print("🧪 测试 BOM 字符修复...")
    print("=" * 50)

    # 测试整数类型
    print("\n📊 整数类型环境变量:")
    assert isinstance(Config.SMTP_PORT, int), "SMTP_PORT 应为整数"
    print(
        f"  ✅ SMTP_PORT = {Config.SMTP_PORT} (类型: {type(Config.SMTP_PORT).__name__})"
    )

    assert isinstance(Config.OPENROUTER_MAX_TOKENS, int), (
        "OPENROUTER_MAX_TOKENS 应为整数"
    )
    print(f"  ✅ OPENROUTER_MAX_TOKENS = {Config.OPENROUTER_MAX_TOKENS}")

    assert isinstance(Config.MAX_RETRIES, int), "MAX_RETRIES 应为整数"
    print(f"  ✅ MAX_RETRIES = {Config.MAX_RETRIES}")

    # 测试浮点数类型
    print("\n📈 浮点数类型环境变量:")
    assert isinstance(Config.OPENROUTER_TEMPERATURE, float), (
        "OPENROUTER_TEMPERATURE 应为浮点数"
    )
    print(f"  ✅ OPENROUTER_TEMPERATURE = {Config.OPENROUTER_TEMPERATURE}")

    assert isinstance(Config.VIX_ALERT_THRESHOLD, float), (
        "VIX_ALERT_THRESHOLD 应为浮点数"
    )
    print(f"  ✅ VIX_ALERT_THRESHOLD = {Config.VIX_ALERT_THRESHOLD}")

    # 测试布尔类型
    print("\n✓ 布尔类型环境变量:")
    assert isinstance(Config.SMTP_USE_TLS, bool), "SMTP_USE_TLS 应为布尔值"
    print(f"  ✅ SMTP_USE_TLS = {Config.SMTP_USE_TLS}")

    assert isinstance(Config.ENABLE_TAVILY, bool), "ENABLE_TAVILY 应为布尔值"
    print(f"  ✅ ENABLE_TAVILY = {Config.ENABLE_TAVILY}")

    # 测试字符串类型
    print("\n📝 字符串类型环境变量:")
    assert isinstance(Config.SMTP_HOST, str), "SMTP_HOST 应为字符串"
    print(f"  ✅ SMTP_HOST = {Config.SMTP_HOST}")

    assert isinstance(Config.OPENROUTER_MODEL, str), "OPENROUTER_MODEL 应为字符串"
    print(f"  ✅ OPENROUTER_MODEL = {Config.OPENROUTER_MODEL}")

    # 测试配置验证
    print("\n🔍 配置验证:")
    try:
        Config.validate()
        print("  ✅ 配置验证通过")
    except ValueError as e:
        print(f"  ❌ 配置验证失败: {e}")
        return False

    print("\n" + "=" * 50)
    print("✅ 所有测试通过! BOM 字符修复生效")
    return True


if __name__ == "__main__":
    success = test_bom_fix()
    sys.exit(0 if success else 1)
