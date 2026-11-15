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
async def test_xhs_scheduled_task_uses_pure_api_without_cdp(tmp_path, monkeypatch):
    service = await _build_service(tmp_path, monkeypatch)
    task = await service.create_task(
        ScheduledTaskUpsertRequest(
            name="小红书纯 API 日采",
            platform=PlatformEnum.XHS,
            run_time="09:00",
            max_pages=1,
            save_option=SaveDataOptionEnum.SQLITE,
            status="paused",
            creators=[
                "https://www.xiaohongshu.com/user/profile/640c29eb000000001001c91b?xsec_token=tokenA&xsec_source=pc_search"
            ],
        )
    )
    requests = []

    async def fake_start(request):
        requests.append(request)
        return True

    async def fake_count_creator_items(_platform, _creator):
        return 0

    async def fake_wait():
        return 0

    monkeypatch.setattr("api.scheduled_tasks.service.crawler_manager.start", fake_start)
    monkeypatch.setattr("api.scheduled_tasks.service.crawler_manager.wait", fake_wait)
    monkeypatch.setattr("api.scheduled_tasks.service.crawler_manager.process", None)
    monkeypatch.setattr(service, "_count_creator_items", fake_count_creator_items)

    await service._execute_task_run(task["id"], "manual")

    assert len(requests) == 1
    request = requests[0]
    assert request.pure_api is True
    assert request.cdp_attach_only is False
    assert request.login_type.value == "cookie"
    assert request.creator_ids == task["creators"][0]["raw_input"]

    await service.shutdown()


@pytest.mark.asyncio
async def test_xhs_default_schedule_is_one_daily_safe_creator_run(tmp_path, monkeypatch):
    service = await _build_service(tmp_path, monkeypatch)
    monkeypatch.setenv("AUTO_SEED_XHS_SCHEDULE", "true")
    monkeypatch.setenv(
        "XHS_CREATOR_IDS",
        "5b4e046811be1031e22f19d8,640c29eb000000001001c91b",
    )
    monkeypatch.setenv("XHS_SCHEDULE_RUN_TIME", "10:30")

    await service.ensure_default_xhs_schedule()
    task = (await service.list_tasks())["tasks"][0]

    assert task["name"] == "小红书每日安全快照(自动)"
    assert task["platform"] == "xhs"
    assert task["run_time"] == "10:30"
    assert task["max_pages"] == 1
    assert task["enable_comments"] is False
    assert [creator["normalized_creator_id"] for creator in task["creators"]] == [
        "5b4e046811be1031e22f19d8"
    ]

    await service.shutdown()


@pytest.mark.asyncio
async def test_bilibili_default_schedule_uses_configured_frequency(tmp_path, monkeypatch):
    service = await _build_service(tmp_path, monkeypatch)
    monkeypatch.setenv("AUTO_SEED_BILI_SCHEDULE", "true")
    monkeypatch.setenv("BILI_SCHEDULE_CREATOR_IDS", "20813884, 625267185")
    monkeypatch.setenv("BILI_SCHEDULE_RUN_TIME", "09:00,21:00")
    monkeypatch.setenv("BILI_SCHEDULE_SAVE_OPTION", "sqlite")

    await service.ensure_default_bilibili_schedule()
    task = (await service.list_tasks())["tasks"][0]

    assert task["name"] == "B站增长快照(自动)"
    assert task["platform"] == "bili"
    assert task["run_time"] == "09:00,21:00"
    assert task["status"] == "active"
    assert [creator["normalized_creator_id"] for creator in task["creators"]] == ["20813884", "625267185"]

    await service.shutdown()


@pytest.mark.asyncio
async def test_bilibili_scheduled_task_uses_pure_api_and_snapshot_slot(tmp_path, monkeypatch):
    service = await _build_service(tmp_path, monkeypatch)
    task = await service.create_task(
        ScheduledTaskUpsertRequest(
            name="B站增长快照(自动)",
            platform=PlatformEnum.BILIBILI,
            run_time="09:00",
            max_pages=1,
            save_option=SaveDataOptionEnum.SQLITE,
            status="paused",
            creators=["https://space.bilibili.com/20813884"],
        )
    )
    requests = []

    async def fake_start(request):
        requests.append(request)
        return True

    async def fake_count_creator_items(_platform, _creator):
        return 0

    async def fake_wait():
        return 0

    monkeypatch.setenv("SCHEDULED_CRAWL_PURE_API", "true")
    monkeypatch.setenv("BILI_SCHEDULE_SYNC_FROM_DB", "false")
    monkeypatch.setattr("api.scheduled_tasks.service.crawler_manager.start", fake_start)
    monkeypatch.setattr("api.scheduled_tasks.service.crawler_manager.wait", fake_wait)
    monkeypatch.setattr("api.scheduled_tasks.service.crawler_manager.process", None)
    monkeypatch.setattr(service, "_count_creator_items", fake_count_creator_items)

    await service._execute_task_run(task["id"], "schedule", scheduled_slot="morning")

    assert len(requests) == 1
    assert requests[0].pure_api is True
    assert requests[0].cdp_attach_only is False
    assert requests[0].scheduled_slot == "morning"
    assert requests[0].creator_ids == "20813884"

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
