"""
COMEX库存快照查询工具
为AI模型提供便捷的库存状态查询接口

使用方式:
    from utils.comex_query import get_comex_snapshot

    # 查询白银库存
    snapshot = get_comex_snapshot("silver")
    print(snapshot["alert_message"])

    # 查询黄金库存
    gold_snapshot = get_comex_snapshot("gold")
"""

import logging
from datetime import datetime
from typing import Any, Dict, Literal, Optional

from config.config import Config

logger = logging.getLogger("utils.comex_query")


def get_comex_snapshot(
    metal: Literal["silver", "gold"] = "silver",
    force_refresh: bool = False,
) -> Dict[str, Any]:
    """
    获取COMEX库存快照 (带三级预警)

    此函数为AI模型频繁查询设计，返回完整的库存状态和投资建议。

    Args:
        metal: 金属类型 ("silver" 或 "gold")
        force_refresh: 是否强制刷新数据 (默认使用缓存)

    Returns:
        {
            "metal": "silver",
            "success": True,
            "report_date": "2026-01-21",

            # 库存数据 (原始盎司)
            "registered": 28500000,
            "eligible": 250000000,
            "total": 278500000,

            # 库存数据 (百万盎司，便于阅读)
            "registered_million": 28.5,
            "eligible_million": 250.0,
            "total_million": 278.5,

            # 三级预警
            "alert_level": "red",         # "safe", "yellow", "red", "system_failure"
            "alert_emoji": "🔴",
            "alert_message": "🔴 库存 28.5M oz 跌破生死线(30M)！脱钩风险急剧上升",

            # 投资建议
            "recommendation": "清仓 SLV，换成 PSLV 或实物白银",
            "slv_status": "高风险",

            # 周变化
            "weekly_change": -3300000,
            "weekly_change_percent": -10.4,
            "weekly_change_message": "本周流出 3.3M oz (-10.4%)",

            # 阈值参考
            "thresholds": {
                "yellow": 40000000,
                "red": 30000000,
                "system_failure": 20000000
            },

            # 元数据
            "fetched_at": "2026-01-21T10:05:00",
            "data_source": "CME Group Daily Report"
        }

    Example:
        >>> snapshot = get_comex_snapshot("silver")
        >>> if snapshot["alert_level"] == "red":
        ...     print(f"警告: {snapshot['alert_message']}")
        ...     print(f"建议: {snapshot['recommendation']}")
    """
    # 导入放在函数内部避免循环依赖
    from scrapers.comex_scraper import ComexScraper

    result = {
        "metal": metal,
        "success": False,
        "error": None,
        "report_date": None,
        "fetched_at": datetime.now().isoformat(),
        "data_source": "CME Group Daily Report",
    }

    try:
        # 获取最新数据
        scraper = ComexScraper()
        data = scraper.fetch_metal(metal)

        if data is None:
            result["error"] = f"无法获取{metal}库存数据"
            return result

        result["success"] = True
        result["report_date"] = (
            data["report_date"].strftime("%Y-%m-%d")
            if data.get("report_date")
            else None
        )

        # 复制原始数据
        for key in [
            "registered",
            "eligible",
            "total",
            "registered_million",
            "eligible_million",
            "total_million",
            "registered_change",
            "eligible_change",
            "total_change",
            "registered_weekly_change",
            "registered_weekly_change_pct",
        ]:
            result[key] = data.get(key)

        # 获取阈值配置
        thresholds = _get_thresholds(metal)
        result["thresholds"] = thresholds

        # 计算预警级别 (基于 Registered 库存)
        registered = data.get("registered")
        if registered is not None:
            alert_info = _calculate_alert_level(registered, thresholds, metal)
            result.update(alert_info)

        # 计算周变化消息
        weekly_change = data.get("registered_weekly_change")
        weekly_pct = data.get("registered_weekly_change_pct")
        if weekly_change is not None:
            result["weekly_change"] = weekly_change
            result["weekly_change_percent"] = weekly_pct
            change_million = round(weekly_change / 1_000_000, 2)
            direction = "流出" if weekly_change < 0 else "流入"
            result["weekly_change_message"] = (
                f"本周{direction} {abs(change_million)}M oz ({weekly_pct:+.1f}%)"
            )

    except ImportError as e:
        result["error"] = f"依赖缺失: {e}"
        logger.error(f"COMEX查询失败: {e}")
    except Exception as e:
        result["error"] = f"查询失败: {e}"
        logger.error(f"COMEX查询失败: {e}", exc_info=True)

    return result


