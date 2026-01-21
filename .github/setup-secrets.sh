#!/bin/bash
# GitHub Secrets 批量配置脚本
# 使用方法: bash .github/setup-secrets.sh

set -e

echo "=========================================="
echo "GitHub Secrets 批量配置工具"
echo "=========================================="
echo ""

# 检查 gh CLI 是否安装
if ! command -v gh &> /dev/null; then
    echo "❌ 错误: 未安装 GitHub CLI"
    echo "请先安装: https://cli.github.com/"
    exit 1
fi

# 检查是否已登录
if ! gh auth status &> /dev/null; then
    echo "❌ 错误: 未登录 GitHub CLI"
    echo "请运行: gh auth login"
    exit 1
fi

# 检查 .env 文件是否存在
if [ ! -f .env ]; then
    echo "❌ 错误: .env 文件不存在"
    echo "请先创建 .env 文件（参考 .env.example）"
    exit 1
fi

echo "✅ 环境检查通过"
echo ""
echo "准备从 .env 文件读取并上传 secrets..."
echo "⚠️  警告: 这将覆盖已存在的同名 secrets"
echo ""
read -p "是否继续? (y/N) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "已取消"
    exit 0
fi

echo ""
echo "开始上传 secrets..."
echo "=========================================="

# 读取 .env 文件并上传
uploaded=0
skipped=0

while IFS='=' read -r key value; do
    # 跳过空行和注释
    [[ -z "$key" || "$key" =~ ^# ]] && continue
    
    # 移除前后空格
    key=$(echo "$key" | xargs)
    value=$(echo "$value" | xargs)
    
    # 跳过空值
    [[ -z "$value" ]] && continue
    
    # 上传 secret
    echo -n "上传 $key ... "
    if echo "$value" | gh secret set "$key" 2>/dev/null; then
        echo "✅"
        ((uploaded++))
    else
        echo "❌ 失败"
        ((skipped++))
    fi
done < .env

echo "=========================================="
echo "完成!"
echo "✅ 成功上传: $uploaded 个"
echo "❌ 失败: $skipped 个"
echo ""
echo "验证 secrets:"
gh secret list
