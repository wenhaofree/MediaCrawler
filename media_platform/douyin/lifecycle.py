# -*- coding: utf-8 -*-
"""Douyin aweme lifecycle helpers for layered stats crawl frequency."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable, Optional
from zoneinfo import ZoneInfo

import config

SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")

SLOT_MORNING = "morning"
SLOT_AFTERNOON = "afternoon"
SLOT_EVENING = "evening"
SLOT_MANUAL = "manual"
SLOT_AUTO = "auto"

VALID_SLOTS = {SLOT_MORNING, SLOT_AFTERNOON, SLOT_EVENING, SLOT_MANUAL, SLOT_AUTO}


def now_shanghai(now: Optional[datetime] = None) -> datetime:
    if now is None:
        return datetime.now(SHANGHAI_TZ)
    if now.tzinfo is None:
        return now.replace(tzinfo=SHANGHAI_TZ)
    return now.astimezone(SHANGHAI_TZ)


def collected_at_iso(now: Optional[datetime] = None) -> str:
    return now_shanghai(now).isoformat(timespec="seconds")


def parse_count(value) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip().replace(",", "")
    if not text or text.lower() in {"none", "null"}:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def normalize_create_ts(create_time) -> Optional[int]:
    """Normalize Douyin create_time to unix seconds."""
    if create_time is None:
        return None
    try:
        ts = int(create_time)
    except (TypeError, ValueError):
        return None
    if ts > 10_000_000_000:  # milliseconds
        ts //= 1000
    return ts


def aweme_age_days(create_time, now: Optional[datetime] = None) -> Optional[float]:
    ts = normalize_create_ts(create_time)
    if ts is None:
        return None
    current = now_shanghai(now)
    created = datetime.fromtimestamp(ts, tz=SHANGHAI_TZ)
    return max((current - created).total_seconds() / 86400.0, 0.0)


def infer_slot_from_clock(now: Optional[datetime] = None) -> str:
    current = now_shanghai(now)
    minutes = current.hour * 60 + current.minute
    morning = 9 * 60
    afternoon = 14 * 60
    evening = 22 * 60 + 30
    # Nearest canonical slot
    distances = {
        SLOT_MORNING: min(abs(minutes - morning), 24 * 60 - abs(minutes - morning)),
        SLOT_AFTERNOON: min(abs(minutes - afternoon), 24 * 60 - abs(minutes - afternoon)),
        SLOT_EVENING: min(abs(minutes - evening), 24 * 60 - abs(minutes - evening)),
    }
    return min(distances, key=distances.get)


def resolve_scheduled_slot(explicit: Optional[str] = None, now: Optional[datetime] = None) -> str:
    value = (explicit if explicit is not None else getattr(config, "DY_SCHEDULED_SLOT", SLOT_MANUAL) or SLOT_MANUAL)
    value = str(value).strip().lower() or SLOT_MANUAL
    if value == SLOT_AUTO:
        return infer_slot_from_clock(now)
    if value not in VALID_SLOTS:
        return SLOT_MANUAL
    return value


def slot_from_hhmm(hour: int, minute: int) -> str:
    if (hour, minute) == (9, 0):
        return SLOT_MORNING
    if (hour, minute) == (14, 0):
        return SLOT_AFTERNOON
    if (hour, minute) == (22, 30):
        return SLOT_EVENING
    return infer_slot_from_clock(datetime(2000, 1, 1, hour, minute, tzinfo=SHANGHAI_TZ))


def should_write_creator_stats(slot: str) -> bool:
    return slot in {SLOT_MORNING, SLOT_MANUAL}


def should_refresh_aweme_for_slot(
    *,
    create_time,
    slot: str,
    last_collected_at: Optional[str] = None,
    now: Optional[datetime] = None,
) -> bool:
    """Return whether an aweme should receive a detail/stats refresh in this slot."""
    if slot == SLOT_MANUAL:
        return True

    age = aweme_age_days(create_time, now=now)
    if age is None:
        # Unknown age: only refresh in evening to limit cost
        return slot == SLOT_EVENING

    hot_days = int(getattr(config, "DY_STATS_HOT_DAYS", 7))
    mid_days = int(getattr(config, "DY_STATS_MID_DAYS", 30))
    old_refresh_days = int(getattr(config, "DY_STATS_OLD_REFRESH_DAYS", 7))

    if age <= hot_days:
        return slot in {SLOT_MORNING, SLOT_AFTERNOON, SLOT_EVENING}

    if age <= mid_days:
        return slot == SLOT_EVENING

    # 30+ days: evening only, and at most once per old_refresh_days
    if slot != SLOT_EVENING:
        return False
    if not last_collected_at:
        return True
    try:
        last_dt = datetime.fromisoformat(last_collected_at)
        if last_dt.tzinfo is None:
            last_dt = last_dt.replace(tzinfo=SHANGHAI_TZ)
        else:
            last_dt = last_dt.astimezone(SHANGHAI_TZ)
    except ValueError:
        return True
    return now_shanghai(now) - last_dt >= timedelta(days=old_refresh_days)


def filter_aweme_rows_for_slot(
    rows: Iterable[dict],
    slot: str,
    now: Optional[datetime] = None,
) -> list[str]:
    """
    rows: dicts with keys aweme_id, create_time, last_collected_at (optional)
    """
    selected: list[str] = []
    for row in rows:
        aweme_id = row.get("aweme_id")
        if not aweme_id:
            continue
        if should_refresh_aweme_for_slot(
            create_time=row.get("create_time"),
            slot=slot,
            last_collected_at=row.get("last_collected_at"),
            now=now,
        ):
            selected.append(str(aweme_id))
    return selected
