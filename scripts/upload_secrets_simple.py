#!/usr/bin/env python3
"""
GitHub Secrets 配置脚本 - 简化版
使用 subprocess 调用 gh CLI 上传 secrets
"""

import os
import subprocess
import sys
from pathlib import Path

# 必需的 Secrets
REQUIRED_SECRETS = [
    "TAVILY_API_KEY",
    "FRED_API_KEY",
    "OPENROUTER_API_KEY",
    "SMTP_USERNAME",
    "SMTP_PASSWORD",
    "EMAIL_FROM",
    "EMAIL_TO",
]

# 可选的 Secrets
OPTIONAL_SECRETS = [
    "ALPHA_VANTAGE_API_KEY",
    "OPENROUTER_MODEL",
    "SMTP_HOST",
    "SMTP_PORT",
]


def load_env():
    """加载 .env 文件"""
    env_path = Path(".env")
    if not env_path.exists():
        return None

    env_vars = {}
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if value:
                    env_vars[key] = value
    return env_vars


def set_secret_with_gh(key, value):
    """使用 gh CLI 设置 secret"""
    # 设置 PATH
    gh_path = r"C:\Program Files\GitHub CLI"
    env = os.environ.copy()
    if gh_path not in env.get("PATH", ""):
        env["PATH"] = f"{gh_path};{env.get('PATH', '')}"

    try:
        # 使用 echo + pipe 传递 secret
        process = subprocess.Popen(
            ["gh", "secret", "set", key],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
        stdout, stderr = process.communicate(input=value, timeout=30)
        return process.returncode == 0, stderr
    except Exception as e:
        return False, str(e)


def main():
    print("=" * 80)
    print("GitHub Secrets 配置工具 - 简化版")
    print("=" * 80)
    print()

    # 加载 .env
    print("📁 加载 .env 文件...")
    env_vars = load_env()
    if not env_vars:
        print("❌ .env 文件不存在或为空")
        return
    print("✅ .env 文件加载成功")
    print()

    # 收集要上传的 secrets
    secrets = []
    missing = []

    for key in REQUIRED_SECRETS:
        if key in env_vars:
            secrets.append((key, env_vars[key]))
        else:
            missing.append(key)

    for key in OPTIONAL_SECRETS:
        if key in env_vars:
            secrets.append((key, env_vars[key]))

    if missing:
        print("❌ 缺少必需的配置:")
        for key in missing:
            print(f"   - {key}")
        return

    print(f"📊 准备上传 {len(secrets)} 个 secrets")
    print()

    # 显示列表
    print("Secrets 列表:")
    for key, value in secrets:
        if len(value) > 10:
            masked = f"{value[:4]}...{value[-4:]}"
        else:
            masked = "***"
        print(f"  • {key:30s} = {masked}")
    print()

    response = input("确认上传? (y/N): ").strip().lower()
    if response not in ["y", "yes", "是"]:
        print("已取消")
        return

    # 上传
    print()
    print("🚀 开始上传...")
    print()

    success_count = 0
    fail_count = 0

    for key, value in secrets:
        print(f"   {key:30s} ... ", end="", flush=True)
        ok, err = set_secret_with_gh(key, value)
        if ok:
            print("✅")
            success_count += 1
        else:
            print(f"❌ {err[:50]}")
            fail_count += 1

    print()
    print("=" * 80)
    print(f"✅ 成功: {success_count} 个")
    if fail_count > 0:
        print(f"❌ 失败: {fail_count} 个")
    print("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n已取消")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
