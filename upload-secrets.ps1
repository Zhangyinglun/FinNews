# GitHub Secrets 批量上传脚本 - 终极简化版
# 使用方法: 
#   1. 先运行: gh auth login
#   2. 再运行此脚本

$ErrorActionPreference = "Continue"

# 设置 GitHub CLI 路径
$ghPath = "C:\Program Files\GitHub CLI"
if (Test-Path $ghPath) {
    $env:PATH = "$ghPath;$env:PATH"
}

# 检查 gh 命令是否可用
try {
    $ghVersion = & gh --version 2>&1 | Select-Object -First 1
    Write-Host "✅ GitHub CLI: $ghVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ 错误: 找不到 gh 命令" -ForegroundColor Red
    Write-Host ""
    Write-Host "请关闭所有 PowerShell 窗口，重新打开后再试" -ForegroundColor Yellow
    Write-Host "或运行: " -ForegroundColor Yellow
    Write-Host '  $env:PATH = "C:\Program Files\GitHub CLI;$env:PATH"' -ForegroundColor Yellow
    exit 1
}

# 检查 gh 登录状态
Write-Host "检查 GitHub 登录状态..." -ForegroundColor Cyan
$authStatus = & gh auth status 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 未登录 GitHub CLI" -ForegroundColor Red
    Write-Host ""
    Write-Host "请先运行: gh auth login" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "登录后重新运行此脚本"
    exit 1
}
Write-Host "✅ GitHub 已登录" -ForegroundColor Green

Write-Host ""
Write-Host "=" -NoNewline; 1..79 | % { Write-Host "=" -NoNewline }; Write-Host ""
Write-Host "GitHub Secrets 批量配置工具"
Write-Host "=" -NoNewline; 1..79 | % { Write-Host "=" -NoNewline }; Write-Host ""
Write-Host ""

# 仓库信息
$REPO_OWNER = "Zhangyinglun"
$REPO_NAME = "FinNews"

Write-Host "📦 仓库: $REPO_OWNER/$REPO_NAME"
Write-Host ""

# 检查 .env 文件
if (!(Test-Path ".env")) {
    Write-Host "❌ .env 文件不存在" -ForegroundColor Red
    exit 1
}

Write-Host "✅ .env 文件存在" -ForegroundColor Green
Write-Host ""

# 读取 .env 文件
$secrets = @{}
Get-Content ".env" | ForEach-Object {
    $line = $_.Trim()
    if ($line -and !$line.StartsWith('#') -and $line.Contains('=')) {
        $parts = $line -split '=', 2
        $key = $parts[0].Trim()
        $value = $parts[1].Trim() -replace '^["'']|["'']$', ''
        if ($value) {
            $secrets[$key] = $value
        }
    }
}

# 必需的 secrets
$required = @(
    "TAVILY_API_KEY",
    "FRED_API_KEY",
    "OPENROUTER_API_KEY",
    "SMTP_USERNAME",
    "SMTP_PASSWORD",
    "EMAIL_FROM",
    "EMAIL_TO"
)

# 可选的 secrets
$optional = @(
    "ALPHA_VANTAGE_API_KEY",
    "OPENROUTER_MODEL",
    "SMTP_HOST",
    "SMTP_PORT"
)

# 检查必需的 secrets
$missing = @()
foreach ($key in $required) {
    if (!$secrets.ContainsKey($key)) {
        $missing += $key
    }
}

if ($missing.Count -gt 0) {
    Write-Host "❌ 缺少必需的配置:" -ForegroundColor Red
    $missing | ForEach-Object { Write-Host "   - $_" -ForegroundColor Red }
    exit 1
}

# 显示将要上传的 secrets
$toUpload = @()
foreach ($key in $required) {
    $toUpload += @{Key=$key; Value=$secrets[$key]; Required=$true}
}
foreach ($key in $optional) {
    if ($secrets.ContainsKey($key)) {
        $toUpload += @{Key=$key; Value=$secrets[$key]; Required=$false}
    }
}

Write-Host "📊 将要上传 $($toUpload.Count) 个 secrets:"
Write-Host ""

foreach ($item in $toUpload) {
    $key = $item.Key
    $value = $item.Value
    $masked = if ($value.Length -gt 10) {
        "$($value.Substring(0,4))...$($value.Substring($value.Length-4))"
    } else {
        "***"
    }
    $type = if ($item.Required) { "[必需]" } else { "[可选]" }
    Write-Host "  $type $key = $masked"
}

Write-Host ""
Write-Host "⚠️  警告: 这将覆盖 GitHub 上已存在的同名 secrets" -ForegroundColor Yellow
Write-Host ""

$confirm = Read-Host "确认上传? (y/N)"
if ($confirm -notmatch '^[Yy是]') {
    Write-Host "已取消"
    exit 0
}

Write-Host ""
Write-Host "🚀 开始上传..." -ForegroundColor Cyan
Write-Host ""

$successCount = 0
$failCount = 0

foreach ($item in $toUpload) {
    $key = $item.Key
    $value = $item.Value
    
    $paddedKey = $key.PadRight(30)
    Write-Host "   $paddedKey ... " -NoNewline
    
    try {
        # 使用 gh CLI 上传 secret
        $value | & gh secret set $key --repo "$REPO_OWNER/$REPO_NAME" 2>&1 | Out-Null
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅" -ForegroundColor Green
            $successCount++
        } else {
            Write-Host "❌ (错误码: $LASTEXITCODE)" -ForegroundColor Red
            $failCount++
        }
    } catch {
        Write-Host "❌ $_" -ForegroundColor Red
        $failCount++
    }
}

Write-Host ""
Write-Host "=" -NoNewline; 1..79 | % { Write-Host "=" -NoNewline }; Write-Host ""
Write-Host "完成!" -ForegroundColor Cyan
Write-Host "=" -NoNewline; 1..79 | % { Write-Host "=" -NoNewline }; Write-Host ""
Write-Host ""
Write-Host "✅ 成功: $successCount 个" -ForegroundColor Green
if ($failCount -gt 0) {
    Write-Host "❌ 失败: $failCount 个" -ForegroundColor Red
}
Write-Host ""

if ($successCount -gt 0) {
    Write-Host "🎉 Secrets 配置完成!" -ForegroundColor Green
    Write-Host ""
    Write-Host "下一步:"
    Write-Host "  1. 查看 secrets:"
    Write-Host "     https://github.com/$REPO_OWNER/$REPO_NAME/settings/secrets/actions"
    Write-Host ""
    Write-Host "  2. 启用 workflows:"
    Write-Host "     https://github.com/$REPO_OWNER/$REPO_NAME/actions"
    Write-Host ""
}
