# 🚀 GitHub Secrets 快速配置指南

## 只需 2 步！

### 步骤 1: 登录 GitHub CLI (只需一次)

在 PowerShell 中运行：

```powershell
gh auth login
```

按提示选择：
1. **Where do you use GitHub?** → `GitHub.com`
2. **What is your preferred protocol?** → `HTTPS`
3. **Authenticate Git with your GitHub credentials?** → `Yes`
4. **How would you like to authenticate?** → `Login with a web browser` (推荐)

会显示一个 8 位代码，浏览器会自动打开，粘贴代码并授权即可。

### 步骤 2: 运行上传脚本

```powershell
powershell .\upload-secrets.ps1
```

脚本会：
- ✅ 从 `.env` 自动读取所有配置
- ✅ 显示将要上传的 secrets（隐藏敏感信息）
- ✅ 批量上传到 GitHub
- ✅ 显示上传结果

**完成！** 就这么简单！

---

## 📋 将要上传的 Secrets

根据你的 `.env` 文件，将会上传：

**必需 (7个)**:
- TAVILY_API_KEY
- FRED_API_KEY
- OPENROUTER_API_KEY
- SMTP_USERNAME
- SMTP_PASSWORD
- EMAIL_FROM
- EMAIL_TO

**可选 (4个)**:
- ALPHA_VANTAGE_API_KEY
- OPENROUTER_MODEL
- SMTP_HOST
- SMTP_PORT

---

## ❓ 常见问题

### Q: gh auth login 提示找不到命令？
**A**: 重启 PowerShell 或 Terminal，让系统重新加载 PATH

### Q: 登录后如何验证？
**A**: 运行 `gh auth status`，应该显示 "Logged in to github.com"

### Q: 上传失败怎么办？
**A**: 检查：
1. `gh auth status` 确认已登录
2. 你的账号有仓库的 Admin 权限
3. `.env` 文件格式正确

---

## 🎯 上传后

访问查看已配置的 secrets：
```
https://github.com/Zhangyinglun/FinNews/settings/secrets/actions
```

启用 workflows：
```
https://github.com/Zhangyinglun/FinNews/actions
```

---

**创建时间**: 2026-01-21
