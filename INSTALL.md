# FinNews 安装指南 | Installation Guide

## 中文说明

### 依赖安装可能遇到的问题

由于 `numpy` 和 `pandas` 需要编译 C 扩展，在 Windows 环境下可能需要较长时间。建议按以下步骤安装：

#### 方法 1：使用预编译的二进制包（推荐）

```bash
# 先升级 pip
python -m pip install --upgrade pip

# 分步安装可能需要编译的包
pip install numpy
pip install pandas

# 再安装其他依赖
pip install -r requirements.txt
```

#### 方法 2：使用 Conda（适合有 Anaconda/Miniconda 的用户）

```bash
# 创建虚拟环境
conda create -n finnews python=3.10
conda activate finnews

# 使用 conda 安装科学计算库
conda install numpy pandas

# 再用 pip 安装其他依赖
pip install -r requirements.txt
```

#### 方法 3：手动安装（如果上述方法失败）

```bash
# 安装必需的包（不包括可能失败的）
pip install tavily-python==0.5.0
pip install yfinance==0.2.52
pip install feedparser==6.0.11
pip install fredapi==0.5.2
pip install alpha-vantage==2.3.1
pip install requests==2.32.3
pip install beautifulsoup4==4.12.3
pip install python-dotenv==1.0.1
pip install APScheduler==3.10.4

# 单独安装可能需要编译的包（允许使用兼容版本）
pip install numpy
pip install pandas
pip install lxml
```

### 验证安装

安装完成后，运行以下命令验证：

```bash
python -c "import tavily; import yfinance; import feedparser; import fredapi; import pandas; print('所有依赖安装成功！')"
```

### 下一步

1. **配置 API 密钥**：
   ```bash
   # 复制示例文件
   copy .env.example .env  # Windows
   
   # 编辑 .env 文件，添加你的 API 密钥
   notepad .env
   ```

2. **获取免费 API 密钥**：
   - **Tavily**（必需）: https://tavily.com/
     - 注册后在 Dashboard 中获取 API Key
     - 免费套餐：1000次请求/月
   
   - **FRED**（必需）: https://fred.stlouisfed.org/docs/api/api_key.html
     - 点击 "Request API Key"
     - 免费无限制使用

3. **测试运行**：
   ```bash
   python main.py --mode once
   ```

4. **检查输出**：
   ```bash
   # 查看生成的报告
   dir outputs\processed  # Windows
   ```

---

## English Instructions

### Dependency Installation Issues

Since `numpy` and `pandas` require C extension compilation, installation may take longer on Windows. Follow these steps:

#### Method 1: Use Pre-compiled Binary Packages (Recommended)

```bash
# Upgrade pip first
python -m pip install --upgrade pip

# Install packages that may need compilation step-by-step
pip install numpy
pip install pandas

# Then install other dependencies
pip install -r requirements.txt
```

#### Method 2: Use Conda (For Anaconda/Miniconda Users)

```bash
# Create virtual environment
conda create -n finnews python=3.10
conda activate finnews

# Install scientific computing libraries with conda
conda install numpy pandas

# Then install other dependencies with pip
pip install -r requirements.txt
```

#### Method 3: Manual Installation (If Above Methods Fail)

```bash
# Install required packages (excluding potentially problematic ones)
pip install tavily-python==0.5.0
pip install yfinance==0.2.52
pip install feedparser==6.0.11
pip install fredapi==0.5.2
pip install alpha-vantage==2.3.1
pip install requests==2.32.3
pip install beautifulsoup4==4.12.3
pip install python-dotenv==1.0.1
pip install APScheduler==3.10.4

# Install packages that may need compilation separately (allow compatible versions)
pip install numpy
pip install pandas
pip install lxml
```

### Verify Installation

After installation, verify with:

```bash
python -c "import tavily; import yfinance; import feedparser; import fredapi; import pandas; print('All dependencies installed successfully!')"
```

### Next Steps

1. **Configure API Keys**:
   ```bash
   # Copy example file
   cp .env.example .env  # Linux/Mac
   copy .env.example .env  # Windows
   
   # Edit .env file to add your API keys
   nano .env  # Linux/Mac
   notepad .env  # Windows
   ```

2. **Get Free API Keys**:
   - **Tavily** (Required): https://tavily.com/
     - Get API Key from Dashboard after registration
     - Free tier: 1,000 requests/month
   
   - **FRED** (Required): https://fred.stlouisfed.org/docs/api/api_key.html
     - Click "Request API Key"
     - Free unlimited usage

3. **Test Run**:
   ```bash
   python main.py --mode once
   ```

4. **Check Output**:
   ```bash
   # View generated reports
   ls outputs/processed  # Linux/Mac
   dir outputs\processed  # Windows
   ```

---

## Troubleshooting

### Issue: `error: Microsoft Visual C++ 14.0 or greater is required`

**Windows Users**: Download and install [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)

### Issue: `No module named 'dotenv'`

```bash
pip install python-dotenv
```

### Issue: Installation hangs at "Preparing metadata"

- Press `Ctrl+C` to cancel
- Try installing packages individually
- Use `pip install --no-cache-dir <package-name>` to bypass cache

### Issue: SSL Certificate Error

```bash
pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt
```
