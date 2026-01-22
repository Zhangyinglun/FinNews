# GitHub Actions finnews-schedule 故障排查指南

## 🎉 最新修复 (2026-01-21)

### ✅ BOM 字符问题已修复

**问题**: `ValueError: invalid literal for int() with base 10: '\ufeff587'`

**根本原因**: `.env` 文件或 GitHub Secrets 包含 Unicode BOM (Byte Order Mark) 字符，导致类型转换失败。

**修复内容**:
- ✅ 添加环境变量清理函数，自动移除 BOM 和空格
- ✅ 修复 24 处环境变量读取（整数、浮点数、布尔、字符串）
- ✅ 增强配置验证，提前发现问题

**详细信息**: 查看 [BOM_FIX_REPORT.md](BOM_FIX_REPORT.md)

**如何验证修复**:
```bash
python test_bom_fix.py
```

---

## 问题概述

`finnews-schedule` workflow 运行失败的常见原因和解决方案。

---

## 修复内容 (2026-01-21)

### 1. 时区门控逻辑优化

**问题**: 原来的逻辑要求分钟数必须严格为 `00`，但 GitHub Actions 的 cron 触发和实际执行之间可能有延迟（通常 1-3 分钟），导致任务被跳过。

**修复**: 将时间窗口从 0 分钟扩展到 5 分钟容差：

```bash
# 修改前
if [ "$minute" != "00" ]; then
    echo "should_run=false"
    exit 0
fi

# 修改后
if [ "$minute" -gt "05" ]; then
    echo "should_run=false"
    exit 0
fi
```

### 2. 增强的配置验证

**新增**: 在运行主程序前验证所有必需的环境变量是否存在：

- `TAVILY_API_KEY`
- `FRED_API_KEY`
- `OPENROUTER_API_KEY`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `EMAIL_FROM`
- `EMAIL_TO`

这样可以在早期发现配置问题，而不是等到程序运行到一半才失败。

### 3. 改进的重试日志

**改进**: 重试逻辑现在输出更详细的中文日志，方便排查问题。

---

## 快速检查清单

### ✅ 步骤 1: 检查 GitHub Secrets

运行检查脚本验证配置：

**Linux / Mac:**
```bash
bash .github/check-secrets.sh
```

**Windows:**
```powershell
powershell .github\check-secrets.ps1
```

如果有缺失的 secrets，运行上传脚本：

**Linux / Mac:**
```bash
bash .github/setup-secrets.sh
```

**Windows:**
```powershell
powershell .github\setup-secrets.ps1
```

### ✅ 步骤 2: 手动触发测试

使用 GitHub CLI 手动触发 workflow 测试：

```bash
gh workflow run finnews-schedule.yml
```

查看运行状态：

```bash
gh run list --workflow=finnews-schedule.yml --limit=5
```

查看详细日志：

```bash
# 获取最新运行的 ID
gh run list --workflow=finnews-schedule.yml --limit=1 --json databaseId --jq '.[0].databaseId'

# 查看日志（替换 <run-id>）
gh run view <run-id> --log
```

### ✅ 步骤 3: 检查时区设置

workflow 配置了 `TZ: America/Los_Angeles`，确保：

1. cron 时间是 UTC 时间
2. 门控逻辑检查的是 PT (Pacific Time) 时间
3. 当前修复后允许 ±5 分钟误差

---

## 常见失败原因

### 1. ⏰ 时间门控失败

**症状**: workflow 运行了，但所有步骤都被跳过

**原因**: `should_run=false`，时间不匹配

**解决方案**:
- 检查是否在 08:00 或 20:00 PT 运行
- 新版本已允许 5 分钟容差窗口
- 使用 `workflow_dispatch` 手动触发可以绕过时间检查

### 2. 🔑 API Key 缺失或无效

**症状**: 
```
❌ 配置错误: 缺少必需的API密钥
❌ 缺少必需的环境变量: TAVILY_API_KEY
```

**解决方案**:
1. 运行 `.github/check-secrets.sh` 检查
2. 确认本地 `.env` 文件包含所有 keys
3. 运行 `.github/setup-secrets.sh` 上传
4. 在 GitHub 网页端验证: `Settings` → `Secrets and variables` → `Actions`

### 3. 📧 邮件发送失败

