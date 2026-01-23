# FinNews 数据源优化实施计划

**创建时间**: 2026-01-23  
**状态**: 执行中  
**优先级**: 高

---

## 📋 背景

### 问题描述
1. **RSS 源失效**: `kitco_gold` RSS 源返回 404 错误，无法获取数据
2. **数据冗余**: FRED 经济指标存在重复（如 `treasury_10y` 与 YFinance 重复，`dxy` 重复）
3. **低相关性数据**: 部分指标（GDP、M1/M2、oilprice）与黄金白银相关性弱
4. **邮件布局问题**: 经济指标嵌套在市场行情板块内，无数据时显示警告影响美观

### 目标
1. 替换失效 RSS 源，删除低相关性源
2. 精简 FRED 指标从 14 个到 9 个核心指标
3. 优化邮件模板，经济指标独立成板块，无数据时隐藏

---

## 🎯 实施任务

### Task 1: 修改 RSS_FEEDS 配置
**文件**: `config/config.py`  
**行号**: 148-154

**修改内容**:
- ✅ **新增**: `mining_com` (https://www.mining.com/feed/) - 矿业专业新闻，替代 kitco
- ❌ **删除**: `kitco_gold` (404 失效)
- ❌ **删除**: `oilprice` (主要是油气新闻，与黄金白银弱相关)
- ✅ **保留**: `fxstreet_commodities`, `investing_commodities`, `zerohedge`

**新配置**:
```python
RSS_FEEDS = {
    "mining_com": "https://www.mining.com/feed/",
    "fxstreet_commodities": "https://www.fxstreet.com/rss/news/commodities/gold",
    "investing_commodities": "https://www.investing.com/rss/commodities.rss",
    "zerohedge": "http://feeds.feedburner.com/zerohedge/feed",
}
```

---

### Task 2: 精简 FRED_SERIES 配置
**文件**: `config/config.py`  
**行号**: 253-273

**删除指标** (共 5 个):
| 指标 | 代码 | 删除原因 |
|------|------|----------|
| `treasury_10y` | DGS10 | 与 YFinance 的 `^TNX` 重复 |
| `dxy` | DTWEXBGS | 与 YFinance 的 `DX-Y.NYB` 重复 |
| `gdp` | GDP | 季度发布，滞后性强 |
| `m1` | M1SL | 与黄金白银相关性弱 |
| `m2` | M2SL | 与黄金白银相关性弱 |

**保留指标** (共 9 个):
| 类别 | 指标 | 代码 | 说明 |
|------|------|------|------|
| 通胀 | CPI | CPIAUCSL | 消费者价格指数 |
| 通胀 | Core CPI | CPILFESL | 核心 CPI (除食品能源) |
| 通胀 | PCE | PCEPI | 个人消费支出价格指数 |
| 通胀 | Core PCE | PCEPILFE | 核心 PCE (美联储首选指标) |
| 就业 | NFP | PAYEMS | 非农就业人数 |
| 就业 | Unemployment | UNRATE | 失业率 |
| 利率 | Fed Funds | FEDFUNDS | 联邦基金利率 |
| 利率 | Treasury 2Y | DGS2 | 2 年期国债收益率 |
| 利率 | Real Rate | DFII10 | 10 年期实际利率 |

**新配置**:
```python
FRED_SERIES = {
    # 通胀指标
    "cpi": "CPIAUCSL",
    "core_cpi": "CPILFESL",
    "pce": "PCEPI",
    "core_pce": "PCEPILFE",
    # 就业指标
    "nonfarm_payroll": "PAYEMS",
    "unemployment": "UNRATE",
    # 利率与国债
    "fed_funds": "FEDFUNDS",
    "treasury_2y": "DGS2",
    "real_interest_rate": "DFII10",
}
```

---

### Task 3: 邮件模板重构 - 经济指标独立板块
**文件**: `utils/digest_controller.py`

#### 3.1 修改经济指标渲染逻辑 (317-342 行)

**原逻辑**:
- 固定生成 HTML 嵌套在市场行情板块内
- 无数据时显示警告消息

**新逻辑**:
- 生成独立的 `<tr>` 板块 HTML
- 无数据时返回空字符串（隐藏整个板块）

**新代码**:
```python
# 构建经济指标独立板块
econ_items = []
if data.cycle.cpi_actual:
    econ_items.append(f"CPI: {data.cycle.cpi_actual}")
if data.cycle.pce_actual:
    econ_items.append(f"PCE: {data.cycle.pce_actual}")
if data.cycle.nfp_actual:
    econ_items.append(f"NFP: {data.cycle.nfp_actual}")
if data.cycle.fed_rate:
    econ_items.append(f"联邦基金利率: {data.cycle.fed_rate}%")

if econ_items:
    econ_content = " | ".join(econ_items)
    econ_section_html = f'''<tr>
        <td style="padding: 0 16px 20px 16px;">
            <div style="border: 1px solid #e9ecef; border-radius: 8px; overflow: hidden;">
                <div style="background-color: #f8f9fa; padding: 10px 12px; border-bottom: 1px solid #e9ecef;">
                    <span style="font-size: 20px; font-weight: 600; color: #1a1a2e;">📅 经济指标</span>
                </div>
                <div style="padding: 12px; font-size: 16px; color: #333;">
                    {econ_content}
                </div>
            </div>
        </td>
    </tr>'''
else:
    econ_section_html = ""  # 无数据时隐藏整个板块
```

#### 3.2 修改 EMAIL_TEMPLATE (737 行)

**删除**:
```html
{econ_indicators}   <!-- 删除嵌套在市场行情内的占位符 -->
```

**新增** (在 COMEX 板块之前，约 741 行):
```html
<!-- Section 1.5: Economic Indicators (独立板块) -->
{econ_section}

<!-- Section 1.6: COMEX Inventory -->
{comex_section}
```

#### 3.3 修改 format 调用 (379 行)

**原代码**:
```python
econ_indicators=econ_html,
```

**新代码**:
```python
econ_section=econ_section_html,
```

---

### Task 4: 测试验证

**测试步骤**:
1. 运行 `python main.py` 确认无报错
2. 检查生成的邮件 HTML 文件
3. 验证 RSS 源是否正常抓取 (mining_com)
4. 验证 FRED 指标是否正确精简
5. 验证邮件布局：
   - 经济指标是否独立成板块
   - 无数据时是否隐藏

**预期结果**:
- ✅ RSS 源从 5 个减少到 4 个
- ✅ FRED 指标从 14 个减少到 9 个
- ✅ 邮件模板新增独立的经济指标板块
- ✅ 无经济数据时该板块完全隐藏

---

## 📊 影响分析

### 数据源变化
| 类型 | 原数量 | 新数量 | 变化 |
|------|--------|--------|------|
| RSS 源 | 5 | 4 | -1 (删除 kitco, oilprice; 新增 mining_com) |
| FRED 指标 | 14 | 9 | -5 |
| 核心指标 | 8 | 8 | 无变化 (黄金/白银/VIX/美元/国债/CPI/利率/实际利率) |

### 代码变化
| 文件 | 修改行数 | 影响范围 |
|------|----------|----------|
| `config/config.py` | ~30 行 | RSS_FEEDS, FRED_SERIES |
| `utils/digest_controller.py` | ~40 行 | 经济指标渲染逻辑 + 邮件模板 |

---

## ⚠️ 风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| mining_com RSS 格式不兼容 | 新闻抓取失败 | 测试验证，必要时回退 |
| FRED 指标删除影响分析 | 市场分析可能缺失维度 | 保留核心指标，定期评估 |
| 邮件模板渲染异常 | 邮件发送失败或显示错误 | 端到端测试 |

---

## ✅ 完成标准

- [x] RSS_FEEDS 配置修改完成
- [x] FRED_SERIES 配置精简完成
- [x] 邮件模板重构完成
- [x] 测试通过，无报错
- [x] 生成邮件格式正确
- [x] Git 提交完成

---

## 📝 备注

- **相关文档**: `docs/plans/2026-01-23-mobile-email-optimization-design.md`
- **前置工作**: 邮件模板手机端优化已完成
- **后续优化**: 可考虑增加 COMEX 实时库存 API 替代爬虫
