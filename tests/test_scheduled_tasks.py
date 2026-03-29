# -*- coding: utf-8 -*-
#
# This file is part of MediaCrawler project.

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.schemas import PlatformEnum, SaveDataOptionEnum, ScheduledTaskUpsertRequest
from api.scheduled_tasks.service import ScheduledTaskService
from config import db_config


async def _noop_async(*_args, **_kwargs):
    return None


async def _build_service(tmp_path, monkeypatch) -> ScheduledTaskService:
    db_path = tmp_path / "scheduled_tasks.db"
    monkeypatch.setattr(db_config, "SQLITE_DB_PATH", str(db_path))
    service = ScheduledTaskService()
    await service.ensure_tables()
    return service


def test_schedule_tasks_page_available(monkeypatch):
    monkeypatch.setattr("api.main.scheduled_task_service.start", _noop_async)
    monkeypatch.setattr("api.main.scheduled_task_service.shutdown", _noop_async)

    client = TestClient(app)
    response = client.get("/schedule-tasks")

    assert response.status_code == 200
    assert "每日定时采集配置" in response.text


def test_homepage_contains_quick_links_for_data_pages(monkeypatch):
    monkeypatch.setattr("api.main.scheduled_task_service.start", _noop_async)
    monkeypatch.setattr("api.main.scheduled_task_service.shutdown", _noop_async)

    client = TestClient(app)
    response = client.get("/")

    assert response.status_code == 200
    assert "/sqlite-viewer" in response.text
    assert "/schedule-tasks" in response.text


@pytest.mark.asyncio
async def test_scheduled_task_create_and_list_supports_multiple_creators(tmp_path, monkeypatch):
    service = await _build_service(tmp_path, monkeypatch)
    payload = ScheduledTaskUpsertRequest(
        name="小红书作者日采",
        platform=PlatformEnum.XHS,
        run_time="09:00",
        max_pages=3,
        enable_comments=False,
        enable_sub_comments=False,
        save_option=SaveDataOptionEnum.SQLITE,
        status="paused",
        creators=[
            "https://www.xiaohongshu.com/user/profile/640c29eb000000001001c91b?xsec_token=tokenA&xsec_source=pc_search",
            "https://www.xiaohongshu.com/user/profile/5eb8e1d400000000010075ae?xsec_token=tokenB&xsec_source=pc_search",
            "640c29eb000000001001c91b",
        ],
    )

    task = await service.create_task(payload)
    tasks_payload = await service.list_tasks()

    assert task["platform"] == "xhs"
    assert task["status"] == "paused"
    assert [item["normalized_creator_id"] for item in task["creators"]] == [
        "640c29eb000000001001c91b",
        "5eb8e1d400000000010075ae",
    ]
    assert tasks_payload["tasks"][0]["creator_count"] == 2
    assert tasks_payload["tasks"][0]["creators"][0]["raw_input"].startswith("https://www.xiaohongshu.com")

    await service.shutdown()


@pytest.mark.asyncio
async def test_scheduled_task_rejects_foreign_platform_creator_url(tmp_path, monkeypatch):
    service = await _build_service(tmp_path, monkeypatch)
    payload = ScheduledTaskUpsertRequest(
        name="抖音作者日采",
        platform=PlatformEnum.DOUYIN,
        run_time="09:00",
        max_pages=3,
        save_option=SaveDataOptionEnum.SQLITE,
        status="paused",
        creators=["https://space.bilibili.com/20813884"],
    )

    with pytest.raises(ValueError, match="Unsupported Douyin creator URL"):
        await service.create_task(payload)

    await service.shutdown()


@pytest.mark.asyncio
async def test_scheduled_task_run_executes_creators_sequentially_and_keeps_partial_success(
    tmp_path,
    monkeypatch,
):
    service = await _build_service(tmp_path, monkeypatch)
    payload = ScheduledTaskUpsertRequest(
        name="知乎作者日采",
        platform=PlatformEnum.ZHIHU,
        run_time="09:00",
        max_pages=2,
        enable_comments=False,
        enable_sub_comments=False,
        save_option=SaveDataOptionEnum.SQLITE,
        status="paused",
        creators=["alice", "bob", "carol"],
    )
    task = await service.create_task(payload)

    start_calls: list[str] = []
    exit_codes = iter([0, 2, 0])
    count_sequences = {
        "alice": [0, 2],
        "bob": [3, 3],
        "carol": [1, 4],
    }

    async def fake_start(request):
        start_calls.append(request.creator_ids)
        return True

    async def fake_wait():
        return next(exit_codes)

    async def fake_count_creator_items(_platform, creator):
        return count_sequences[creator["normalized_creator_id"]].pop(0)

    monkeypatch.setattr("api.scheduled_tasks.service.crawler_manager.start", fake_start)
    monkeypatch.setattr("api.scheduled_tasks.service.crawler_manager.wait", fake_wait)
    monkeypatch.setattr("api.scheduled_tasks.service.crawler_manager.process", None)
    monkeypatch.setattr(service, "_count_creator_items", fake_count_creator_items)

    await service._execute_task_run(task["id"], "manual")
    runs_payload = await service.list_runs(task["id"])
    updated_task = await service.get_task(task["id"])

    assert start_calls == ["alice", "bob", "carol"]
    assert len(runs_payload["runs"]) == 1
    assert runs_payload["runs"][0]["status"] == "partial"
    assert [item["normalized_creator_id"] for item in runs_payload["runs"][0]["items"]] == [
        "alice",
        "bob",
        "carol",
    ]
    assert [item["status"] for item in runs_payload["runs"][0]["items"]] == [
        "success",
        "failed",
        "success",
    ]
    assert [item["items_fetched"] for item in runs_payload["runs"][0]["items"]] == [2, 0, 3]
    assert updated_task["last_success_at"] != ""
    assert "bob: Crawler exited with code: 2" in updated_task["last_error"]

    await service.shutdown()


@pytest.mark.asyncio
async def test_delete_task_removes_queued_run_requests(tmp_path, monkeypatch):
    service = await _build_service(tmp_path, monkeypatch)
    payload = ScheduledTaskUpsertRequest(
        name="微博作者日采",
        platform=PlatformEnum.WEIBO,
        run_time="09:00",
        max_pages=3,
        save_option=SaveDataOptionEnum.SQLITE,
        status="paused",
        creators=["1234567890"],
    )
    task = await service.create_task(payload)

    await service.run_task_now(task["id"])
    assert service.is_busy() is True

    await service.delete_task(task["id"])

    assert service._queue.empty() is True
    with pytest.raises(LookupError):
        await service.get_task(task["id"])

    await service.shutdown()