**症状**:
```
❌ 邮件发送失败
❌ SMTP authentication failed
```

**解决方案**:
- 确认 Gmail 使用的是 **应用专用密码**（不是账户密码）
- 获取应用专用密码: https://myaccount.google.com/apppasswords
- 确认 `SMTP_USERNAME` 是完整的邮箱地址
- 确认 `SMTP_PORT=587` 和 `SMTP_USE_TLS=true`

### 4. 🌐 网络请求失败

**症状**:
```
❌ Tavily爬虫初始化失败
❌ Request timeout
```

**解决方案**:
- 检查 API 密钥是否有效（在提供商网站登录验证）
- 检查是否超出 API 配额
- 等待一段时间后重试（可能是临时网络问题）
- 禁用失败的数据源（在 `.env` 中设置 `ENABLE_TAVILY=false`）

### 5. 🤖 LLM 调用失败

**症状**:
```
❌ LLM调用失败
❌ OpenRouter API error
```

**解决方案**:
- 确认 `OPENROUTER_API_KEY` 有效
- 检查 OpenRouter 账户余额: https://openrouter.ai/
- 检查选择的模型是否可用: `OPENROUTER_MODEL=google/gemini-3-pro-preview`
- 减少 `OPENROUTER_MAX_TOKENS` 或增加 `OPENROUTER_TIMEOUT`

### 6. 🏦 COMEX 爬虫失败

**症状**:
```
⚠️ COMEX爬虫初始化失败
⚠️ COMEX数据获取失败
```

**解决方案**:
- 这是 **非致命错误**，不会导致整个 workflow 失败
- COMEX 数据用于库存预警，缺失不影响主要功能
- 检查 `scrapers/comex_scraper.py` 的网站抓取逻辑是否过期

---

## 调试技巧

### 查看完整的 workflow 日志

在 GitHub 网页端：

1. 访问: `https://github.com/Zhangyinglun/FinNews/actions`
2. 点击失败的 workflow 运行
3. 展开各个步骤查看详细日志

或使用 GitHub CLI：

```bash
gh run view <run-id> --log-failed
```

### 本地测试

在本地环境模拟 GitHub Actions：

```bash
# 设置环境变量
export TZ=America/Los_Angeles
export TAVILY_API_KEY=tvly-...
export FRED_API_KEY=...
# ... 其他环境变量

# 运行主程序
python main.py
```

### 启用调试日志

在 `.env` 中设置：

```env
LOG_LEVEL=DEBUG
```

重新运行 workflow 将输出更详细的调试信息。

---

## 验证修复是否成功

### 方法 1: 手动触发测试

```bash
gh workflow run finnews-schedule.yml
sleep 10  # 等待启动
gh run list --workflow=finnews-schedule.yml --limit=1
```

### 方法 2: 查看下次定时运行

workflow 配置为每天 08:00 和 20:00 PT 自动运行。

查看下次运行时间（UTC）：
- 08:00 PT = 15:00/16:00 UTC (取决于 PDT/PST)
- 20:00 PT = 03:00/04:00 UTC (取决于 PDT/PST)

### 方法 3: 查看邮件

如果配置正确，你应该会在 `EMAIL_TO` 地址收到邮件摘要。

---

## 还有问题?

### 收集诊断信息

运行以下命令并提供输出：

```bash
# 1. 检查 secrets 配置
bash .github/check-secrets.sh

# 2. 查看最近的运行记录
gh run list --workflow=finnews-schedule.yml --limit=5

# 3. 查看最新失败的详细日志
gh run view $(gh run list --workflow=finnews-schedule.yml --limit=1 --json databaseId --jq '.[0].databaseId') --log-failed
```

### 联系支持

将上述诊断信息和以下内容一起提供：

- 失败时间（包括时区）
- 是定时触发还是手动触发
- 本地 `python main.py` 是否能成功运行
- 使用的 Python 版本: `python --version`

---

## 相关文档

- [QUICKSTART.md](.github/QUICKSTART.md) - 快速开始指南
- [SECRETS.md](.github/SECRETS.md) - Secrets 详细配置
- [WORKFLOWS.md](.github/WORKFLOWS.md) - Workflows 完整说明

---

**最后更新**: 2026-01-21  
**维护者**: FinNews Team
