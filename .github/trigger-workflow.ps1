# 手动触发 GitHub Actions workflow 来测试修复
# Windows PowerShell 版本

$ErrorActionPreference = "Stop"

Write-Host "🚀 准备触发 finnews-schedule workflow..." -ForegroundColor Cyan
Write-Host ""

# 检查 gh CLI
if (!(Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Host "❌ 未安装 GitHub CLI" -ForegroundColor Red
    Write-Host "请访问 https://cli.github.com/ 安装"
    exit 1
}

# 检查登录状态
$authStatus = gh auth status 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 未登录 GitHub CLI" -ForegroundColor Red
    Write-Host "请运行: gh auth login"
    exit 1
}

Write-Host "✅ GitHub CLI 已就绪" -ForegroundColor Green
Write-Host ""

# 显示当前提交
$currentSha = git rev-parse HEAD
$currentShortSha = git rev-parse --short HEAD
$currentMessage = (git log -1 --pretty=%B | Select-Object -First 1)

Write-Host "📍 当前提交:" -ForegroundColor Cyan
Write-Host "  SHA: $currentSha"
Write-Host "  消息: $currentMessage"
Write-Host ""

# 确认是否是修复提交
if ($currentMessage -match "BOM" -or $currentShortSha -eq "8f67bdf") {
    Write-Host "✅ 当前提交包含 BOM 修复" -ForegroundColor Green
} else {
    Write-Host "⚠️  警告: 当前提交可能不包含 BOM 修复" -ForegroundColor Yellow
    Write-Host "请确认你在正确的分支上"
}

Write-Host ""
Write-Host "准备触发 workflow 'finnews-schedule'..."
Write-Host "这将使用最新的代码 (提交 $currentShortSha)"
Write-Host ""

$confirmation = Read-Host "是否继续? (y/N)"
if ($confirmation -notmatch '^[Yy]$') {
    Write-Host "已取消"
    exit 0
}

Write-Host ""
Write-Host "🚀 触发 workflow..." -ForegroundColor Cyan

# 触发 workflow
gh workflow run finnews-schedule.yml 2>&1 | Out-Null

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ Workflow 已触发!" -ForegroundColor Green
    Write-Host ""
    Write-Host "等待 5 秒后查看运行状态..."
    Start-Sleep -Seconds 5
    
    Write-Host ""
    Write-Host "📋 最近的运行记录:" -ForegroundColor Cyan
    gh run list --workflow=finnews-schedule.yml --limit=3
    
    Write-Host ""
    Write-Host "💡 查看详细日志:" -ForegroundColor Cyan
    Write-Host "  gh run view --workflow=finnews-schedule.yml --log"
    Write-Host ""
    
    $repoUrl = git remote get-url origin
    $repoPath = $repoUrl -replace '.*github\.com[:/](.*?)(?:\.git)?$', '$1'
    Write-Host "或访问:"
    Write-Host "  https://github.com/$repoPath/actions"
} else {
    Write-Host ""
    Write-Host "❌ 触发失败" -ForegroundColor Red
    exit 1
}
