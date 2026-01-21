"""
时间窗口工具
用于将记录过滤到最近N小时，并在无结果时回退到最新一条。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from config.config import Config


def _parse_timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except Exception:
            return datetime.now()
    return datetime.now()


def apply_time_window(
    records: List[Dict[str, Any]],
    window_hours: Optional[int] = None,
    *,
    allow_fallback: bool = False,
    fallback_note: Optional[str] = None,
    daily_label: Optional[str] = None,
) -> List[Dict[str, Any]]:
    if not records:
        return []

    window = window_hours or Config.FLASH_WINDOW_HOURS
    cutoff_time = datetime.now() - timedelta(hours=window)

    if daily_label:
        for record in records:
            record["daily_label"] = daily_label

    recent = [
        record
        for record in records
        if _parse_timestamp(record.get("timestamp")) >= cutoff_time
    ]
    if recent:
        return recent

    if allow_fallback:
        latest = max(
            records, key=lambda record: _parse_timestamp(record.get("timestamp"))
        )
        latest["fallback_allowed"] = True
        if fallback_note:
            latest["fallback_note"] = fallback_note
        return [latest]

    return []
