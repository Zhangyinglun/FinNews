#!/bin/bash
# GitHub 推送脚本

echo "GitHub 推送助手"
echo "==============="
echo ""
echo "请提供以下信息："
read -p "GitHub 用户名 (通常是邮箱): " USERNAME
read -sp "GitHub Personal Access Token: " TOKEN
echo ""

# 配置临时远程 URL
REMOTE_URL="https://${USERNAME}:${TOKEN}@github.com/Zhangyinglun/FinNews.git"
git remote set-url origin "${REMOTE_URL}"

# 推送
echo "正在推送..."
if git push origin main; then
    echo "✅ 推送成功！"
    
    # 恢复原始远程 URL（移除 token）
    git remote set-url origin https://github.com/Zhangyinglun/FinNews.git
    echo "✅ 已恢复远程 URL"
else
    echo "❌ 推送失败"
    git remote set-url origin https://github.com/Zhangyinglun/FinNews.git
fi
