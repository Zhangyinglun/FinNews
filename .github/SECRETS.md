# GitHub Secrets 配置指南

## 🎯 三种配置方法

### 方法 1: 网页界面逐个配置（最简单）

**步骤**：

1. **打开 Secrets 配置页面**
   ```
   https://github.com/<你的用户名>/FinNews/settings/secrets/actions
   ```

2. **点击 "New repository secret"**

3. **输入 Secret**
   - **Name**: `TAVILY_API_KEY`
   - **Value**: `tvly-xxxxxxxxxxxx`（你的实际 API key）

4. **点击 "Add secret"**

5. **重复步骤 2-4**，依次添加以下所有 secrets

---

### 方法 2: GitHub CLI 批量配置（推荐）⭐

**前提条件**：
- ✅ 已安装 [GitHub CLI](https://cli.github.com/)
- ✅ 已有 `.env` 文件（包含所有 API keys）

**Windows 用户**：
```powershell
# 1. 安装 GitHub CLI (如果未安装)
winget install GitHub.cli

# 2. 登录 GitHub
gh auth login

# 3. 运行批量配置脚本
powershell .github\setup-secrets.ps1
```

**Linux/Mac 用户**：
```bash
# 1. 安装 GitHub CLI (如果未安装)
# Mac: brew install gh
# Ubuntu: sudo apt install gh

# 2. 登录 GitHub
gh auth login

# 3. 运行批量配置脚本
bash .github/setup-secrets.sh
```

**优点**：
- ✅ 一次性上传所有 secrets
- ✅ 自动从 `.env` 文件读取
- ✅ 避免手动复制粘贴错误

---

### 方法 3: GitHub CLI 手动逐个配置

如果不想使用脚本，也可以手动使用 gh CLI：

```bash
# 登录 GitHub CLI
gh auth login

# 逐个添加 secrets (从 .env 文件中复制值)
gh secret set TAVILY_API_KEY
# 粘贴 API key 后按 Ctrl+D (Linux/Mac) 或 Ctrl+Z (Windows)

gh secret set FRED_API_KEY
# 粘贴 API key 后按 Ctrl+D/Ctrl+Z

# ... 依此类推
```

---

## 📋 必需的 Secrets 清单

### 必需配置（缺少会导致程序无法运行）

| Secret Name | 说明 | 示例值 | 获取方式 |
|-------------|------|--------|---------|
| `TAVILY_API_KEY` | Tavily API 密钥 | `tvly-xxxxxxxxxxxx` | [tavily.com](https://tavily.com/) 注册 |
| `FRED_API_KEY` | FRED API 密钥 | `xxxxxxxxxxxxxxxx` | [FRED API](https://fred.stlouisfed.org/docs/api/api_key.html) 注册 |
| `OPENROUTER_API_KEY` | OpenRouter API 密钥 | `sk-or-v1-xxxxxxxx` | [openrouter.ai](https://openrouter.ai/) 注册 |
| `SMTP_USERNAME` | SMTP 登录用户名 | `your-email@gmail.com` | 你的邮箱账号 |
| `SMTP_PASSWORD` | SMTP 登录密码 | `xxxx xxxx xxxx xxxx` | **Gmail 应用专用密码** |
| `EMAIL_FROM` | 发件人邮箱 | `your-email@gmail.com` | 同 SMTP_USERNAME |
| `EMAIL_TO` | 收件人邮箱 | `receiver@example.com` | 接收报告的邮箱 |

### 可选配置

| Secret Name | 说明 | 默认值 | 备注 |
|-------------|------|--------|------|
| `ALPHA_VANTAGE_API_KEY` | Alpha Vantage 密钥 | - | 可选数据源 |
| `OPENROUTER_MODEL` | LLM 模型名称 | 代码中配置 | 如需更改模型 |
| `OPENROUTER_HTTP_REFERER` | HTTP Referer | - | 可选 |
| `OPENROUTER_X_TITLE` | X-Title 头 | - | 可选 |
| `SMTP_HOST` | SMTP 服务器 | `smtp.gmail.com` | 非 Gmail 需配置 |
| `SMTP_PORT` | SMTP 端口 | `587` | 非标准端口需配置 |
| `SMTP_USE_TLS` | 是否使用 TLS | `true` | - |

---

## 🔐 获取各个 API Key 的详细步骤

### 1. Tavily API Key

1. 访问 https://tavily.com/
2. 点击 "Sign Up" 注册账号
3. 登录后进入 Dashboard
4. 找到 API Key 并复制（格式：`tvly-xxxxxxxxxxxx`）
5. **免费套餐**: 1000 次请求/月

### 2. FRED API Key

1. 访问 https://fred.stlouisfed.org/
2. 点击右上角 "My Account" → "API Keys"
3. 如无账号，先注册（免费）
4. 点击 "Request API Key"
5. 填写申请表单（用途可填写：Educational/Research）
6. 即时获得 API Key（格式：32 位字符串）
7. **完全免费**，无请求限制

### 3. OpenRouter API Key

1. 访问 https://openrouter.ai/
2. 注册/登录账号
3. 前往 https://openrouter.ai/keys
4. 点击 "Create Key" 创建新密钥
5. 复制 API Key（格式：`sk-or-v1-xxxxxxxxxxxx`）
6. **按使用量付费**，建议充值 $5-10 测试

### 4. Gmail SMTP 配置（重要！）

**错误方式** ❌：直接使用 Gmail 账号密码
**正确方式** ✅：使用应用专用密码

#### 步骤：

1. **启用两步验证**
   - 访问 https://myaccount.google.com/security
   - 找到 "两步验证"（2-Step Verification）
   - 按提示启用

2. **创建应用专用密码**
   - 访问 https://myaccount.google.com/apppasswords
   - 选择应用：选择 "邮件"
   - 选择设备：选择 "其他（自定义名称）"
   - 输入名称：`FinNews GitHub Actions`
   - 点击 "生成"
   - **复制 16 位密码**（格式：`xxxx xxxx xxxx xxxx`）

3. **配置 Secrets**
   ```
   SMTP_USERNAME = your-email@gmail.com
   SMTP_PASSWORD = xxxx xxxx xxxx xxxx  （应用专用密码）
   EMAIL_FROM = your-email@gmail.com
   EMAIL_TO = receiver@example.com  （可以是任何邮箱）
   ```

**注意事项**：
- ⚠️ 必须使用应用专用密码，不能用账号密码
- ⚠️ 如果无法创建应用专用密码，先启用两步验证
- ⚠️ 应用专用密码仅显示一次，请妥善保存

---

## ✅ 验证配置

### 方法 1: 网页查看

访问 Secrets 页面查看已配置的 secrets：
```
https://github.com/<你的用户名>/FinNews/settings/secrets/actions
```

你会看到类似：
```
TAVILY_API_KEY          Updated 2 minutes ago
FRED_API_KEY            Updated 2 minutes ago
OPENROUTER_API_KEY      Updated 2 minutes ago
...
```

**注意**：Secret 的值是不可见的（安全设计）

### 方法 2: GitHub CLI 查看

```bash
gh secret list
```

输出示例：
```
TAVILY_API_KEY          Updated 2 minutes ago
FRED_API_KEY            Updated 2 minutes ago
EMAIL_FROM              Updated 2 minutes ago
...
```

### 方法 3: 运行 Workflow 测试

1. 前往 Actions 页面
2. 选择 "CI Tests" workflow
3. 点击 "Run workflow" → "Run workflow"
4. 查看运行日志，确认没有 "Missing API Key" 错误

---

## 🛠️ 常见问题

### Q1: 如何更新已配置的 Secret?

**方法 1**: 网页界面
1. 进入 Secrets 页面
2. 找到要更新的 secret
3. 点击 "Update" 按钮
4. 输入新值并保存

**方法 2**: GitHub CLI
```bash
gh secret set TAVILY_API_KEY
# 输入新值，按 Ctrl+D/Ctrl+Z
```

### Q2: 如何删除 Secret?

**网页界面**：
1. 进入 Secrets 页面
2. 找到要删除的 secret
3. 点击 "Remove" 按钮

**GitHub CLI**：
```bash
gh secret remove TAVILY_API_KEY
```

### Q3: Secret 会被泄露吗?

**不会**。GitHub Secrets 有以下保护措施：
- ✅ 值加密存储，无法查看
- ✅ Workflow 日志中自动打码（显示 `***`）
- ✅ 仅当前仓库的 Workflows 可访问
- ✅ Fork 的仓库无法访问原仓库的 Secrets

### Q4: 可以在 Workflow 中查看 Secret 的值吗?

**不能直接查看**，但可以验证是否存在：

```yaml
- name: 验证 Secret
  run: |
    if [ -z "${{ secrets.TAVILY_API_KEY }}" ]; then
      echo "❌ TAVILY_API_KEY 未配置"
    else
      echo "✅ TAVILY_API_KEY 已配置"
    fi
```

**警告**：不要尝试 `echo ${{ secrets.XXX }}`，会被 GitHub 自动打码为 `***`

### Q5: 测试环境和生产环境如何分离?

**建议配置**：
- 生产环境: `TAVILY_API_KEY`（用于 finnews-schedule）
- 测试环境: `TAVILY_API_KEY_TEST`（用于 CI Tests）

在 workflow 中使用回退机制：
```yaml
env:
  TAVILY_API_KEY: ${{ secrets.TAVILY_API_KEY_TEST || secrets.TAVILY_API_KEY }}
```

如果 `TAVILY_API_KEY_TEST` 不存在，会使用 `TAVILY_API_KEY`。

---

## 📊 配置检查清单

配置完成后，逐项检查：

```
必需 Secrets（7个）:
☐ TAVILY_API_KEY - 从 tavily.com 获取
☐ FRED_API_KEY - 从 FRED 网站获取
☐ OPENROUTER_API_KEY - 从 openrouter.ai 获取
☐ SMTP_USERNAME - 你的 Gmail 地址
☐ SMTP_PASSWORD - Gmail 应用专用密码（16位）
☐ EMAIL_FROM - 同 SMTP_USERNAME
☐ EMAIL_TO - 接收报告的邮箱

可选 Secrets:
☐ ALPHA_VANTAGE_API_KEY - 可选数据源
☐ OPENROUTER_MODEL - 如需自定义模型
☐ TAVILY_API_KEY_TEST - 测试环境专用（推荐）
☐ FRED_API_KEY_TEST - 测试环境专用（推荐）

验证:
☐ gh secret list 能看到所有 secrets
☐ 运行 CI Tests workflow 没有报错
☐ 手动触发 finnews-schedule 能成功运行
```

---

## 🚀 快速配置（5 分钟完成）

如果你已有 `.env` 文件：

```powershell
# Windows
gh auth login
powershell .github\setup-secrets.ps1
gh secret list  # 验证
```

```bash
# Linux/Mac
gh auth login
bash .github/setup-secrets.sh
gh secret list  # 验证
```

**就这么简单！** 🎉

---

**最后更新**: 2026-01-21  
**维护者**: FinNews Team
