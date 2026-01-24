import json
import logging
from pathlib import Path
from datetime import datetime

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cleaner")

HISTORY_FILE = Path("D:/Projects/FinNews/outputs/comex_history.json")


def clean_history():
    if not HISTORY_FILE.exists():
        logger.error("历史文件不存在")
        return

    try:
        data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        logger.error(f"读取历史文件失败: {e}")
        return

    logger.info("开始清理模拟历史数据...")

    # 我们知道真实的运行日期只有 1月21日 和 1月23日
    # 任何早于 2026-01-21 的数据都是模拟的
    real_start_date = "2026-01-21"

    cleaned_count = 0

    for key in data.keys():
        records = data[key]
        if not records:
            continue

        original_len = len(records)

        # 过滤掉模拟数据 (保留 >= real_start_date 的记录)
        # 注意: 字符串比较 "2026-01-20" < "2026-01-21" 是有效的
        clean_records = [r for r in records if r["date"][:10] >= real_start_date]

        data[key] = clean_records
        cleaned_count += original_len - len(clean_records)

        logger.info(
            f"  Processed {key}: kept {len(clean_records)} records, removed {original_len - len(clean_records)}"
        )

    # 保存回文件
    HISTORY_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    logger.info(f"✅ 清理完成，共移除了 {cleaned_count} 条模拟记录")


if __name__ == "__main__":
    clean_history()
