"""Rolling 24h digest controller.

Maintains an in-memory rolling window of records and builds an LLM prompt.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Tuple


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime objects."""

    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)


def _parse_timestamp(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except Exception:
            return None
    return None


def _stable_record_id(record: Dict[str, Any]) -> str:
    record_type = str(record.get("type", ""))

    if record_type in {"price_data", "economic_data", "fx_data"}:
        parts = [
            record_type,
            str(
                record.get("ticker")
                or record.get("pair")
                or record.get("indicator")
                or ""
            ),
            str(record.get("timestamp") or record.get("date") or ""),
            str(
                record.get("value") or record.get("price") or record.get("close") or ""
            ),
        ]
        key = "|".join(parts)
        return hashlib.md5(key.encode("utf-8")).hexdigest()

    # News-like records
    title = str(record.get("title", ""))
    summary = str(record.get("summary", ""))
    url = str(record.get("url", ""))
    key = f"{title}|{summary}|{url}"
    return hashlib.md5(key.encode("utf-8")).hexdigest()


@dataclass
class DigestStats:
    window_hours: int
    window_start: datetime
    window_end: datetime
    total_records: int
    counts_by_type: Dict[str, int]
    counts_by_source: Dict[str, int]


class DailyDigestController:
    def __init__(self, *, window_hours: int = 24):
        self.window_hours = window_hours
        self._records_by_id: Dict[str, Dict[str, Any]] = {}

    def update(
        self, records: Iterable[Dict[str, Any]], *, now: Optional[datetime] = None
    ) -> DigestStats:
        if now is None:
            now = datetime.now()

        cutoff = now - timedelta(hours=self.window_hours)

        added = 0
        for record in records:
            record_id = _stable_record_id(record)

            ts = _parse_timestamp(record.get("timestamp"))
            if ts is not None and ts < cutoff:
                continue

            if record_id not in self._records_by_id:
                self._records_by_id[record_id] = record
                added += 1

        # prune
        to_delete: List[str] = []
        for record_id, record in self._records_by_id.items():
            ts = _parse_timestamp(record.get("timestamp"))
            if ts is not None and ts < cutoff:
                to_delete.append(record_id)

        for record_id in to_delete:
            del self._records_by_id[record_id]

        stats = self._compute_stats(now=now)
        return stats

    def _compute_stats(self, *, now: Optional[datetime] = None) -> DigestStats:
        if now is None:
            now = datetime.now()

        window_start = now - timedelta(hours=self.window_hours)

        by_type: Counter[str] = Counter()
        by_source: Counter[str] = Counter()

        for record in self._records_by_id.values():
            record_type = str(record.get("type", "unknown"))
            by_type[record_type] += 1

            source = str(
                record.get("source")
                or record.get("provider")
                or record.get("name")
                or "Unknown"
            )
            by_source[source] += 1

        return DigestStats(
            window_hours=self.window_hours,
            window_start=window_start,
            window_end=now,
            total_records=len(self._records_by_id),
            counts_by_type=dict(by_type),
            counts_by_source=dict(by_source),
        )

    def get_window_records(self) -> List[Dict[str, Any]]:
        return list(self._records_by_id.values())

    def build_llm_input(
        self,
        *,
        now: Optional[datetime] = None,
        include_full_content: bool = False,
        max_full_content_chars_per_article: int = 2000,
        max_news_items: int = 200,
    ) -> Tuple[str, DigestStats]:
        if now is None:
            now = datetime.now()

        stats = self._compute_stats(now=now)

        records = self.get_window_records()

        # Group
        econ_items = [r for r in records if r.get("type") == "economic_data"]
        price_items = [r for r in records if r.get("type") == "price_data"]
        fx_items = [r for r in records if r.get("type") == "fx_data"]
        news_items = [
            r
            for r in records
            if r.get("type") not in {"economic_data", "price_data", "fx_data"}
        ]

        def _news_sort_key(item: Dict[str, Any]):
            ts = _parse_timestamp(item.get("timestamp"))
            return ts or datetime.min

        news_items.sort(key=_news_sort_key, reverse=True)
        news_items = news_items[:max_news_items]

        lines: List[str] = []
        lines.append("You are an assistant that writes an HTML email digest.")
        lines.append("Return STRICT JSON only per the schema provided.")
        lines.append("")
        lines.append(f"Digest window: last {stats.window_hours} hours")
        lines.append(
            f"Window start: {stats.window_start.strftime('%Y-%m-%d %H:%M:%S')} | "
            f"Window end: {stats.window_end.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        lines.append(f"Total records in window: {stats.total_records}")
        lines.append(
            f"Counts by type: {json.dumps(stats.counts_by_type, ensure_ascii=False, cls=DateTimeEncoder)}"
        )
        lines.append(
            f"Counts by source: {json.dumps(stats.counts_by_source, ensure_ascii=False, cls=DateTimeEncoder)}"
        )

        lines.append("")
        lines.append("== Macro / Economic Data ==")
        for item in econ_items:
            indicator = item.get("indicator")
            value = item.get("value")
            change_pct = item.get("change_pct")
            ts = item.get("timestamp")
            lines.append(
                f"- indicator={indicator} value={value} change_pct={change_pct} timestamp={ts}"
            )

        lines.append("")
        lines.append("== Prices ==")
        for item in price_items:
            lines.append(
                "- "
                + json.dumps(
                    {
                        "ticker": item.get("ticker"),
                        "ticker_name": item.get("ticker_name"),
                        "price": item.get("price"),
                        "change": item.get("change"),
                        "change_percent": item.get("change_percent"),
                        "week_change_percent": item.get("week_change_percent"),
                        "open": item.get("open"),
                        "high": item.get("high"),
                        "low": item.get("low"),
                        "volume": item.get("volume"),
                        "timestamp": item.get("timestamp"),
                    },
                    ensure_ascii=False,
                    cls=DateTimeEncoder,
                )
            )

        lines.append("")
        lines.append("== FX ==")
        for item in fx_items:
            lines.append(
                "- "
                + json.dumps(
                    {
                        "pair": item.get("pair"),
                        "close": item.get("close"),
                        "timestamp": item.get("timestamp"),
                    },
                    ensure_ascii=False,
                    cls=DateTimeEncoder,
                )
            )

        lines.append("")
        lines.append("== News Items (most recent first) ==")
        for item in news_items:
            payload: Dict[str, Any] = {
                "timestamp": item.get("timestamp"),
                "source": item.get("source"),
                "title": item.get("title"),
                "summary": item.get("summary"),
                "impact_tag": item.get("impact_tag"),
                "url": item.get("url"),
            }

            if include_full_content:
                full_content = item.get("full_content")
                if isinstance(full_content, str) and full_content:
                    payload["full_content"] = full_content[
                        :max_full_content_chars_per_article
                    ]

            lines.append(
                "- " + json.dumps(payload, ensure_ascii=False, cls=DateTimeEncoder)
            )

        user_prompt = "\n".join(lines)
        return user_prompt, stats


DIGEST_JSON_SCHEMA: Dict[str, Any] = {
    "name": "finnews_email_digest",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "subject": {"type": "string"},
            "html_body": {"type": "string"},
            "window_hours": {"type": "integer"},
            "stats": {"type": "object"},
            "highlights": {"type": "object"},
        },
        "required": ["subject", "html_body", "window_hours", "stats"],
    },
}
