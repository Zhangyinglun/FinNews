# GitHub Actions Workflows 使用说明

## 📋 Workflow 清单

本项目包含以下 GitHub Actions workflows：

### 1. 🕐 **finnews-schedule.yml** - 定时执行（生产环境）

**用途**: 每天自动运行数据抓取和邮件发送任务

**触发时机**:
- 定时：每天 08:00 和 20:00（太平洋时间）
- 手动：GitHub Actions 页面手动触发

**配置要求**:
需要在 GitHub Repository → Settings → Secrets and variables → Actions 中配置以下 secrets：

#### 必需的 Secrets:
- `TAVILY_API_KEY` - Tavily API 密钥
- `FRED_API_KEY` - FRED API 密钥
- `OPENROUTER_API_KEY` - OpenRouter API 密钥（LLM）
- `SMTP_USERNAME` - SMTP 用户名
- `SMTP_PASSWORD` - SMTP 密码
- `EMAIL_FROM` - 发件人邮箱
- `EMAIL_TO` - 收件人邮箱（多个用逗号分隔）

#### 可选的 Secrets:
- `ALPHA_VANTAGE_API_KEY` - Alpha Vantage API 密钥
- `OPENROUTER_MODEL` - LLM 模型名称（默认值在代码中配置）
- `OPENROUTER_HTTP_REFERER` - OpenRouter HTTP Referer
- `OPENROUTER_X_TITLE` - OpenRouter X-Title
- `SMTP_HOST` - SMTP 服务器（默认：smtp.gmail.com）
- `SMTP_PORT` - SMTP 端口（默认：587）
- `SMTP_USE_TLS` - 是否使用 TLS（默认：true）

**特性**:
- ✅ 智能 jitter（随机延迟 0-600 秒，避开流量高峰）
- ✅ 自动重试（3 次，指数退避）
- ✅ 保存输出产物（14 天保留期）
- ✅ 并发控制（同时只运行一个实例）

---

### 2. 🧪 **ci.yml** - 持续集成测试

**用途**: 自动运行测试套件，确保代码质量

**触发时机**:
- Push 到 main 或 develop 分支
- Pull Request 到 main 或 develop 分支
- 手动触发

**测试内容**:
- ✅ Python 3.10 和 3.11 兼容性测试
- ✅ 快速测试套件（Push 时运行）
- ✅ 完整测试套件（PR 时运行）
- ✅ 代码格式检查（Black, isort）
- ✅ Linting 检查（Ruff）
- ✅ 类型检查（MyPy）

**配置要求**:
- `TAVILY_API_KEY_TEST` - 测试环境的 Tavily 密钥（可选，回退到生产密钥）
- `FRED_API_KEY_TEST` - 测试环境的 FRED 密钥（可选，回退到生产密钥）

**注意**:
- 代码格式和 Linting 检查设置为 `continue-on-error: true`，不会阻止 workflow
- 建议但不强制遵守代码规范

---

### 3. 🔒 **security.yml** - 安全检查

**用途**: 定期检查依赖漏洞和敏感信息泄露

**触发时机**:
- 定时：每周一 08:00 UTC
- Pull Request 中修改 requirements.txt
- 手动触发

**检查内容**:
- ✅ 依赖审查（Dependency Review）
- ✅ 安全漏洞扫描（pip-audit）
- ✅ 敏感信息泄露扫描（TruffleHog）

**无需配置** - 使用 GitHub 内置 token

---

### 4. 🔄 **dependency-update.yml** - 依赖更新提醒

**用途**: 自动检测可更新的依赖并创建 Issue

**触发时机**:
- 定时：每周日 10:00 UTC
- 手动触发

**功能**:
- ✅ 检测所有过期的依赖包
- ✅ 自动创建 Issue 列出可更新的包
- ✅ 打上 `dependencies` 和 `automated` 标签

**无需配置** - 使用 GitHub CLI 和内置 token

---

## 🚀 快速开始

### 1. 配置 Secrets

前往仓库设置页面配置必需的 secrets：

```
https://github.com/<username>/<repo>/settings/secrets/actions
```

点击 **New repository secret** 按钮，依次添加上述必需的 secrets。

### 2. 启用 Workflows

前往 Actions 页面：

```
https://github.com/<username>/<repo>/actions
```

如果 workflows 被禁用，点击 **I understand my workflows, go ahead and enable them** 按钮。

### 3. 测试运行

