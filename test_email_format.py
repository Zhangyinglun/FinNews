"""
测试邮件格式生成
生成纯文本预览文件供人工查看
"""

import sys

sys.path.insert(0, "D:\\Projects\\FinNews")

import json
import logging
from datetime import datetime
from pathlib import Path

from analyzers.market_analyzer import MarketAnalyzer
from analyzers.rule_engine import RuleEngine
from config.config import Config
from models.analysis import MarketSignal, ComexSignal

# 设置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_latest_data():
    """加载最新的处理数据"""
    # 查找最新的 raw 数据文件
    raw_dir = Config.RAW_DIR
    raw_files = list(raw_dir.glob("raw_*.json"))

    if not raw_files:
        logger.error("未找到任何 raw 数据文件")
        return None

    latest_file = max(raw_files, key=lambda p: p.stat().st_mtime)
    logger.info(f"加载数据文件: {latest_file}")

    with open(latest_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data


def main():
    logger.info("=" * 60)
    logger.info("测试邮件格式生成")
    logger.info("=" * 60)

    # 1. 加载数据
    raw_data = load_latest_data()
    if not raw_data:
        logger.error("无法加载数据，退出")
        return

    logger.info(f"加载了 {len(raw_data)} 条记录")

    # 2. 运行规则引擎
    rule_engine = RuleEngine()
    price_data = [r for r in raw_data if r.get("type") == "price_data"]

    market_signal = rule_engine.analyze(price_data)
    logger.info(
        f"市场信号: VIX={market_signal.vix_value}, "
        f"Gold={market_signal.gold_price}, "
        f"Alert={market_signal.vix_alert_level.value}"
    )

    # 3. 分析 COMEX（如果有数据）
    comex_signal = None
    comex_data = [r for r in raw_data if r.get("type") == "inventory_data"]
    if comex_data:
        comex_signal = rule_engine.analyze_comex(comex_data)
        logger.info(
            f"COMEX信号: 白银={comex_signal.silver_registered_million}M oz, "
            f"黄金={comex_signal.gold_registered_million}M oz"
        )

    # 4. 组织多窗口数据
    market_analyzer = MarketAnalyzer()
    multi_window_data = market_analyzer.organize_data(raw_data, market_signal)

    logger.info(
        f"数据组织完成: Flash={len(multi_window_data.flash.news)}, "
        f"Cycle={len(multi_window_data.cycle.news)}, "
        f"Trend={len(multi_window_data.trend.news)}"
    )

    # 5. 生成邮件格式内容
    logger.info("=" * 60)
    logger.info("生成邮件格式内容...")
    logger.info("=" * 60)

    email_content = market_analyzer.build_email_prompt(
        data=multi_window_data,
        signal=market_signal,
        comex_signal=comex_signal,
        mode="full",  # 完整模式
    )

    # 6. 保存到文件
    output_file = (
        Config.OUTPUT_DIR
        / f"email_preview_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    )
    output_file.write_text(email_content, encoding="utf-8")

    logger.info(f"✅ 邮件预览已保存: {output_file}")
    logger.info(f"📄 文件大小: {len(email_content)} 字符")

    # 显示前 50 行预览
    lines = email_content.split("\n")
    logger.info("=" * 60)
    logger.info("前 50 行预览:")
    logger.info("=" * 60)
    for line in lines[:50]:
        print(line)

    if len(lines) > 50:
        logger.info(f"\n... (还有 {len(lines) - 50} 行)")

    logger.info("=" * 60)
    logger.info(f"✅ 测试完成！请查看文件: {output_file}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
