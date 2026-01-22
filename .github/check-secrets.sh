#!/bin/bash
# 检查 GitHub Secrets 是否正确配置

set -e

echo "🔍 检查 GitHub Secrets 配置状态..."
echo ""

# 需要的 Secrets 列表
REQUIRED_SECRETS=(
    "TAVILY_API_KEY"
    "FRED_API_KEY"
    "OPENROUTER_API_KEY"
    "SMTP_USERNAME"
    "SMTP_PASSWORD"
    "EMAIL_FROM"
    "EMAIL_TO"
)

OPTIONAL_SECRETS=(
    "ALPHA_VANTAGE_API_KEY"
    "OPENROUTER_MODEL"
    "OPENROUTER_HTTP_REFERER"
    "OPENROUTER_X_TITLE"
    "SMTP_HOST"
    "SMTP_PORT"
    "SMTP_USE_TLS"
)

# 检查 gh CLI 是否安装
if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI (gh) 未安装"
    echo "请访问: https://cli.github.com/ 安装"
    exit 1
fi

# 检查是否登录
if ! gh auth status &> /dev/null; then
    echo "❌ 未登录 GitHub CLI"
    echo "请运行: gh auth login"
    exit 1
fi

echo "✅ GitHub CLI 已就绪"
echo ""

# 获取已配置的 secrets
echo "📋 已配置的 Secrets:"
gh secret list

echo ""
echo "🔍 验证必需的 Secrets..."

missing_secrets=()
for secret in "${REQUIRED_SECRETS[@]}"; do
    if gh secret list | grep -q "^$secret"; then
        echo "  ✅ $secret"
    else
        echo "  ❌ $secret (缺失)"
        missing_secrets+=("$secret")
    fi
done

echo ""
echo "🔍 可选的 Secrets..."

for secret in "${OPTIONAL_SECRETS[@]}"; do
    if gh secret list | grep -q "^$secret"; then
        echo "  ✅ $secret"
    else
        echo "  ⚠️  $secret (未配置，使用默认值)"
    fi
done

echo ""
if [ ${#missing_secrets[@]} -eq 0 ]; then
    echo "✅ 所有必需的 Secrets 已配置!"
    echo ""
    echo "💡 你可以运行以下命令手动触发 workflow 测试:"
    echo "   gh workflow run finnews-schedule.yml"
    echo ""
    echo "或者查看最近的运行记录:"
    echo "   gh run list --workflow=finnews-schedule.yml --limit=5"
    exit 0
else
    echo "❌ 缺少以下必需的 Secrets:"
    for secret in "${missing_secrets[@]}"; do
        echo "   - $secret"
    done
    echo ""
    echo "💡 请使用以下脚本上传 Secrets:"
    echo "   bash .github/setup-secrets.sh"
    exit 1
fi
