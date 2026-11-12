# -*- coding: utf-8 -*-
import asyncio
import os

import pytest

from api.schemas import SaveDataOptionEnum
from api.scheduled_tasks import service as scheduled_service


def test_save_option_supports_postgres():
    assert SaveDataOptionEnum("postgres").value == "postgres"


def test_ensure_default_douyin_schedule_skips_without_creators(monkeypatch, tmp_path):
    db_path = tmp_path / "sched.db"
    monkeypatch.setenv("AUTO_SEED_DY_SCHEDULE", "true")
    monkeypatch.setenv("DY_SCHEDULE_CREATOR_IDS", "")
    monkeypatch.setattr(scheduled_service.db_config, "SQLITE_DB_PATH", str(db_path))

    svc = scheduled_service.ScheduledTaskService()

    async def _empty_db():
        return []

    monkeypatch.setattr(svc, "_load_douyin_creator_ids_from_db", _empty_db)

    async def _run():
        await svc.ensure_tables()
        await svc.ensure_default_douyin_schedule()
        tasks = await svc.list_tasks()
        return tasks

    payload = asyncio.run(_run())
    assert payload["tasks"] == []


def test_ensure_default_douyin_schedule_loads_from_db(monkeypatch, tmp_path):
    db_path = tmp_path / "sched.db"
    monkeypatch.setenv("AUTO_SEED_DY_SCHEDULE", "true")
    monkeypatch.setenv("DY_SCHEDULE_CREATOR_IDS", "")
    monkeypatch.setenv("DY_SCHEDULE_SAVE_OPTION", "postgres")
    monkeypatch.setattr(scheduled_service.db_config, "SQLITE_DB_PATH", str(db_path))

    svc = scheduled_service.ScheduledTaskService()

    async def _from_db():
        return [
            "MS4wLjABAAAAB92s1iYJ6Kr4B6RpP3zenR2DywmkuBBX-RKYLExuNHk",
            "MS4wLjABAAAAqW8dJX9-mXgmeucLFQW9iPwKz8LHOXBnLzscBfG-YBGLIv_lWbdPa3PUfvl9-6Q5",
        ]

    monkeypatch.setattr(svc, "_load_douyin_creator_ids_from_db", _from_db)

    async def _run():
        await svc.ensure_tables()
        await svc.ensure_default_douyin_schedule()
        return await svc.list_tasks()

    payload = asyncio.run(_run())
    assert len(payload["tasks"]) == 1
    assert payload["tasks"][0]["creator_count"] == 2


def test_ensure_default_douyin_schedule_creates_task(monkeypatch, tmp_path):
    db_path = tmp_path / "sched.db"
    monkeypatch.setenv("AUTO_SEED_DY_SCHEDULE", "true")
    monkeypatch.setenv(
        "DY_SCHEDULE_CREATOR_IDS",
        "MS4wLjABAAAAB92s1iYJ6Kr4B6RpP3zenR2DywmkuBBX-RKYLExuNHk",
    )
    monkeypatch.setenv("DY_SCHEDULE_RUN_TIME", "09:00,14:00,22:30")
    monkeypatch.setenv("DY_SCHEDULE_SAVE_OPTION", "postgres")
    monkeypatch.setenv("DY_SCHEDULE_TASK_NAME", "抖音增长快照(自动)")
    monkeypatch.setattr(scheduled_service.db_config, "SQLITE_DB_PATH", str(db_path))

    svc = scheduled_service.ScheduledTaskService()

    async def _run():
        await svc.ensure_tables()
        await svc.ensure_default_douyin_schedule()
        await svc.ensure_default_douyin_schedule()  # idempotent update
        return await svc.list_tasks()

    payload = asyncio.run(_run())
    assert len(payload["tasks"]) == 1
    task = payload["tasks"][0]
    assert task["name"] == "抖音增长快照(自动)"
    assert task["platform"] == "dy"
    assert task["run_time"] == "09:00,14:00,22:30"
    assert task["save_option"] == "postgres"
    assert task["status"] == "active"
    assert task["creator_count"] == 1
