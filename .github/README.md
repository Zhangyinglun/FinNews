# GitHub Actions 配置文档索引

本目录包含 FinNews 项目的 GitHub Actions 配置和文档。

## 📁 目录结构

```
.github/
├── workflows/                    # GitHub Actions workflow 文件
│   ├── finnews-schedule.yml     # 生产环境定时执行
│   ├── ci.yml                   # 持续集成测试
│   ├── security.yml             # 安全检查
│   └── dependency-update.yml    # 依赖更新提醒
│
├── setup-secrets.sh             # Secrets 批量配置脚本 (Linux/Mac)
├── setup-secrets.ps1            # Secrets 批量配置脚本 (Windows)
│
├── QUICKSTART.md                # ⭐ 快速开始（推荐先看）
├── SECRETS.md                   # Secrets 详细配置指南
├── WORKFLOWS.md                 # Workflows 使用说明
└── README.md                    # 本文件
```

## 🚀 快速开始

### 第一次配置？从这里开始：

1. **阅读快速开始指南**
   ```
   .github/QUICKSTART.md
   ```

2. **配置 GitHub Secrets**
   ```bash
   # 详细步骤见 .github/SECRETS.md
   
   # 快速配置（推荐）:
   gh auth login
   bash .github/setup-secrets.sh        # Linux/Mac
   powershell .github\setup-secrets.ps1  # Windows
   ```

3. **启用 Workflows**
   - 访问: `https://github.com/<你的用户名>/FinNews/actions`
   - 点击 "I understand my workflows, go ahead and enable them"

4. **测试运行**
   ```bash
   gh workflow run ci.yml
   ```

## 📚 文档说明

### [QUICKSTART.md](QUICKSTART.md) - 快速参考 ⭐
- ✅ 最快配置方法（1 分钟完成）
- ✅ 常见问题速查
- ✅ 配置检查清单
- **推荐**: 第一次配置必读

### [SECRETS.md](SECRETS.md) - Secrets 配置详解
- 📝 三种配置方法对比
- 📝 必需和可选 Secrets 清单
- 📝 各个 API Key 获取步骤
- 📝 Gmail 应用专用密码详细教程
- 📝 常见问题解答
- **推荐**: 遇到配置问题时查阅

### [WORKFLOWS.md](WORKFLOWS.md) - Workflows 使用手册
- 📖 4 个 Workflows 详细说明
- 📖 触发时机和配置要求
- 📖 故障排除指南
- 📖 最佳实践建议
- **推荐**: 了解各个 Workflow 的作用

## 🎯 核心 Workflows

### 1. finnews-schedule.yml - 生产环境
- **作用**: 每天自动运行数据抓取和邮件发送
- **触发**: 每天 08:00 & 20:00 PT
- **状态**: ✅ 已配置（生产就绪）

### 2. ci.yml - 持续集成
- **作用**: 自动运行测试套件
- **触发**: Push / PR 到 main/develop
- **状态**: 🆕 新增

### 3. security.yml - 安全检查
- **作用**: 扫描依赖漏洞和敏感信息
- **触发**: 每周一 + PR 修改依赖
- **状态**: 🆕 新增

### 4. dependency-update.yml - 依赖更新
- **作用**: 自动检测过期依赖并创建 Issue
- **触发**: 每周日
- **状态**: 🆕 新增

## 🔧 配置脚本

### setup-secrets.sh / setup-secrets.ps1
批量上传 Secrets 到 GitHub 的自动化脚本。

**使用方法**:
```bash
# Linux/Mac
bash .github/setup-secrets.sh

# Windows
powershell .github\setup-secrets.ps1
```

**前提条件**:
- ✅ 已安装 GitHub CLI
- ✅ 已登录 GitHub (`gh auth login`)
- ✅ `.env` 文件存在且包含所有 API keys

## ❓ 常见问题

### Q: 从哪里开始？
**A**: 按顺序阅读:
1. `QUICKSTART.md` - 了解配置流程
2. `SECRETS.md` - 配置 GitHub Secrets
3. `WORKFLOWS.md` - 了解 Workflows 功能

### Q: 必须配置哪些 Secrets？
**A**: 7 个必需 Secrets（详见 `SECRETS.md`）:
```
TAVILY_API_KEY
FRED_API_KEY
OPENROUTER_API_KEY
SMTP_USERNAME
SMTP_PASSWORD
EMAIL_FROM
EMAIL_TO
```

### Q: 如何验证配置是否成功？
**A**: 运行以下命令:
```bash
gh secret list                    # 查看已配置的 Secrets
gh workflow run ci.yml           # 手动触发测试
gh run list --limit 5            # 查看最近的运行记录
```

### Q: Workflow 运行失败怎么办？
**A**: 
1. 查看 Actions 页面的日志
2. 参考 `WORKFLOWS.md` 的故障排除章节
3. 检查 Secrets 是否配置正确

### Q: 如何临时禁用某个 Workflow？
**A**:
1. 前往 Actions 页面
2. 选择要禁用的 Workflow
3. 点击右上角 `...` → "Disable workflow"

## 🔗 相关链接

- **GitHub Actions 文档**: https://docs.github.com/en/actions
- **GitHub CLI 文档**: https://cli.github.com/manual/
- **项目主 README**: `../README.md`
- **项目代理指南**: `../AGENTS.md`

## 📞 支持

遇到问题？
1. 查看本目录下的文档（`QUICKSTART.md`, `SECRETS.md`, `WORKFLOWS.md`）
2. 查看 GitHub Actions 运行日志
3. 提交 Issue 到项目仓库

---

**最后更新**: 2026-01-21  
**维护者**: FinNews Team
