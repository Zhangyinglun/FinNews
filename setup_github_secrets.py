#!/usr/bin/env python3
"""
GitHub Secrets 自动配置脚本
从 .env 文件读取并上传所有 secrets 到 GitHub
"""

import os
import subprocess
import sys
from pathlib import Path

# 必需的 Secrets 列表
REQUIRED_SECRETS = [
    "TAVILY_API_KEY",
    "FRED_API_KEY",
    "OPENROUTER_API_KEY",
    "SMTP_USERNAME",
    "SMTP_PASSWORD",
    "EMAIL_FROM",
    "EMAIL_TO",
]

# 可选的 Secrets 列表
OPTIONAL_SECRETS = [
    "ALPHA_VANTAGE_API_KEY",
    "OPENROUTER_MODEL",
    "OPENROUTER_HTTP_REFERER",
    "OPENROUTER_X_TITLE",
    "SMTP_HOST",
    "SMTP_PORT",
    "SMTP_USE_TLS",
]


def check_gh_cli():
    """检查 GitHub CLI 是否安装"""
    try:
        result = subprocess.run(
            ["gh", "--version"], capture_output=True, text=True, check=True
        )
        print("✅ GitHub CLI 已安装")
        print(f"   版本: {result.stdout.strip().split()[2]}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ 错误: 未安装 GitHub CLI")
        print("   请运行: winget install GitHub.cli")
        return False


def check_gh_auth():
    """检查 GitHub CLI 是否已登录"""
    try:
        subprocess.run(["gh", "auth", "status"], capture_output=True, check=True)
        print("✅ GitHub CLI 已登录")
        return True
    except subprocess.CalledProcessError:
        print("❌ 错误: 未登录 GitHub CLI")
        print("   请运行: gh auth login")
        return False


def load_env_file():
    """从 .env 文件加载环境变量"""
    env_path = Path(".env")
    if not env_path.exists():
        print("❌ 错误: .env 文件不存在")
        print("   请先创建 .env 文件（参考 .env.example）")
        return None

    print("✅ .env 文件存在")

    env_vars = {}
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # 跳过空行和注释
            if not line or line.startswith("#"):
                continue

            # 解析 key=value
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()

                # 移除引号
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]

                if value:  # 只保存非空值
                    env_vars[key] = value

    return env_vars


def upload_secret(key, value):
    """上传单个 secret 到 GitHub"""
    try:
        # 使用 echo + pipe 方式传递 secret 值
        process = subprocess.Popen(
            ["gh", "secret", "set", key],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        stdout, stderr = process.communicate(input=value)

        if process.returncode == 0:
            return True, None
        else:
            return False, stderr
    except Exception as e:
        return False, str(e)


def main():
    print("=" * 80)
    print("GitHub Secrets 自动配置工具")
    print("=" * 80)
    print()

    # 1. 检查 GitHub CLI
    if not check_gh_cli():
        sys.exit(1)

    # 2. 检查登录状态
    if not check_gh_auth():
        print()
        print("请先登录 GitHub CLI:")
        print("  gh auth login")
        print()
        print("登录后重新运行此脚本")
        sys.exit(1)

    # 3. 加载 .env 文件
    print()
    env_vars = load_env_file()
    if env_vars is None:
        sys.exit(1)

    # 4. 确认上传
    print()
    print(f"准备从 .env 文件上传 secrets 到 GitHub")
    print()

    # 显示将要上传的 secrets
    secrets_to_upload = []
    missing_required = []

    for key in REQUIRED_SECRETS:
        if key in env_vars:
            secrets_to_upload.append((key, env_vars[key], True))
        else:
            missing_required.append(key)

    for key in OPTIONAL_SECRETS:
        if key in env_vars:
            secrets_to_upload.append((key, env_vars[key], False))

    print("将要上传的 Secrets:")
    print()
    print("必需的 Secrets:")
    for key, value, required in secrets_to_upload:
        if required:
            # 隐藏敏感信息，只显示前后几个字符
            if len(value) > 10:
                masked = f"{value[:4]}...{value[-4:]}"
            else:
                masked = "***"
            print(f"  ✓ {key:30s} = {masked}")

    if missing_required:
        print()
        print("⚠️  缺少必需的 Secrets:")
        for key in missing_required:
            print(f"  ✗ {key}")

    optional_count = sum(1 for _, _, req in secrets_to_upload if not req)
    if optional_count > 0:
        print()
        print(f"可选的 Secrets ({optional_count} 个):")
        for key, value, required in secrets_to_upload:
            if not required:
                if len(value) > 10:
                    masked = f"{value[:4]}...{value[-4:]}"
                else:
                    masked = "***"
                print(f"  ✓ {key:30s} = {masked}")

    if missing_required:
        print()
        print("❌ 错误: 缺少必需的 Secrets，请先在 .env 中配置")
        sys.exit(1)

    print()
    print("⚠️  警告: 这将覆盖 GitHub 上已存在的同名 secrets")
    print()

    response = input("是否继续? (y/N): ").strip().lower()
    if response not in ["y", "yes"]:
        print("已取消")
        sys.exit(0)

    # 5. 上传 secrets
    print()
    print("=" * 80)
    print("开始上传 secrets...")
    print("=" * 80)
    print()

    uploaded = 0
    failed = 0

    for key, value, required in secrets_to_upload:
        print(f"上传 {key:30s} ... ", end="", flush=True)
        success, error = upload_secret(key, value)

        if success:
            print("✅")
            uploaded += 1
        else:
            print(f"❌ 失败: {error}")
            failed += 1

    # 6. 显示结果
    print()
    print("=" * 80)
    print("完成!")
    print("=" * 80)
    print()
    print(f"✅ 成功上传: {uploaded} 个")
    if failed > 0:
        print(f"❌ 失败: {failed} 个")
    print()

    # 7. 验证
    print("验证已上传的 secrets:")
    print()
    try:
        result = subprocess.run(
            ["gh", "secret", "list"], capture_output=True, text=True, check=True
        )
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"❌ 验证失败: {e}")

    print()
    print("🎉 所有 secrets 已配置完成!")
    print()
    print("下一步:")
    print("  1. 前往 GitHub Actions 页面启用 workflows")
    print("     https://github.com/<你的用户名>/FinNews/actions")
    print()
    print("  2. 手动触发测试:")
    print("     gh workflow run ci.yml")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n已取消")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ 错误: {e}")
        sys.exit(1)
