# 检查 GitHub Secrets 是否正确配置
# Windows PowerShell 版本

Write-Host "🔍 检查 GitHub Secrets 配置状态..." -ForegroundColor Cyan
Write-Host ""

# 需要的 Secrets 列表
$REQUIRED_SECRETS = @(
    "TAVILY_API_KEY",
    "FRED_API_KEY",
    "OPENROUTER_API_KEY",
    "SMTP_USERNAME",
    "SMTP_PASSWORD",
    "EMAIL_FROM",
    "EMAIL_TO"
)

$OPTIONAL_SECRETS = @(
    "ALPHA_VANTAGE_API_KEY",
    "OPENROUTER_MODEL",
    "OPENROUTER_HTTP_REFERER",
    "OPENROUTER_X_TITLE",
    "SMTP_HOST",
    "SMTP_PORT",
    "SMTP_USE_TLS"
)

# 检查 gh CLI 是否安装
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Host "❌ GitHub CLI (gh) 未安装" -ForegroundColor Red
    Write-Host "请访问: https://cli.github.com/ 安装"
    exit 1
}

# 检查是否登录
$authStatus = gh auth status 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 未登录 GitHub CLI" -ForegroundColor Red
    Write-Host "请运行: gh auth login"
    exit 1
}

Write-Host "✅ GitHub CLI 已就绪" -ForegroundColor Green
Write-Host ""

# 获取已配置的 secrets
Write-Host "📋 已配置的 Secrets:" -ForegroundColor Cyan
$secretsList = gh secret list | Out-String
Write-Host $secretsList

Write-Host ""
Write-Host "🔍 验证必需的 Secrets..." -ForegroundColor Cyan

$missingSecrets = @()
foreach ($secret in $REQUIRED_SECRETS) {
    if ($secretsList -match "^$secret\s") {
        Write-Host "  ✅ $secret" -ForegroundColor Green
    } else {
        Write-Host "  ❌ $secret (缺失)" -ForegroundColor Red
        $missingSecrets += $secret
    }
}

Write-Host ""
Write-Host "🔍 可选的 Secrets..." -ForegroundColor Cyan

foreach ($secret in $OPTIONAL_SECRETS) {
    if ($secretsList -match "^$secret\s") {
        Write-Host "  ✅ $secret" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  $secret (未配置，使用默认值)" -ForegroundColor Yellow
    }
}

Write-Host ""
if ($missingSecrets.Count -eq 0) {
    Write-Host "✅ 所有必需的 Secrets 已配置!" -ForegroundColor Green
    Write-Host ""
    Write-Host "💡 你可以运行以下命令手动触发 workflow 测试:" -ForegroundColor Cyan
    Write-Host "   gh workflow run finnews-schedule.yml"
    Write-Host ""
    Write-Host "或者查看最近的运行记录:" -ForegroundColor Cyan
    Write-Host "   gh run list --workflow=finnews-schedule.yml --limit=5"
    exit 0
} else {
    Write-Host "❌ 缺少以下必需的 Secrets:" -ForegroundColor Red
    foreach ($secret in $missingSecrets) {
        Write-Host "   - $secret"
    }
    Write-Host ""
    Write-Host "💡 请使用以下脚本上传 Secrets:" -ForegroundColor Cyan
    Write-Host "   powershell .github\setup-secrets.ps1"
    exit 1
}
