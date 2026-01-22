#!/usr/bin/env python3
"""
GitHub Secrets 自动配置脚本 (使用 GitHub API)
不依赖 gh CLI，直接调用 GitHub API 上传 secrets
"""

import os
import json
import base64
import requests
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
from nacl import encoding, public

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


def load_env_file():
    """从 .env 文件加载环境变量"""
    env_path = Path(".env")
    if not env_path.exists():
        print("❌ 错误: .env 文件不存在")
        return None

    print("✅ .env 文件存在")

    env_vars = {}
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()

                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]

                if value:
                    env_vars[key] = value

    return env_vars


def encrypt_secret(public_key: str, secret_value: str) -> str:
    """使用公钥加密 secret"""
    public_key_obj = public.PublicKey(
        public_key.encode("utf-8"), encoding.Base64Encoder()
    )
    encrypted = public.SealedBox(public_key_obj).encrypt(secret_value.encode("utf-8"))
    return base64.b64encode(encrypted).decode("utf-8")


def get_repo_public_key(owner: str, repo: str, token: str):
    """获取仓库的公钥"""
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/secrets/public-key"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def upload_secret(
    owner: str,
    repo: str,
    token: str,
    secret_name: str,
    secret_value: str,
    key_id: str,
    public_key: str,
):
    """上传 secret 到 GitHub"""
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/secrets/{secret_name}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    encrypted_value = encrypt_secret(public_key, secret_value)

    data = {"encrypted_value": encrypted_value, "key_id": key_id}

    response = requests.put(url, headers=headers, json=data)
    response.raise_for_status()
    return True


def main():
    print("=" * 80)
    print("GitHub Secrets 自动配置工具 (使用 GitHub API)")
    print("=" * 80)
    print()

    # 检查依赖
    try:
        import nacl
    except ImportError:
        print("❌ 错误: 缺少依赖包 PyNaCl")
        print("   请运行: pip install PyNaCl")
        return

    # 获取 GitHub token
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("❌ 错误: 未设置 GITHUB_TOKEN 环境变量")
        print()
        print("请按以下步骤配置:")
        print("1. 前往 https://github.com/settings/tokens/new")
        print("2. 勾选权限: repo (完整权限)")
        print("3. 生成 token 并复制")
        print("4. 设置环境变量:")
        print("   $env:GITHUB_TOKEN='your_token_here'  # PowerShell")
        print("   export GITHUB_TOKEN='your_token_here'  # Bash")
        print()
        print("然后重新运行此脚本")
        return

    print("✅ GitHub Token 已配置")

    # 获取仓库信息
    repo_owner = (
        os.getenv("GITHUB_REPOSITORY_OWNER") or input("请输入 GitHub 用户名: ").strip()
    )
    repo_name = (
        os.getenv("GITHUB_REPOSITORY_NAME")
        or input("请输入仓库名 (FinNews): ").strip()
        or "FinNews"
    )

    print(f"✅ 仓库: {repo_owner}/{repo_name}")
    print()

    # 加载 .env
    env_vars = load_env_file()
    if not env_vars:
        return

    # 检查必需的 secrets
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
        print()
        print("❌ 错误: 请先在 .env 中配置所有必需的 secrets")
        return

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

    print()
    print("⚠️  警告: 这将覆盖 GitHub 上已存在的同名 secrets")
    print()

    response = input("是否继续? (y/N): ").strip().lower()
    if response not in ["y", "yes"]:
        print("已取消")
        return

    # 获取公钥
    print()
    print("获取仓库公钥...")
    try:
        key_info = get_repo_public_key(repo_owner, repo_name, token)
        key_id = key_info["key_id"]
        public_key = key_info["key"]
        print("✅ 公钥获取成功")
    except Exception as e:
        print(f"❌ 错误: {e}")
        return

    # 上传 secrets
    print()
    print("=" * 80)
    print("开始上传 secrets...")
    print("=" * 80)
    print()

    uploaded = 0
    failed = 0

    for key, value, required in secrets_to_upload:
        print(f"上传 {key:30s} ... ", end="", flush=True)
        try:
            upload_secret(repo_owner, repo_name, token, key, value, key_id, public_key)
            print("✅")
            uploaded += 1
        except Exception as e:
            print(f"❌ 失败: {e}")
            failed += 1

    # 显示结果
    print()
    print("=" * 80)
    print("完成!")
    print("=" * 80)
    print()
    print(f"✅ 成功上传: {uploaded} 个")
    if failed > 0:
        print(f"❌ 失败: {failed} 个")
    print()
    print("🎉 所有 secrets 已配置完成!")
    print()
    print("下一步:")
    print("  1. 前往 GitHub Actions 页面启用 workflows")
    print(f"     https://github.com/{repo_owner}/{repo_name}/actions")
    print()
    print("  2. 查看已配置的 secrets:")
    print(f"     https://github.com/{repo_owner}/{repo_name}/settings/secrets/actions")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n已取消")
    except Exception as e:
        print(f"\n\n❌ 错误: {e}")
        import traceback

        traceback.print_exc()
