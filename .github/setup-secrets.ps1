# GitHub Secrets 批量配置脚本 (PowerShell 版本)
# 使用方法: powershell .github\setup-secrets.ps1

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "GitHub Secrets 批量配置工具 (PowerShell)"
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# 检查 gh CLI 是否安装
if (!(Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Host "❌ 错误: 未安装 GitHub CLI" -ForegroundColor Red
    Write-Host "请先安装: https://cli.github.com/"
    exit 1
}

# 检查是否已登录
$authStatus = gh auth status 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 错误: 未登录 GitHub CLI" -ForegroundColor Red
    Write-Host "请运行: gh auth login"
    exit 1
}

# 检查 .env 文件是否存在
if (!(Test-Path .env)) {
    Write-Host "❌ 错误: .env 文件不存在" -ForegroundColor Red
    Write-Host "请先创建 .env 文件（参考 .env.example）"
    exit 1
}

Write-Host "✅ 环境检查通过" -ForegroundColor Green
Write-Host ""
Write-Host "准备从 .env 文件读取并上传 secrets..."
Write-Host "⚠️  警告: 这将覆盖已存在的同名 secrets" -ForegroundColor Yellow
Write-Host ""

$confirmation = Read-Host "是否继续? (y/N)"
if ($confirmation -notmatch '^[Yy]$') {
    Write-Host "已取消"
    exit 0
}

Write-Host ""
Write-Host "开始上传 secrets..."
Write-Host "==========================================" -ForegroundColor Cyan

# 读取 .env 文件并上传
$uploaded = 0
$skipped = 0

Get-Content .env | ForEach-Object {
    $line = $_.Trim()
    
    # 跳过空行和注释
    if ([string]::IsNullOrWhiteSpace($line) -or $line.StartsWith('#')) {
        return
    }
    
    # 解析 key=value
    if ($line -match '^([^=]+)=(.*)$') {
        $key = $matches[1].Trim()
        $value = $matches[2].Trim()
        
        # 移除引号
        $value = $value -replace '^["'']|["'']$', ''
        
        # 跳过空值
        if ([string]::IsNullOrWhiteSpace($value)) {
            return
        }
        
        # 上传 secret
        Write-Host "上传 $key ... " -NoNewline
        try {
            $value | gh secret set $key 2>&1 | Out-Null
            if ($LASTEXITCODE -eq 0) {
                Write-Host "✅" -ForegroundColor Green
                $script:uploaded++
            } else {
                Write-Host "❌ 失败" -ForegroundColor Red
                $script:skipped++
            }
        } catch {
            Write-Host "❌ 失败" -ForegroundColor Red
            $script:skipped++
        }
    }
}

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "完成!"
Write-Host "✅ 成功上传: $uploaded 个" -ForegroundColor Green
Write-Host "❌ 失败: $skipped 个" -ForegroundColor Red
Write-Host ""
Write-Host "验证 secrets:"
gh secret list
