# BOM 字符问题修复报告

## 问题描述

**错误**: `ValueError: invalid literal for int() with base 10: '\ufeff587'`

**位置**: `config/config.py` 第 300 行（修复前）

**原因**: `.env` 文件或 GitHub Secrets 中的环境变量值包含 Unicode BOM (Byte Order Mark) 字符 `\ufeff`，导致 `int()` 类型转换失败。

---

## 根本原因

### 什么是 BOM？

BOM (Byte Order Mark) 是一个特殊的 Unicode 字符 (`U+FEFF`)，用于标识文本文件的编码格式：

- **UTF-8 BOM**: `EF BB BF`
- **问题**: 某些编辑器（如 Windows 记事本）保存 UTF-8 文件时会自动添加 BOM
- **影响**: Python 的 `int()`, `float()` 等函数无法解析带 BOM 的字符串

### 为什么会出现？

1. **本地 `.env` 文件**: 使用 Windows 记事本或某些编辑器编辑，自动添加 BOM
2. **GitHub Secrets**: 从带 BOM 的文件复制粘贴到 GitHub Secrets
3. **自动化脚本**: 使用 `setup-secrets.sh/ps1` 从带 BOM 的 `.env` 上传

---

## 修复方案

### 1. 添加环境变量清理函数

在 `config/config.py` 中添加辅助函数，所有环境变量读取前自动清理 BOM：

```python
def _clean_env_value(value: str | None) -> str:
    """移除 BOM 字符和首尾空格"""
    if value is None:
        return ""
    return value.strip("\ufeff").strip()

def _getenv_int(key: str, default: str) -> int:
    """安全地获取整数类型的环境变量"""
    value = os.getenv(key, default)
    return int(_clean_env_value(value))

def _getenv_float(key: str, default: str) -> float:
    """安全地获取浮点数类型的环境变量"""
    value = os.getenv(key, default)
    return float(_clean_env_value(value))

def _getenv_bool(key: str, default: str) -> bool:
    """安全地获取布尔类型的环境变量"""
    value = os.getenv(key, default)
    return _clean_env_value(value).lower() == "true"

def _getenv_str(key: str, default: str = "") -> str | None:
    """安全地获取字符串类型的环境变量"""
    value = os.getenv(key, default)
    if value is None or value == "":
        return None if default == "" else default
    return _clean_env_value(value)
```

### 2. 替换所有环境变量读取

**修复前**:
```python
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
OPENROUTER_TEMPERATURE = float(os.getenv("OPENROUTER_TEMPERATURE", "0.3"))
ENABLE_TAVILY = os.getenv("ENABLE_TAVILY", "true").lower() == "true"
```

**修复后**:
```python
SMTP_PORT = _getenv_int("SMTP_PORT", "587")
OPENROUTER_TEMPERATURE = _getenv_float("OPENROUTER_TEMPERATURE", "0.3")
ENABLE_TAVILY = _getenv_bool("ENABLE_TAVILY", "true")
```

### 3. 更新的配置项（共 24 处）

**整数类型** (12 处):
- `FLASH_WINDOW_HOURS`
- `CYCLE_WINDOW_DAYS`
- `TREND_WINDOW_DAYS`
- `COMEX_SILVER_*_THRESHOLD` (3个)
- `COMEX_GOLD_*_THRESHOLD` (3个)
- `MAX_RETRIES`
- `REQUEST_TIMEOUT`
- `DEDUPLICATION_WINDOW_HOURS`
- `DIGEST_WINDOW_HOURS`
- `DIGEST_FULL_CONTENT_MAX_CHARS_PER_ARTICLE`
- `OPENROUTER_MAX_TOKENS`
- `OPENROUTER_TIMEOUT`
- `OPENROUTER_MAX_RETRIES`
- `SMTP_PORT` ⚠️ **问题源头**

