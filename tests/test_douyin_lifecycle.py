# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from media_platform.douyin.lifecycle import (
    SLOT_AFTERNOON,
    SLOT_EVENING,
    SLOT_MANUAL,
    SLOT_MORNING,
    filter_aweme_rows_for_slot,
    resolve_scheduled_slot,
    should_refresh_aweme_for_slot,
    should_write_creator_stats,
    slot_from_hhmm,
)

SHANGHAI = ZoneInfo("Asia/Shanghai")


def _ts_days_ago(days: float, now: datetime) -> int:
    return int((now - timedelta(days=days)).timestamp())


def test_resolve_scheduled_slot_and_creator_stats_gate():
    assert resolve_scheduled_slot("morning") == SLOT_MORNING
    assert resolve_scheduled_slot("EVENING") == SLOT_EVENING
    assert resolve_scheduled_slot("unknown") == SLOT_MANUAL
    assert should_write_creator_stats(SLOT_MORNING) is True
    assert should_write_creator_stats(SLOT_AFTERNOON) is False
    assert should_write_creator_stats(SLOT_MANUAL) is True
    assert slot_from_hhmm(9, 0) == SLOT_MORNING
    assert slot_from_hhmm(14, 0) == SLOT_AFTERNOON
    assert slot_from_hhmm(22, 30) == SLOT_EVENING


def test_lifecycle_hot_mid_old_selection():
    now = datetime(2026, 11, 12, 22, 30, tzinfo=SHANGHAI)
    hot = _ts_days_ago(2, now)
    mid = _ts_days_ago(15, now)
    old = _ts_days_ago(60, now)

    assert should_refresh_aweme_for_slot(create_time=hot, slot=SLOT_MORNING, now=now)
    assert should_refresh_aweme_for_slot(create_time=hot, slot=SLOT_AFTERNOON, now=now)
    assert should_refresh_aweme_for_slot(create_time=hot, slot=SLOT_EVENING, now=now)

    assert not should_refresh_aweme_for_slot(create_time=mid, slot=SLOT_MORNING, now=now)
    assert not should_refresh_aweme_for_slot(create_time=mid, slot=SLOT_AFTERNOON, now=now)
    assert should_refresh_aweme_for_slot(create_time=mid, slot=SLOT_EVENING, now=now)

    recent_old_stats = (now - timedelta(days=2)).isoformat()
    assert not should_refresh_aweme_for_slot(
        create_time=old,
        slot=SLOT_EVENING,
        last_collected_at=recent_old_stats,
        now=now,
    )
    stale_old_stats = (now - timedelta(days=8)).isoformat()
    assert should_refresh_aweme_for_slot(
        create_time=old,
        slot=SLOT_EVENING,
        last_collected_at=stale_old_stats,
        now=now,
    )

    selected = filter_aweme_rows_for_slot(
        [
            {"aweme_id": "hot1", "create_time": hot},
            {"aweme_id": "mid1", "create_time": mid},
            {"aweme_id": "old1", "create_time": old, "last_collected_at": recent_old_stats},
            {"aweme_id": "old2", "create_time": old, "last_collected_at": stale_old_stats},
        ],
        SLOT_EVENING,
        now=now,
    )
    assert selected == ["hot1", "mid1", "old2"]
