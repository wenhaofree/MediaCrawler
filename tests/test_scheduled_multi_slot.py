# -*- coding: utf-8 -*-
from datetime import datetime
from zoneinfo import ZoneInfo

from api.scheduled_tasks.service import (
    _compute_next_run,
    _parse_run_times,
    _slot_from_hhmm,
)


SHANGHAI = ZoneInfo("Asia/Shanghai")


def test_parse_multi_run_times():
    assert _parse_run_times("09:00") == [(9, 0)]
    assert _parse_run_times("09:00,14:00,22:30") == [(9, 0), (14, 0), (22, 30)]
    assert _parse_run_times("09:00, 09:00, 14:00") == [(9, 0), (14, 0)]


def test_compute_next_run_picks_nearest_slot():
    now = datetime(2026, 11, 12, 10, 0, tzinfo=SHANGHAI)
    next_run = _compute_next_run("09:00,14:00,22:30", now=now)
    assert (next_run.hour, next_run.minute) == (14, 0)

    now2 = datetime(2026, 11, 12, 23, 0, tzinfo=SHANGHAI)
    next_run2 = _compute_next_run("09:00,14:00,22:30", now=now2)
    assert next_run2.day == 13
    assert (next_run2.hour, next_run2.minute) == (9, 0)


def test_slot_from_hhmm_mapping():
    assert _slot_from_hhmm(9, 0) == "morning"
    assert _slot_from_hhmm(14, 0) == "afternoon"
    assert _slot_from_hhmm(22, 30) == "evening"