**浮点数类型** (4 处):
- `VIX_ALERT_THRESHOLD`
- `VIX_SPIKE_PERCENT`
- `DXY_CHANGE_THRESHOLD`
- `US10Y_CHANGE_THRESHOLD`
- `OPENROUTER_TEMPERATURE`

**布尔类型** (8 处):
- `ENABLE_TAVILY`
- `ENABLE_YFINANCE`
- `ENABLE_RSS`
- `ENABLE_FRED`
- `ENABLE_ALPHA_VANTAGE`
- `ENABLE_ETF`
- `ENABLE_COMEX`
- `DIGEST_INCLUDE_FULL_CONTENT`
- `SMTP_USE_TLS`

---

## 验证

### 本地测试

```bash
# 测试配置导入
python -c "from config.config import Config; print('✅ 导入成功'); print(f'SMTP_PORT = {Config.SMTP_PORT}')"

# 预期输出:
# ✅ 导入成功
# SMTP_PORT = 587
```

### GitHub Actions 测试

workflow 中新增配置验证步骤会在运行主程序前检查所有环境变量。

---

## 预防措施

### 1. 检查 `.env` 文件是否包含 BOM

**Linux / Mac**:
```bash
# 检查 BOM
file .env

# 如果显示 "UTF-8 Unicode (with BOM) text"，移除 BOM:
sed -i '1s/^\xEF\xBB\xBF//' .env
```

**Windows (PowerShell)**:
```powershell
# 检查并移除 BOM
$content = Get-Content .env -Raw -Encoding UTF8
$content = $content -replace '^\xEF\xBB\xBF', ''
[System.IO.File]::WriteAllText('.\.env', $content, [System.Text.UTF8Encoding]::new($false))
```

### 2. 推荐的编辑器设置

**VS Code** (推荐):
- 默认使用 UTF-8 without BOM ✅
- 设置: `"files.encoding": "utf8"`

**Notepad++**:
- Encoding → Convert to UTF-8 without BOM

**避免使用**:
- Windows 记事本（会自动添加 BOM）❌

### 3. GitHub Secrets 配置

使用自动化脚本上传时，确保先移除 BOM：

```bash
# setup-secrets.sh 已更新（未来可考虑添加 BOM 检测）
bash .github/setup-secrets.sh
```

---

## 相关问题

### 为什么本地运行正常，GitHub Actions 失败？

- **本地**: 可能使用了无 BOM 的编辑器（VS Code, vim 等）
- **GitHub Actions**: 从带 BOM 的 `.env` 上传的 Secrets

### 其他可能受影响的项目

任何使用以下模式的 Python 项目都可能受影响：

```python
PORT = int(os.getenv("PORT"))
TIMEOUT = float(os.getenv("TIMEOUT"))
```

**解决方案**: 在类型转换前清理字符串：

```python
PORT = int(os.getenv("PORT", "8080").strip("\ufeff").strip())
```

或使用本项目的辅助函数模式。

---

## 修复文件清单

| 文件 | 修改内容 |
|------|---------|
| `config/config.py` | 添加 4 个辅助函数，替换 24 处环境变量读取 |
| `.github/workflows/finnews-schedule.yml` | 新增配置验证步骤 |
| `.github/TROUBLESHOOTING.md` | 新增故障排查文档 |
| `.github/check-secrets.sh` | 新增 Secrets 检查脚本 |
| `.github/check-secrets.ps1` | 新增 Secrets 检查脚本 (Windows) |

---

## 测试结果

✅ **本地测试通过**:
```
✅ Config 导入成功
SMTP_PORT = 587 (类型: int)
```

⏳ **GitHub Actions**: 待下次运行验证

---

## 总结

**问题**: BOM 字符导致类型转换失败  
**修复**: 统一使用清理函数处理所有环境变量  
**影响**: 所有环境变量读取现在都能容忍 BOM 和空格  
**预防**: 使用正确的编辑器，定期检查 `.env` 文件编码  

---

**最后更新**: 2026-01-21  
**修复人**: Sisyphus (OhMyOpenCode)
