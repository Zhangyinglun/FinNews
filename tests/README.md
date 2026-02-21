# FinNews 测试文档 | Test Documentation

## 概述 | Overview

FinNews 项目的测试套件，包含单元测试、集成测试和各模块的独立测试。

测试采用独立可执行脚本模式（无需 pytest），每个测试文件都可以单独运行。

## 测试结构 | Test Structure

```
tests/
├── __init__.py
├── scrapers/              # 数据源测试
│   ├── test_tavily.py
│   ├── test_yfinance.py
│   ├── test_rss.py
│   ├── test_fred.py
│   ├── test_alpha_vantage.py
│   └── test_content_fetcher.py
├── processors/            # 数据处理测试
│   ├── test_cleaner.py
│   └── test_deduplicator.py
├── storage/               # 存储测试
│   └── test_json_storage.py
├── utils/                 # 工具类测试
│   ├── test_gmail_smtp.py
│   ├── test_openrouter_digest.py
│   └── test_digest_to_file.py
├── config/                # 配置测试
│   └── test_config.py
└── test_integration.py    # 集成测试

run_tests.py               # 统一测试运行脚本（根目录）
```

## 快速开始 | Quick Start

### 1. 运行所有测试

```bash
python run_tests.py
```

### 2. 运行特定模块测试

```bash
# 数据源测试
python run_tests.py scrapers

# 数据处理测试
python run_tests.py processors

# 存储测试
python run_tests.py storage

# 工具类测试
python run_tests.py utils

# 配置测试
python run_tests.py config

# 集成测试
python run_tests.py integration
```

### 3. 快速测试（跳过慢速测试）

```bash
python run_tests.py --quick
# 或
python run_tests.py quick
```

### 4. 运行单个测试文件

```bash
# 直接运行测试文件
python tests/scrapers/test_tavily.py

# 或使用 -m 选项
python -m tests.scrapers.test_tavily
```

## 测试模块说明 | Test Module Description

### 📡 Scrapers 测试

测试各个数据源的抓取功能。

| 测试文件 | 测试内容 | 需要API密钥 |
|---------|---------|-----------|
| `test_tavily.py` | Tavily API 新闻抓取 | ✅ TAVILY_API_KEY |
| `test_yfinance.py` | 股票/期货价格抓取 | ❌ 无需 |
| `test_rss.py` | RSS 源抓取 | ❌ 无需 |
| `test_fred.py` | FRED 经济数据抓取 | ✅ FRED_API_KEY |
| `test_alpha_vantage.py` | Alpha Vantage 外汇数据 | ✅ ALPHA_VANTAGE_API_KEY |
| `test_content_fetcher.py` | 完整网页内容抓取 | ❌ 无需 |

**运行:**
```bash
python run_tests.py scrapers
```

### 🔧 Processors 测试

测试数据清洗和去重功能。

| 测试文件 | 测试内容 |
|---------|---------|
| `test_cleaner.py` | 关键词过滤、HTML清理、影响标签 |
| `test_deduplicator.py` | MD5去重、时间窗口过滤 |

**运行:**
```bash
python run_tests.py processors
```

