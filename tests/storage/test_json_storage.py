"""
测试 JSONStorage 存储模块
"""

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from storage.json_storage import JSONStorage
from utils.logger import setup_logger
from datetime import datetime
import json
from pathlib import Path


def test_json_storage():
    """测试 JSONStorage 保存功能"""
    # 初始化
    setup_logger()
    storage = JSONStorage()

    print("=" * 80)
    print("正在测试 JSONStorage...")
    print("=" * 80)

    # 测试数据
    test_data = [
        {
            "type": "economic_data",
            "indicator": "CPI",
            "value": 3.2,
            "change_pct": 0.5,
            "timestamp": datetime(2026, 1, 20, 10, 0, 0),
            "source": "FRED",
        },
        {
            "type": "price_data",
            "ticker": "GC=F",
            "ticker_name": "Gold Futures",
            "price": 2050.12,
            "change": 15.30,
            "change_percent": 0.75,
            "week_change_percent": 2.5,
            "open": 2035.00,
            "high": 2055.00,
            "low": 2030.00,
            "volume": 150000,
            "ma5": 2040.50,
            "timestamp": datetime(2026, 1, 20, 15, 0, 0),
            "source": "YFinance",
        },
        {
            "type": "price_data",
            "ticker": "SI=F",
            "ticker_name": "Silver Futures",
            "price": 24.50,
            "change": -0.25,
            "change_percent": -1.0,
            "timestamp": datetime(2026, 1, 20, 15, 0, 0),
            "source": "YFinance",
        },
        {
            "type": "fx_data",
            "pair": "USD/EUR",
            "close": 0.92,
            "timestamp": datetime(2026, 1, 20, 14, 0, 0),
            "source": "AlphaVantage",
        },
        {
            "type": "news",
            "title": "Gold prices surge on inflation concerns",
            "summary": "Gold futures rose sharply as inflation data exceeded expectations...",
            "full_content": "Gold futures rose sharply as inflation data exceeded expectations. The Consumer Price Index showed an increase of 3.2%, higher than the forecasted 3.0%. This has led investors to seek safe-haven assets.",
            "url": "https://example.com/news/1",
            "timestamp": datetime(2026, 1, 20, 12, 30, 0),
            "source": "Reuters",
            "impact_tag": "#Bullish",
        },
        {
            "type": "news",
            "title": "Silver demand increases in industrial sector",
            "summary": "Industrial demand for silver continues to grow, particularly in electronics and solar panels...",
            "url": "https://example.com/news/2",
            "timestamp": datetime(2026, 1, 20, 11, 0, 0),
            "source": "Kitco",
            "impact_tag": "#Bullish",
        },
        {
            "type": "news",
            "title": "Fed signals potential rate hold",
            "summary": "Federal Reserve officials suggest interest rates may remain steady in coming months...",
            "url": "https://example.com/news/3",
            "timestamp": datetime(2026, 1, 20, 10, 30, 0),
            "source": "Bloomberg",
            "impact_tag": "#Neutral",
        },
    ]

    print(f"\n测试数据: {len(test_data)} 条记录\n")

    # 测试保存原始数据
    print("=" * 80)
    print("测试 save_raw()...")
    print("=" * 80)

    raw_filename = f"test_raw_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    storage.save_raw(test_data, filename=raw_filename)

    raw_filepath = storage.raw_dir / raw_filename
    assert raw_filepath.exists(), "原始数据文件应该存在"

    # 验证JSON格式正确
    with open(raw_filepath, "r", encoding="utf-8") as f:
        loaded_data = json.load(f)
    assert len(loaded_data) == len(test_data), "加载的数据条数应该匹配"

    print(f"✅ 原始数据保存成功: {raw_filepath}")

    # 测试保存处理后数据（Markdown）
    print("\n" + "=" * 80)
    print("测试 save_processed()...")
    print("=" * 80)

    processed_filename = f"test_processed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    storage.save_processed(test_data, filename=processed_filename)

    processed_filepath = storage.processed_dir / processed_filename
    assert processed_filepath.exists(), "处理后数据文件应该存在"

    # 读取Markdown内容
    with open(processed_filepath, "r", encoding="utf-8") as f:
        markdown_content = f.read()

    print(f"✅ 处理数据保存成功: {processed_filepath}")
    print(f"\nMarkdown内容长度: {len(markdown_content)} 字符\n")

    # 验证Markdown格式
    print("=" * 80)
    print("验证Markdown格式...")
    print("=" * 80)

    # 应该包含各个section
    assert "宏观经济指标" in markdown_content, "应该包含经济指标section"
    assert "最新市场价格" in markdown_content, "应该包含价格section"
    assert "外汇数据" in markdown_content, "应该包含外汇section"
    assert "相关新闻" in markdown_content, "应该包含新闻section"
    assert "数据统计" in markdown_content, "应该包含统计section"

    # 验证数据内容
    assert "CPI" in markdown_content, "应该包含CPI数据"
    assert "Gold Futures" in markdown_content, "应该包含黄金价格"
    assert "Silver Futures" in markdown_content, "应该包含白银价格"
    assert "USD/EUR" in markdown_content, "应该包含外汇数据"
    assert "inflation concerns" in markdown_content, "应该包含新闻标题"
    assert "#Bullish" in markdown_content, "应该包含影响标签"

    # 验证技术指标
    assert "5日均线" in markdown_content, "应该包含移动平均线"
    assert "📈" in markdown_content or "📉" in markdown_content, "应该包含涨跌emoji"

    print("✅ Markdown格式验证通过！")

    # 显示Markdown预览
    print("\n" + "=" * 80)
    print("Markdown内容预览（前800字符）:")
    print("=" * 80)
    print(markdown_content[:800])
    print("..." if len(markdown_content) > 800 else "")

    # 保存测试结果摘要
    output_file = str(Path(__file__).resolve().parent / "test_results.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "test_time": datetime.now().isoformat(),
                "input_records": len(test_data),
                "raw_file": str(raw_filepath),
                "processed_file": str(processed_filepath),
                "markdown_length": len(markdown_content),
                "validations": {
                    "raw_file_exists": raw_filepath.exists(),
                    "processed_file_exists": processed_filepath.exists(),
                    "markdown_has_sections": all(
                        [
                            "宏观经济指标" in markdown_content,
                            "最新市场价格" in markdown_content,
                            "外汇数据" in markdown_content,
                            "相关新闻" in markdown_content,
                        ]
                    ),
                },
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(f"\n💾 测试结果已保存到: {output_file}")
    print("\n✅ 所有测试通过！")


def test_markdown_conversion():
    """测试 _to_markdown 转换功能"""
    print("\n" + "=" * 80)
    print("测试Markdown转换逻辑...")
    print("=" * 80)

    storage = JSONStorage()

    # 测试空数据
    empty_md = storage._to_markdown([])
    assert "总计**: 0 条" in empty_md, "空数据应该显示0条记录"
    print("✅ 空数据测试通过")

    # 测试只有新闻数据
    news_only = [
        {
            "type": "news",
            "title": "Test News",
            "summary": "Test summary",
            "timestamp": datetime.now(),
            "source": "TestSource",
            "impact_tag": "#Neutral",
        }
    ]
    news_md = storage._to_markdown(news_only)
    assert "相关新闻" in news_md, "应该包含新闻section"
    assert "TestSource" in news_md, "应该包含来源"
    print("✅ 新闻数据测试通过")

    # 测试只有价格数据
    price_only = [
        {
            "type": "price_data",
            "ticker": "GC=F",
            "ticker_name": "Gold",
            "price": 2000.0,
            "timestamp": datetime.now(),
        }
    ]
    price_md = storage._to_markdown(price_only)
    assert "最新市场价格" in price_md, "应该包含价格section"
    assert "Gold" in price_md, "应该包含商品名称"
    print("✅ 价格数据测试通过")

    print("=" * 80)


if __name__ == "__main__":
    test_json_storage()
    test_markdown_conversion()