#### 方法 1: 手动触发
1. 前往 Actions 页面
2. 选择想要运行的 workflow（如 `CI Tests`）
3. 点击 **Run workflow** 按钮
4. 选择分支后点击 **Run workflow**

#### 方法 2: 提交代码触发
```bash
# CI Tests 会自动运行
git add .
git commit -m "测试 CI workflow"
git push origin main
```

---

## 📝 Workflow 文件说明

### finnews-schedule.yml
```yaml
定时：cron 表达式（UTC 时间）
重试：最多 3 次，指数退避（2, 4, 8 秒）
超时：30 分钟
Jitter：0-600 秒随机延迟
产物：outputs/ 目录，保留 14 天
```

### ci.yml
```yaml
Python 版本：3.10, 3.11
快速测试：push 触发
完整测试：PR 触发
Linting：非阻塞（continue-on-error）
```

### security.yml
```yaml
频率：每周一
工具：dependency-review, pip-audit, TruffleHog
权限：security-events:write（用于 SARIF 上传）
```

### dependency-update.yml
```yaml
频率：每周日
输出：创建 Issue
标签：dependencies, automated
```

---

## 🛠️ 故障排除

### Workflow 运行失败

#### 1. 检查 Secrets 配置
确保所有必需的 secrets 已正确配置：
```bash
# 在本地测试 secrets 是否有效
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
print('TAVILY_API_KEY:', 'OK' if os.getenv('TAVILY_API_KEY') else 'Missing')
print('FRED_API_KEY:', 'OK' if os.getenv('FRED_API_KEY') else 'Missing')
"
```

#### 2. 查看 Workflow 日志
1. 前往 Actions 页面
2. 点击失败的 workflow run
3. 查看具体步骤的日志输出
4. 搜索 `ERROR` 或 `❌` 关键词

#### 3. 常见错误

**错误**: `Missing API Key`
**解决**: 检查 GitHub Secrets 中是否配置了对应的 API key

**错误**: `Rate Limit Exceeded`
**解决**: Tavily 免费套餐限制为 1000 次/月，检查用量或升级计划

**错误**: `SMTP Authentication Failed`
**解决**: 
- Gmail: 需要使用应用专用密码（非账号密码）
- 前往 Google Account → Security → 2-Step Verification → App passwords

**错误**: `pip-audit found vulnerabilities`
**解决**: 查看日志中列出的漏洞，更新对应的依赖包

### 手动禁用 Workflow

如需临时禁用某个 workflow：

1. 前往 Actions 页面
2. 左侧选择要禁用的 workflow
3. 点击右上角 `...` 菜单
4. 选择 **Disable workflow**

---

## 📊 监控和通知

### 邮件通知

GitHub 默认会在 workflow 失败时发送邮件通知给：
- Workflow 触发者
- 仓库的 Watch 用户（Settings → Notifications）

### Slack/Discord 通知（可选）

如需添加 Slack/Discord 通知，可在 workflow 中添加：

```yaml
- name: 发送 Slack 通知
  if: failure()
  uses: slackapi/slack-github-action@v1
  with:
    payload: |
      {
        "text": "FinNews workflow 失败: ${{ github.workflow }}"
      }
  env:
    SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

---

## 🎯 最佳实践

### 1. 保护生产密钥
- ✅ 为测试环境配置单独的 API keys（`*_TEST`）
- ✅ 定期轮换 API keys 和密码
- ✅ 使用最小权限原则

### 2. 监控用量
- ✅ 定期检查 Tavily API 用量（1000 次/月限制）
- ✅ 监控 OpenRouter 费用
- ✅ 关注 GitHub Actions 分钟数用量

### 3. 优化成本
- ✅ 快速测试用于频繁 push
- ✅ 完整测试仅用于 PR
- ✅ 定时任务使用 jitter 避免流量高峰

### 4. 安全审计
- ✅ 定期检查 Security workflow 的报告
- ✅ 及时更新有漏洞的依赖
- ✅ 不要在代码中硬编码密钥

---

## 📚 参考资源

- [GitHub Actions 文档](https://docs.github.com/en/actions)
- [Python setup-python Action](https://github.com/actions/setup-python)
- [Workflow 语法参考](https://docs.github.com/en/actions/reference/workflow-syntax-for-github-actions)
- [Encrypted Secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets)

---

**最后更新**: 2026-01-21  
**维护者**: FinNews Team
