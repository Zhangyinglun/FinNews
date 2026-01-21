# GitHub Actions 快速参考

## 🎯 回答你的问题

**Q: Secrets 是要一个一个配置吗?**

**A: 有两种方式：**

### ❌ 方式 1: 网页逐个配置（慢）
- 需要手动复制粘贴 7-10 次
- 容易出错
- 耗时约 5-10 分钟

### ✅ 方式 2: 脚本批量配置（快）⭐
```powershell
# Windows (3 步搞定)
gh auth login                          # 1. 登录 GitHub
powershell .github\setup-secrets.ps1   # 2. 运行脚本
gh secret list                         # 3. 验证

# 耗时: 约 1 分钟
```

```bash
# Linux/Mac (3 步搞定)
gh auth login                    # 1. 登录 GitHub
bash .github/setup-secrets.sh    # 2. 运行脚本
gh secret list                   # 3. 验证

# 耗时: 约 1 分钟
```

**前提**: 你的 `.env` 文件已包含所有 API keys

---

## 📋 必需配置的 Secrets（7 个）

```
1. TAVILY_API_KEY          - Tavily API 密钥
2. FRED_API_KEY            - FRED API 密钥
3. OPENROUTER_API_KEY      - OpenRouter API 密钥 (LLM)
4. SMTP_USERNAME           - 你的 Gmail 地址
5. SMTP_PASSWORD           - Gmail 应用专用密码 (不是账号密码!)
6. EMAIL_FROM              - 发件人邮箱 (同 SMTP_USERNAME)
7. EMAIL_TO                - 收件人邮箱
```

---

## 🔐 Gmail 应用专用密码获取（重要！）

**错误** ❌: 使用 Gmail 账号密码
**正确** ✅: 使用应用专用密码

### 快速获取步骤:

1. **启用两步验证**
   - 访问: https://myaccount.google.com/security
   - 找到 "两步验证" → 启用

2. **创建应用专用密码**
   - 访问: https://myaccount.google.com/apppasswords
   - 应用: 邮件
   - 设备: 其他 (自定义名称) → 输入 "FinNews"
   - 点击 "生成"
   - 复制 16 位密码: `xxxx xxxx xxxx xxxx`

3. **配置 Secret**
   ```
   SMTP_PASSWORD = xxxx xxxx xxxx xxxx  (应用专用密码，不是账号密码!)
   ```

---

## 🚀 推荐流程（最省时）

### 步骤 1: 安装 GitHub CLI

**Windows**:
```powershell
winget install GitHub.cli
```

**Mac**:
```bash
brew install gh
```

**Linux (Ubuntu/Debian)**:
```bash
sudo apt install gh
```

### 步骤 2: 登录并配置

```bash
# 1. 登录 GitHub
gh auth login

# 2. 确认 .env 文件存在且包含所有 API keys
cat .env  # Linux/Mac
type .env  # Windows

# 3. 运行批量配置脚本
bash .github/setup-secrets.sh      # Linux/Mac
powershell .github\setup-secrets.ps1  # Windows

# 4. 验证配置
gh secret list
```

### 步骤 3: 测试运行

```bash
# 方法 1: 网页手动触发
# 访问: https://github.com/<用户名>/FinNews/actions
# 选择 "CI Tests" → "Run workflow"

# 方法 2: 命令行触发
gh workflow run ci.yml
```

---

## 📊 配置完成检查清单

```
安装工具:
☐ 安装 GitHub CLI: gh --version

登录验证:
☐ 登录 GitHub: gh auth status

准备 API Keys:
☐ .env 文件存在
☐ TAVILY_API_KEY 已填写
☐ FRED_API_KEY 已填写
☐ OPENROUTER_API_KEY 已填写
☐ Gmail 应用专用密码已获取

上传 Secrets:
☐ 运行批量配置脚本
☐ gh secret list 显示 7+ 个 secrets

验证运行:
☐ 手动触发 CI Tests workflow
☐ Workflow 运行成功（绿色勾）
```

---

## 💡 常见问题速查

### Q: 脚本提示 "未安装 GitHub CLI"
**A**: 运行 `winget install GitHub.cli` (Windows) 或 `brew install gh` (Mac)

### Q: 脚本提示 "未登录 GitHub CLI"
**A**: 运行 `gh auth login` 并按提示登录

### Q: 脚本提示 ".env 文件不存在"
**A**: 运行 `cp .env.example .env` 然后编辑 `.env` 填写 API keys

### Q: Workflow 报错 "Missing API Key"
**A**: 运行 `gh secret list` 检查是否所有必需的 secrets 都已配置

### Q: Gmail SMTP 认证失败
**A**: 确认使用的是**应用专用密码**（16 位），不是账号密码

### Q: 想删除某个 Secret
**A**: 运行 `gh secret remove SECRET_NAME`

### Q: 想更新某个 Secret
**A**: 再次运行 `gh secret set SECRET_NAME` 并输入新值

---

## 📚 详细文档

- **Secrets 配置详解**: `.github/SECRETS.md`
- **Workflows 使用说明**: `.github/WORKFLOWS.md`
- **项目文档**: `README.md`
- **代理指南**: `AGENTS.md`

---

## 🎯 总结

| 方法 | 耗时 | 难度 | 推荐度 |
|------|------|------|--------|
| 网页逐个配置 | 5-10 分钟 | ⭐ | ⭐⭐ |
| GitHub CLI 批量配置 | 1 分钟 | ⭐⭐ | ⭐⭐⭐⭐⭐ |

**建议**: 使用 GitHub CLI 批量配置，省时省力且不易出错！

---

**最后更新**: 2026-01-21