def _get_thresholds(metal: str) -> Dict[str, int]:
    """
    获取预警阈值配置

    Args:
        metal: 金属类型

    Returns:
        阈值字典
    """
    if metal == "silver":
        return {
            "yellow": getattr(Config, "COMEX_SILVER_YELLOW_THRESHOLD", 40_000_000),
            "red": getattr(Config, "COMEX_SILVER_RED_THRESHOLD", 30_000_000),
            "system_failure": getattr(
                Config, "COMEX_SILVER_FAILURE_THRESHOLD", 20_000_000
            ),
        }
    elif metal == "gold":
        # 黄金阈值 (可根据需要调整)
        return {
            "yellow": getattr(Config, "COMEX_GOLD_YELLOW_THRESHOLD", 10_000_000),
            "red": getattr(Config, "COMEX_GOLD_RED_THRESHOLD", 5_000_000),
            "system_failure": getattr(
                Config, "COMEX_GOLD_FAILURE_THRESHOLD", 2_000_000
            ),
        }
    else:
        return {"yellow": 0, "red": 0, "system_failure": 0}


def _calculate_alert_level(
    registered: float, thresholds: Dict[str, int], metal: str
) -> Dict[str, Any]:
    """
    计算预警级别和投资建议

    Args:
        registered: Registered库存量 (盎司)
        thresholds: 阈值配置
        metal: 金属类型

    Returns:
        包含预警信息的字典
    """
    registered_m = round(registered / 1_000_000, 2)
    yellow = thresholds["yellow"]
    red = thresholds["red"]
    failure = thresholds["system_failure"]

    yellow_m = round(yellow / 1_000_000, 1)
    red_m = round(red / 1_000_000, 1)
    failure_m = round(failure / 1_000_000, 1)

    metal_cn = "白银" if metal == "silver" else "黄金"
    etf_paper = "SLV" if metal == "silver" else "GLD"
    etf_physical = "PSLV" if metal == "silver" else "PHYS"

    if registered < failure:
        return {
            "alert_level": "system_failure",
            "alert_emoji": "⚫",
            "alert_message": (
                f"⚫ {metal_cn}库存 {registered_m}M oz 跌破熔断线({failure_m}M)！"
                f"纸{metal_cn}面临系统性脱钩风险"
            ),
            "recommendation": f"紧急撤离所有纸{metal_cn}资产，只持有实物",
            "slv_status": "极端危险",
            "is_emergency": True,
        }
    elif registered < red:
        return {
            "alert_level": "red",
            "alert_emoji": "🔴",
            "alert_message": (
                f"🔴 {metal_cn}库存 {registered_m}M oz 跌破生死线({red_m}M)！"
                f"脱钩风险急剧上升"
            ),
            "recommendation": f"清仓 {etf_paper}，换成 {etf_physical} 或实物{metal_cn}",
            "slv_status": "高风险",
            "is_emergency": False,
        }
    elif registered < yellow:
        return {
            "alert_level": "yellow",
            "alert_emoji": "🟡",
            "alert_message": (
                f"🟡 {metal_cn}库存 {registered_m}M oz 跌破警戒线({yellow_m}M)，"
                f"市场趋紧"
            ),
            "recommendation": f"{etf_paper} 暂时安全，关注溢价变化，考虑部分换仓 {etf_physical}",
            "slv_status": "需关注",
            "is_emergency": False,
        }
    else:
        return {
            "alert_level": "safe",
            "alert_emoji": "🟢",
            "alert_message": f"🟢 {metal_cn}库存 {registered_m}M oz 处于安全水平",
            "recommendation": f"{etf_paper} 正常持有，无需担忧",
            "slv_status": "正常",
            "is_emergency": False,
        }


def get_comex_summary() -> str:
    """
    获取COMEX库存摘要文本 (适合直接输出给用户或AI)

    Returns:
        格式化的摘要字符串
    """
    silver = get_comex_snapshot("silver")
    gold = get_comex_snapshot("gold")

    lines = [
        "=" * 50,
        "COMEX 库存监控快照",
        f"更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "=" * 50,
        "",
    ]

    for name, data in [("白银", silver), ("黄金", gold)]:
        if data.get("success"):
            lines.extend(
                [
                    f"【{name}】 {data.get('alert_emoji', '')}",
                    f"  Registered: {data.get('registered_million', 'N/A')}M oz",
                    f"  状态: {data.get('alert_message', 'N/A')}",
                    f"  建议: {data.get('recommendation', 'N/A')}",
                ]
            )
            if data.get("weekly_change_message"):
                lines.append(f"  周变化: {data['weekly_change_message']}")
            lines.append("")
        else:
            lines.extend(
                [
                    f"【{name}】 ❓",
                    f"  错误: {data.get('error', '未知错误')}",
                    "",
                ]
            )

    lines.append("=" * 50)
    return "\n".join(lines)


# 便捷别名
get_silver_snapshot = lambda: get_comex_snapshot("silver")
get_gold_snapshot = lambda: get_comex_snapshot("gold")


if __name__ == "__main__":
    # 测试运行
    print(get_comex_summary())
