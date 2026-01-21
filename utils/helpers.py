"""
辅助函数模块
"""

from datetime import datetime
from typing import Any, Dict


def format_timestamp(ts: Any) -> str:
    """
    统一时间戳格式化

    Args:
        ts: datetime对象或时间戳

    Returns:
        格式化的时间字符串
    """
    if isinstance(ts, datetime):
        return ts.strftime("%Y-%m-%d %H:%M:%S")
    elif isinstance(ts, (int, float)):
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    else:
        return str(ts)


def safe_get(data: Dict, *keys, default=None):
    """
    安全获取嵌套字典值

    Args:
        data: 字典对象
        *keys: 嵌套键路径
        default: 默认值

    Returns:
        值或默认值

    Example:
        >>> safe_get({"a": {"b": {"c": 1}}}, "a", "b", "c")
        1
    """
    current = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
            if current is None:
                return default
        else:
            return default
    return current if current is not None else default