**测试内容:**
- ✅ HTML标签清理
- ✅ 白名单/黑名单关键词过滤
- ✅ 影响标签自动标记 (#Bullish/#Bearish/#Neutral)
- ✅ 内容哈希去重
- ✅ 时间窗口过滤
- ✅ 价格/经济数据保留

### 💾 Storage 测试

测试数据存储功能。

| 测试文件 | 测试内容 |
|---------|---------|
| `test_json_storage.py` | JSON保存、Markdown生成 |

**运行:**
```bash
python run_tests.py storage
```

**测试内容:**
- ✅ JSON格式保存
- ✅ Markdown格式转换
- ✅ 多种数据类型分组显示
- ✅ 技术指标格式化
- ✅ 文件存在性验证

### 🛠️ Utils 测试

测试工具类功能。

| 测试文件 | 测试内容 | 需要配置 |
|---------|---------|---------|
| `test_gmail_smtp.py` | Gmail SMTP 邮件发送 | ✅ SMTP配置 |
| `test_openrouter_digest.py` | OpenRouter API 摘要生成 | ✅ OPENROUTER_API_KEY |
| `test_digest_to_file.py` | 摘要生成并保存为HTML | ✅ OPENROUTER_API_KEY |

**运行:**
```bash
python run_tests.py utils
```

**注意:** 这些测试需要配置相应的API密钥和SMTP设置。

### ⚙️ Config 测试

测试配置加载和验证功能。

**运行:**
```bash
python run_tests.py config
```

**测试内容:**
- ✅ 配置值加载
- ✅ 目录存在性
- ✅ API密钥检查
- ✅ RSS源配置
- ✅ 股票代码配置
- ✅ FRED系列配置
- ✅ 关键词过滤配置

### 🔗 Integration 测试

测试完整的数据管道流程。

**运行:**
```bash
python run_tests.py integration
```

**测试流程:**
1. 数据抓取（多个数据源）
2. 数据清洗（关键词过滤）
3. 数据去重（MD5哈希）
4. 数据统计（按类型、来源分组）
5. 数据存储（JSON + Markdown）
6. 最终验证（文件存在、数据质量）

## 测试输出 | Test Output

### 成功输出示例

```
================================================================================
  FinNews 测试套件 | FinNews Test Suite
================================================================================
开始时间: 2026-01-20 22:30:00
范围: 所有测试

--------------------------------------------------------------------------------
  测试模块: scrapers
--------------------------------------------------------------------------------

▶️ 运行: tests/scrapers/test_yfinance.py
----------------------------------------
✅ 抓取完成！共获取 8 条记录
✅ 通过: tests/scrapers/test_yfinance.py

...

================================================================================
  测试总结 | Test Summary
================================================================================

总计: 15 个测试
✅ 通过: 15 个
❌ 失败: 0 个
⏱️ 用时: 45.23 秒

🎉 所有测试通过！
```

### 失败输出示例

```
❌ 失败: tests/scrapers/test_tavily.py (退出码: 1)

失败的测试:
  ❌ tests/scrapers/test_tavily.py

⚠️ 有 1 个测试失败
```

## 环境要求 | Requirements

### 必需依赖

```bash
pip install -r requirements.txt
```

### API 密钥配置

在 `.env` 文件中配置：

```env
# 必需（用于大部分测试）
TAVILY_API_KEY=tvly-xxxxxxxxxx
FRED_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 可选（用于特定测试）
ALPHA_VANTAGE_API_KEY=your_key_here
OPENROUTER_API_KEY=your_key_here

# SMTP 配置（用于邮件测试）
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
EMAIL_FROM=your_email@gmail.com
EMAIL_TO=recipient@example.com
```

## 测试最佳实践 | Best Practices

### 1. 测试前检查

```bash
# 验证配置
python tests/config/test_config.py

# 检查API密钥
python -c "from config.config import Config; Config.validate()"
```

### 2. 渐进式测试

```bash
# 1. 先运行快速测试
python run_tests.py --quick

# 2. 然后运行特定模块
python run_tests.py scrapers

# 3. 最后运行完整测试
python run_tests.py
```

### 3. 调试失败测试

```bash
# 单独运行失败的测试
python tests/scrapers/test_tavily.py

# 查看详细输出
python tests/scrapers/test_tavily.py 2>&1 | tee test_output.log
```

### 4. 测试输出文件

测试会生成输出文件：

```
tests/
├── scrapers/
│   ├── output_tavily.json
│   ├── output_yfinance.json
│   └── ...
├── processors/
│   ├── output_cleaner.json
│   └── output_deduplicator.json
└── storage/
    └── test_results.json
```

这些文件可用于手动检查测试结果。

## 故障排除 | Troubleshooting

### 问题 1: API 密钥错误

**症状:** `Missing TAVILY_API_KEY` 或类似错误

**解决方案:**
1. 检查 `.env` 文件是否存在
2. 确认 API 密钥格式正确
3. 运行 `python tests/config/test_config.py` 验证配置

### 问题 2: 导入错误

**症状:** `ModuleNotFoundError` 或 `ImportError`

**解决方案:**
```bash
# 安装缺失的依赖
pip install -r requirements.txt

# 或安装特定库
pip install requests beautifulsoup4 lxml
```

### 问题 3: 测试超时

**症状:** 测试运行时间过长

**解决方案:**
```bash
# 使用快速测试模式
python run_tests.py --quick

# 或跳过特定慢速测试
# 直接修改 run_tests.py 中的 QUICK_TESTS 配置
```

### 问题 4: 网络相关测试失败

**症状:** `ConnectionError`, `Timeout` 等

**原因:** 网络问题、API服务不可用、防火墙限制

**解决方案:**
- 检查网络连接
- 确认 API 服务状态
- 使用代理（如需要）
- 跳过网络测试运行本地测试

### 问题 5: 输出目录权限错误

**症状:** `PermissionError` 写入文件失败

**解决方案:**
```bash
# 确保输出目录存在且有写入权限
mkdir -p outputs/raw outputs/processed

# Windows
icacls outputs /grant Users:F /T

# Linux/Mac
chmod -R 755 outputs
```

## 持续集成 | CI Integration

### GitHub Actions 示例

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.10'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
    
    - name: Run quick tests
      run: |
        python run_tests.py --quick
      env:
        TAVILY_API_KEY: ${{ secrets.TAVILY_API_KEY }}
        FRED_API_KEY: ${{ secrets.FRED_API_KEY }}
```

## 扩展测试 | Extending Tests

### 添加新测试

1. 在相应目录创建 `test_*.py` 文件
2. 遵循现有测试格式
3. 添加动态路径头部 (参考下方模板)
4. 实现独立可执行的测试函数
5. 更新 `run_tests.py` 中的 `TEST_MODULES` 字典

### 测试模板

```python
"""
测试 [模块名] | Test [Module Name]
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from [module] import [Class]
from utils.logger import setup_logger


def test_[function_name]():
    """测试 [功能描述]"""
    setup_logger()
    
    print("=" * 80)
    print("正在测试 [模块名]...")
    print("=" * 80)
    
    # 测试代码
    # ...
    
    # 断言验证
    assert condition, "错误消息"
    
    print("\n✅ 测试通过！")


if __name__ == "__main__":
    test_[function_name]()
```

## 联系与贡献 | Contact & Contributing

如有问题或建议，请提交 Issue 或 Pull Request。

---

**最后更新:** 2026-01-20
**版本:** 1.0.0
