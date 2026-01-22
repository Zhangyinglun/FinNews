#!/bin/bash
# 手动触发 GitHub Actions workflow 来测试修复

set -e

echo "🚀 准备触发 finnews-schedule workflow..."
echo ""

# 检查 gh CLI
if ! command -v gh &> /dev/null; then
    echo "❌ 未安装 GitHub CLI"
    echo "请访问 https://cli.github.com/ 安装"
    exit 1
fi

# 检查登录状态
if ! gh auth status &> /dev/null; then
    echo "❌ 未登录 GitHub CLI"
    echo "请运行: gh auth login"
    exit 1
fi

echo "✅ GitHub CLI 已就绪"
echo ""

# 显示当前提交
current_sha=$(git rev-parse HEAD)
current_short_sha=$(git rev-parse --short HEAD)
current_message=$(git log -1 --pretty=%B | head -1)

echo "📍 当前提交:"
echo "  SHA: $current_sha"
echo "  消息: $current_message"
echo ""

# 确认是否是修复提交
if [[ "$current_message" == *"BOM"* ]] || [[ "$current_short_sha" == "8f67bdf" ]]; then
    echo "✅ 当前提交包含 BOM 修复"
else
    echo "⚠️  警告: 当前提交可能不包含 BOM 修复"
    echo "请确认你在正确的分支上"
fi

echo ""
echo "准备触发 workflow 'finnews-schedule'..."
echo "这将使用最新的代码 (提交 $current_short_sha)"
echo ""

read -p "是否继续? (y/N) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "已取消"
    exit 0
fi

echo ""
echo "🚀 触发 workflow..."

# 触发 workflow
if gh workflow run finnews-schedule.yml; then
    echo ""
    echo "✅ Workflow 已触发!"
    echo ""
    echo "等待 5 秒后查看运行状态..."
    sleep 5
    
    echo ""
    echo "📋 最近的运行记录:"
    gh run list --workflow=finnews-schedule.yml --limit=3
    
    echo ""
    echo "💡 查看详细日志:"
    echo "  gh run view --workflow=finnews-schedule.yml --log"
    echo ""
    echo "或访问:"
    echo "  https://github.com/$(git remote get-url origin | sed 's/.*github.com[:/]\(.*\)\.git/\1/')/actions"
else
    echo ""
    echo "❌ 触发失败"
    exit 1
fi
