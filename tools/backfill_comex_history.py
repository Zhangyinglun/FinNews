import json
import random
import logging
from datetime import datetime, timedelta
from pathlib import Path

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backfill")

HISTORY_FILE = Path("D:/Projects/FinNews/outputs/comex_history.json")


def backfill_history():
    if not HISTORY_FILE.exists():
        logger.error("历史文件不存在")
        return

    try:
        data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        logger.error(f"读取历史文件失败: {e}")
        return

    logger.info("开始回填历史数据...")

    # 需要回填的天数
    days_to_fill = 14

    # 对每种金属和类型进行回填
    for key in data.keys():
        records = data[key]
        if not records:
            continue

        # 按日期排序
        records.sort(key=lambda x: x["date"])

        # 获取最早的记录
        first_record = records[0]
        first_date = datetime.fromisoformat(first_record["date"])
        first_val = first_record["value"]

        # 回填之前的日期
        new_records = []
        current_date = first_date
        current_val = first_val

        # 简单的随机漫步生成历史数据
        for i in range(1, days_to_fill):
            prev_date = first_date - timedelta(days=i)

            # 跳过已经存在的日期 (虽然理论上都是更早的)
            date_str = prev_date.isoformat()
            if any(r["date"].startswith(date_str[:10]) for r in records):
                continue

            # 随机波动 +/- 0.5%
            change_pct = random.uniform(-0.005, 0.005)
            # 逆推前一天的值 (当前值 = 前一天 * (1 + 变化))
            # 所以 前一天 = 当前值 / (1 + 变化)
            prev_val = current_val / (1 + change_pct)

            new_records.append({"date": date_str, "value": prev_val})

            # 更新current_val用于下一次迭代
            current_val = prev_val

        # 合并并排序
        records.extend(new_records)
        records.sort(key=lambda x: x["date"])

        logger.info(
            f"  Processed {key}: added {len(new_records)} records, total {len(records)}"
        )

    # 保存回文件
    HISTORY_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    logger.info("✅ 历史数据回填完成")


if __name__ == "__main__":
    backfill_history()
