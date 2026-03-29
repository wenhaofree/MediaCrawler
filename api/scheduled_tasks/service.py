# -*- coding: utf-8 -*-
#
# This file is part of MediaCrawler project.

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse
from zoneinfo import ZoneInfo

import aiosqlite
import httpx
from playwright.async_api import async_playwright

import config
from api.schemas import (
    CrawlerStartRequest,
    CrawlerTypeEnum,
    LoginTypeEnum,
    PlatformEnum,
    SaveDataOptionEnum,
    ScheduledTaskUpsertRequest,
)
from config import db_config
from media_platform.bilibili.help import parse_creator_info_from_url as parse_bili_creator
from media_platform.douyin.help import parse_creator_info_from_url as parse_douyin_creator
from media_platform.xhs.extractor import XiaoHongShuExtractor
from media_platform.xhs.help import parse_creator_info_from_url as parse_xhs_creator
from tools import utils
from tools.cdp_browser import CDPBrowserManager

from ..services import crawler_manager


SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")
SUPPORTED_PLATFORMS = ("xhs", "dy", "bili", "wb", "zhihu")
ITEM_COUNT_CONFIG = {
    "xhs": ("xhs_note", "user_id", "xhs_user_id"),
    "dy": ("douyin_aweme", "sec_uid", "normalized_creator_id"),
    "bili": ("bilibili_video", "user_id", "normalized_creator_id"),
    "wb": ("weibo_note", "user_id", "normalized_creator_id"),
    "zhihu": ("zhihu_content", "user_url_token", "normalized_creator_id"),
}
TASKS_PAGE_SIZE = 20
RUNS_PAGE_SIZE = 20


@dataclass
class RunRequest:
    task_id: int
    trigger_type: str


def _now() -> datetime:
    return datetime.now(tz=SHANGHAI_TZ)


def _now_iso() -> str:
    return _now().isoformat()


def _db_path() -> Path:
    return Path(db_config.SQLITE_DB_PATH)


@asynccontextmanager
async def _get_connection() -> Any:
    db_path = _db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys = ON")
        yield db
        await db.commit()


async def _fetchone(db: aiosqlite.Connection, sql: str, params: tuple[Any, ...] = ()) -> aiosqlite.Row | None:
    cursor = await db.execute(sql, params)
    row = await cursor.fetchone()
    await cursor.close()
    return row


async def _fetchall(db: aiosqlite.Connection, sql: str, params: tuple[Any, ...] = ()) -> list[aiosqlite.Row]:
    cursor = await db.execute(sql, params)
    rows = await cursor.fetchall()
    await cursor.close()
    return rows


def _bool_to_int(value: bool) -> int:
    return 1 if value else 0


def _parse_run_time(run_time: str) -> tuple[int, int]:
    parts = run_time.split(":")
    if len(parts) != 2:
        raise ValueError("run_time must be in HH:MM format")
    try:
        hour = int(parts[0])
        minute = int(parts[1])
    except ValueError as exc:
        raise ValueError("run_time must be in HH:MM format") from exc
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError("run_time must be in HH:MM format")
    return hour, minute


def _compute_next_run(run_time: str, now: datetime | None = None) -> datetime:
    hour, minute = _parse_run_time(run_time)
    now = now or _now()
    next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if next_run <= now:
        next_run += timedelta(days=1)
    return next_run


def _normalize_zhihu_creator(raw_value: str) -> str:
    value = raw_value.strip()
    if not value:
        raise ValueError("Zhihu creator cannot be empty")
    if value.startswith("http://") or value.startswith("https://"):
        parsed = urlparse(value)
        if "zhihu.com" not in parsed.netloc or "/people/" not in parsed.path:
            raise ValueError(f"Unsupported Zhihu creator URL: {raw_value}")
        return parsed.path.rstrip("/").split("/")[-1]
    return value


def _is_http_url(value: str) -> bool:
    return value.startswith("http://") or value.startswith("https://")


def _validate_platform_url(platform: str, value: str, expected_domains: tuple[str, ...]) -> None:
    if not _is_http_url(value):
        return
    netloc = urlparse(value).netloc.lower()
    if not any(domain in netloc for domain in expected_domains):
        raise ValueError(f"Unsupported {platform} creator URL: {value}")


def _normalize_weibo_creator(raw_value: str) -> str:
    value = raw_value.strip()
    if not value:
        raise ValueError("Weibo creator cannot be empty")
    if value.startswith("http://") or value.startswith("https://"):
        raise ValueError("Weibo scheduled creator input must use user ID, not URL")
    if not value.isdigit():
        raise ValueError(f"Unsupported Weibo creator ID: {raw_value}")
    return value


def _normalize_creator(platform: str, raw_value: str) -> dict[str, str]:
    value = raw_value.strip()
    if not value:
        raise ValueError("Creator cannot be empty")

    if platform == "xhs":
        _validate_platform_url("Xiaohongshu", value, ("xiaohongshu.com",))
        creator = parse_xhs_creator(value)
        return {
            "raw_input": value,
            "normalized_creator_id": creator.user_id,
            "display_name": creator.user_id,
            "xhs_user_id": creator.user_id,
            "xhs_xsec_token": creator.xsec_token,
            "xhs_xsec_source": creator.xsec_source or "pc_search",
        }
    if platform == "dy":
        _validate_platform_url("Douyin", value, ("douyin.com",))
        if not _is_http_url(value) and (value.isdigit() or "/" in value):
            raise ValueError(f"Unsupported Douyin creator ID: {value}")
        creator = parse_douyin_creator(value)
        return {
            "raw_input": value,
            "normalized_creator_id": creator.sec_user_id,
            "display_name": creator.sec_user_id,
            "xhs_user_id": "",
            "xhs_xsec_token": "",
            "xhs_xsec_source": "",
        }
    if platform == "bili":
        _validate_platform_url("Bilibili", value, ("bilibili.com",))
        creator = parse_bili_creator(value)
        return {
            "raw_input": value,
            "normalized_creator_id": creator.creator_id,
            "display_name": creator.creator_id,
            "xhs_user_id": "",
            "xhs_xsec_token": "",
            "xhs_xsec_source": "",
        }
    if platform == "wb":
        if _is_http_url(value):
            raise ValueError("Weibo scheduled creator input must use user ID, not URL")
        creator_id = _normalize_weibo_creator(value)
        return {
            "raw_input": value,
            "normalized_creator_id": creator_id,
            "display_name": creator_id,
            "xhs_user_id": "",
            "xhs_xsec_token": "",
            "xhs_xsec_source": "",
        }
    if platform == "zhihu":
        _validate_platform_url("Zhihu", value, ("zhihu.com",))
        if not _is_http_url(value) and "/" in value:
            raise ValueError(f"Unsupported Zhihu creator ID: {value}")
        creator_id = _normalize_zhihu_creator(value)
        return {
            "raw_input": value,
            "normalized_creator_id": creator_id,
            "display_name": creator_id,
            "xhs_user_id": "",
            "xhs_xsec_token": "",
            "xhs_xsec_source": "",
        }
    raise ValueError(f"Unsupported platform: {platform}")


def _normalize_creators(platform: str, creators: list[str]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    seen: set[str] = set()
    for raw_value in creators:
        item = _normalize_creator(platform, raw_value)
        dedupe_key = item["normalized_creator_id"]
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        normalized.append(item)
    if not normalized:
        raise ValueError("At least one valid creator is required")
    return normalized


def _task_row_to_dict(row: aiosqlite.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "platform": row["platform"],
        "run_time": row["run_time"],
        "max_pages": row["max_pages"],
        "enable_comments": bool(row["enable_comments"]),
        "enable_sub_comments": bool(row["enable_sub_comments"]),
        "save_option": row["save_option"],
        "status": row["status"],
        "last_run_at": row["last_run_at"] or "",
        "last_success_at": row["last_success_at"] or "",
        "last_error": row["last_error"] or "",
        "next_run_at": row["next_run_at"] or "",
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _creator_row_to_dict(row: aiosqlite.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "task_id": row["task_id"],
        "sort_order": row["sort_order"],
        "raw_input": row["raw_input"],
        "normalized_creator_id": row["normalized_creator_id"],
        "display_name": row["display_name"] or row["normalized_creator_id"],
        "xhs_user_id": row["xhs_user_id"] or "",
        "xhs_xsec_token": row["xhs_xsec_token"] or "",
        "xhs_xsec_source": row["xhs_xsec_source"] or "",
        "last_success_at": row["last_success_at"] or "",
        "last_error": row["last_error"] or "",
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _run_row_to_dict(row: aiosqlite.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "task_id": row["task_id"],
        "status": row["status"],
        "trigger_type": row["trigger_type"],
        "started_at": row["started_at"],
        "finished_at": row["finished_at"] or "",
        "error_message": row["error_message"] or "",
        "created_at": row["created_at"],
    }


def _run_item_row_to_dict(row: aiosqlite.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "run_id": row["run_id"],
        "task_id": row["task_id"],
        "creator_id": row["creator_id"],
        "raw_input": row["raw_input"],
        "normalized_creator_id": row["normalized_creator_id"],
        "status": row["status"],
        "started_at": row["started_at"],
        "finished_at": row["finished_at"] or "",
        "pages_fetched": row["pages_fetched"] or 0,
        "items_fetched": row["items_fetched"] or 0,
        "error_message": row["error_message"] or "",
        "effective_creator_arg": row["effective_creator_arg"] or "",
    }


class ScheduledTaskService:
    def __init__(self) -> None:
        self._queue: asyncio.Queue[RunRequest] = asyncio.Queue()
        self._worker_task: asyncio.Task | None = None
        self._trigger_tasks: dict[int, asyncio.Task] = {}
        self._started = False
        self._current_task_id: int | None = None

    def is_busy(self) -> bool:
        return self._current_task_id is not None or not self._queue.empty()

    async def ensure_tables(self) -> None:
        async with _get_connection() as db:
            await db.executescript(
                """
                CREATE TABLE IF NOT EXISTS scheduled_crawl_task (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    run_time TEXT NOT NULL,
                    max_pages INTEGER NOT NULL DEFAULT 3,
                    enable_comments INTEGER NOT NULL DEFAULT 0,
                    enable_sub_comments INTEGER NOT NULL DEFAULT 0,
                    save_option TEXT NOT NULL DEFAULT 'sqlite',
                    status TEXT NOT NULL DEFAULT 'active',
                    last_run_at TEXT,
                    last_success_at TEXT,
                    last_error TEXT,
                    next_run_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS scheduled_crawl_task_creator (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    raw_input TEXT NOT NULL,
                    normalized_creator_id TEXT NOT NULL,
                    display_name TEXT,
                    xhs_user_id TEXT,
                    xhs_xsec_token TEXT,
                    xhs_xsec_source TEXT,
                    last_success_at TEXT,
                    last_error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS scheduled_crawl_run (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    trigger_type TEXT NOT NULL DEFAULT 'schedule',
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    error_message TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS scheduled_crawl_run_item (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL,
                    task_id INTEGER NOT NULL,
                    creator_id INTEGER NOT NULL,
                    raw_input TEXT NOT NULL,
                    normalized_creator_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    pages_fetched INTEGER DEFAULT 0,
                    items_fetched INTEGER DEFAULT 0,
                    error_message TEXT,
                    effective_creator_arg TEXT
                );

                CREATE UNIQUE INDEX IF NOT EXISTS idx_scheduled_crawl_creator_unique
                ON scheduled_crawl_task_creator(task_id, normalized_creator_id);
                CREATE INDEX IF NOT EXISTS idx_scheduled_crawl_task_status
                ON scheduled_crawl_task(status);
                CREATE INDEX IF NOT EXISTS idx_scheduled_crawl_run_task_id
                ON scheduled_crawl_run(task_id);
                CREATE INDEX IF NOT EXISTS idx_scheduled_crawl_run_item_run_id
                ON scheduled_crawl_run_item(run_id);
                """
            )

    async def start(self) -> None:
        if self._started:
            return
        await self.ensure_tables()
        self._worker_task = asyncio.create_task(self._worker_loop())
        self._started = True
        await self.refresh_all_schedules()

    async def shutdown(self) -> None:
        for trigger in self._trigger_tasks.values():
            trigger.cancel()
        self._trigger_tasks.clear()
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None
        self._started = False

    async def refresh_all_schedules(self) -> None:
        async with _get_connection() as db:
            task_rows = await _fetchall(
                db,
                "SELECT * FROM scheduled_crawl_task WHERE status = 'active'",
            )
            active_ids = {row["id"] for row in task_rows}
            for task_id in list(self._trigger_tasks):
                if task_id not in active_ids:
                    self._trigger_tasks[task_id].cancel()
                    self._trigger_tasks.pop(task_id, None)
            for row in task_rows:
                await self._schedule_task(_task_row_to_dict(row))

    async def _schedule_task(self, task: dict[str, Any]) -> None:
        task_id = task["id"]
        if task_id in self._trigger_tasks:
            self._trigger_tasks[task_id].cancel()
        self._trigger_tasks[task_id] = asyncio.create_task(
            self._trigger_loop(task_id),
            name=f"scheduled-task-{task_id}",
        )

    async def refresh_task_schedule(self, task_id: int) -> None:
        async with _get_connection() as db:
            row = await _fetchone(
                db, "SELECT * FROM scheduled_crawl_task WHERE id = ?", (task_id,)
            )
            if not row or row["status"] != "active":
                trigger = self._trigger_tasks.pop(task_id, None)
                if trigger:
                    trigger.cancel()
                if row:
                    await db.execute(
                        "UPDATE scheduled_crawl_task SET next_run_at = '', updated_at = ? WHERE id = ?",
                        (_now_iso(), task_id),
                    )
                return
            await self._schedule_task(_task_row_to_dict(row))

    async def _trigger_loop(self, task_id: int) -> None:
        try:
            while True:
                async with _get_connection() as db:
                    row = await _fetchone(
                        db, "SELECT * FROM scheduled_crawl_task WHERE id = ?", (task_id,)
                    )
                    if not row or row["status"] != "active":
                        return
                    next_run = _compute_next_run(row["run_time"])
                    await db.execute(
                        "UPDATE scheduled_crawl_task SET next_run_at = ?, updated_at = ? WHERE id = ?",
                        (next_run.isoformat(), _now_iso(), task_id),
                    )
                delay = max((next_run - _now()).total_seconds(), 0)
                await asyncio.sleep(delay)
                await self._queue.put(RunRequest(task_id=task_id, trigger_type="schedule"))
        except asyncio.CancelledError:
            return
        except Exception:
            utils.logger.exception(
                "[ScheduledTaskService._trigger_loop] failed to schedule task %s",
                task_id,
            )

    async def list_tasks(self) -> dict[str, Any]:
        async with _get_connection() as db:
            task_rows = await _fetchall(
                db,
                "SELECT * FROM scheduled_crawl_task ORDER BY id DESC LIMIT ?",
                (TASKS_PAGE_SIZE,),
            )
            creators_rows = await _fetchall(
                db,
                "SELECT * FROM scheduled_crawl_task_creator ORDER BY task_id ASC, sort_order ASC, id ASC",
            )
            latest_run_rows = await _fetchall(
                db,
                """
                SELECT r.*
                FROM scheduled_crawl_run r
                INNER JOIN (
                    SELECT task_id, MAX(id) AS latest_id
                    FROM scheduled_crawl_run
                    GROUP BY task_id
                ) latest ON latest.latest_id = r.id
                """,
            )

        creators_by_task: dict[int, list[dict[str, Any]]] = {}
        for row in creators_rows:
            creators_by_task.setdefault(row["task_id"], []).append(_creator_row_to_dict(row))

        latest_run_by_task = {
            row["task_id"]: _run_row_to_dict(row)
            for row in latest_run_rows
        }

        tasks: list[dict[str, Any]] = []
        for row in task_rows:
            task = _task_row_to_dict(row)
            task["creators"] = creators_by_task.get(task["id"], [])
            task["creator_count"] = len(task["creators"])
            task["latest_run"] = latest_run_by_task.get(task["id"], {})
            tasks.append(task)
        return {"tasks": tasks, "busy": self.is_busy()}

    async def get_task(self, task_id: int) -> dict[str, Any]:
        async with _get_connection() as db:
            row = await _fetchone(
                db, "SELECT * FROM scheduled_crawl_task WHERE id = ?", (task_id,)
            )
            if not row:
                raise LookupError(f"Scheduled task {task_id} not found")
            creators_rows = await _fetchall(
                db,
                "SELECT * FROM scheduled_crawl_task_creator WHERE task_id = ? ORDER BY sort_order ASC, id ASC",
                (task_id,),
            )
        task = _task_row_to_dict(row)
        task["creators"] = [_creator_row_to_dict(item) for item in creators_rows]
        task["creator_count"] = len(task["creators"])
        return task

    async def create_task(self, payload: ScheduledTaskUpsertRequest) -> dict[str, Any]:
        _parse_run_time(payload.run_time)
        platform = payload.platform.value
        if platform not in SUPPORTED_PLATFORMS:
            raise ValueError(f"Unsupported scheduled platform: {platform}")
        normalized_creators = _normalize_creators(platform, payload.creators)
        now_iso = _now_iso()
        next_run_at = (
            _compute_next_run(payload.run_time).isoformat()
            if payload.status == "active"
            else ""
        )

        async with _get_connection() as db:
            cursor = await db.execute(
                """
                INSERT INTO scheduled_crawl_task (
                    name, platform, run_time, max_pages, enable_comments,
                    enable_sub_comments, save_option, status, last_run_at,
                    last_success_at, last_error, next_run_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, '', '', '', ?, ?, ?)
                """,
                (
                    payload.name.strip(),
                    platform,
                    payload.run_time,
                    payload.max_pages,
                    _bool_to_int(payload.enable_comments),
                    _bool_to_int(payload.enable_sub_comments),
                    payload.save_option.value,
                    payload.status,
                    next_run_at,
                    now_iso,
                    now_iso,
                ),
            )
            task_id = cursor.lastrowid
            await self._insert_creators(
                db=db,
                task_id=task_id,
                normalized_creators=normalized_creators,
                existing_by_creator_id={},
            )
        await self.refresh_task_schedule(task_id)
        return await self.get_task(task_id)

    async def update_task(self, task_id: int, payload: ScheduledTaskUpsertRequest) -> dict[str, Any]:
        _parse_run_time(payload.run_time)
        platform = payload.platform.value
        if platform not in SUPPORTED_PLATFORMS:
            raise ValueError(f"Unsupported scheduled platform: {platform}")
        normalized_creators = _normalize_creators(platform, payload.creators)
        now_iso = _now_iso()

        async with _get_connection() as db:
            existing_task = await _fetchone(
                db, "SELECT * FROM scheduled_crawl_task WHERE id = ?", (task_id,)
            )
            if not existing_task:
                raise LookupError(f"Scheduled task {task_id} not found")

            existing_creator_rows = await _fetchall(
                db,
                "SELECT * FROM scheduled_crawl_task_creator WHERE task_id = ?",
                (task_id,),
            )
            existing_by_creator_id = {
                row["normalized_creator_id"]: _creator_row_to_dict(row)
                for row in existing_creator_rows
            }

            next_run_at = (
                _compute_next_run(payload.run_time).isoformat()
                if payload.status == "active"
                else ""
            )
            await db.execute(
                """
                UPDATE scheduled_crawl_task
                SET name = ?, platform = ?, run_time = ?, max_pages = ?,
                    enable_comments = ?, enable_sub_comments = ?, save_option = ?,
                    status = ?, next_run_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    payload.name.strip(),
                    payload.platform.value,
                    payload.run_time,
                    payload.max_pages,
                    _bool_to_int(payload.enable_comments),
                    _bool_to_int(payload.enable_sub_comments),
                    payload.save_option.value,
                    payload.status,
                    next_run_at,
                    now_iso,
                    task_id,
                ),
            )
            await db.execute(
                "DELETE FROM scheduled_crawl_task_creator WHERE task_id = ?",
                (task_id,),
            )
            await self._insert_creators(
                db=db,
                task_id=task_id,
                normalized_creators=normalized_creators,
                existing_by_creator_id=existing_by_creator_id,
            )
        await self.refresh_task_schedule(task_id)
        return await self.get_task(task_id)

    async def delete_task(self, task_id: int) -> None:
        if self._current_task_id == task_id:
            raise ValueError("Cannot delete a scheduled task while it is running")

        trigger = self._trigger_tasks.pop(task_id, None)
        if trigger:
            trigger.cancel()
        self._remove_queued_requests(task_id)

        async with _get_connection() as db:
            task_row = await _fetchone(
                db, "SELECT id FROM scheduled_crawl_task WHERE id = ?", (task_id,)
            )
            if not task_row:
                raise LookupError(f"Scheduled task {task_id} not found")
            run_rows = await _fetchall(
                db, "SELECT id FROM scheduled_crawl_run WHERE task_id = ?", (task_id,)
            )
            for run_row in run_rows:
                await db.execute(
                    "DELETE FROM scheduled_crawl_run_item WHERE run_id = ?",
                    (run_row["id"],),
                )
            await db.execute(
                "DELETE FROM scheduled_crawl_run WHERE task_id = ?",
                (task_id,),
            )
            await db.execute(
                "DELETE FROM scheduled_crawl_task_creator WHERE task_id = ?",
                (task_id,),
            )
            await db.execute(
                "DELETE FROM scheduled_crawl_task WHERE id = ?",
                (task_id,),
            )

    async def list_runs(self, task_id: int) -> dict[str, Any]:
        async with _get_connection() as db:
            task_row = await _fetchone(
                db, "SELECT id FROM scheduled_crawl_task WHERE id = ?", (task_id,)
            )
            if not task_row:
                raise LookupError(f"Scheduled task {task_id} not found")
            run_rows = await _fetchall(
                db,
                "SELECT * FROM scheduled_crawl_run WHERE task_id = ? ORDER BY id DESC LIMIT ?",
                (task_id, RUNS_PAGE_SIZE),
            )
            run_ids = [row["id"] for row in run_rows]
            run_item_rows: list[aiosqlite.Row] = []
            if run_ids:
                placeholders = ",".join(["?"] * len(run_ids))
                run_item_rows = await _fetchall(
                    db,
                    f"SELECT * FROM scheduled_crawl_run_item WHERE run_id IN ({placeholders}) ORDER BY id ASC",
                    tuple(run_ids),
                )

        items_by_run: dict[int, list[dict[str, Any]]] = {}
        for row in run_item_rows:
            items_by_run.setdefault(row["run_id"], []).append(_run_item_row_to_dict(row))

        runs = []
        for row in run_rows:
            run = _run_row_to_dict(row)
            run["items"] = items_by_run.get(run["id"], [])
            runs.append(run)
        return {"runs": runs}

    async def run_task_now(self, task_id: int) -> dict[str, Any]:
        await self.get_task(task_id)
        await self._queue.put(RunRequest(task_id=task_id, trigger_type="manual"))
        return {"status": "queued", "task_id": task_id}

    async def get_cdp_status(self) -> dict[str, Any]:
        endpoints = [
            f"http://localhost:{config.CDP_DEBUG_PORT}",
            f"http://[::1]:{config.CDP_DEBUG_PORT}",
            f"http://127.0.0.1:{config.CDP_DEBUG_PORT}",
        ]
        last_error = ""
        async with httpx.AsyncClient(trust_env=False) as client:
            for endpoint in endpoints:
                try:
                    response = await client.get(f"{endpoint}/json/version", timeout=5)
                    response.raise_for_status()
                    payload = response.json()
                    return {
                        "status": "ok",
                        "attached": True,
                        "endpoint": endpoint,
                        "browser": payload.get("Browser", ""),
                        "web_socket_debugger_url": payload.get(
                            "webSocketDebuggerUrl", ""
                        ),
                    }
                except Exception as exc:
                    last_error = str(exc)
        return {
            "status": "error",
            "attached": False,
            "endpoint": "",
            "browser": "",
            "web_socket_debugger_url": "",
            "error": last_error,
        }

    async def _insert_creators(
        self,
        db: aiosqlite.Connection,
        task_id: int,
        normalized_creators: list[dict[str, str]],
        existing_by_creator_id: dict[str, dict[str, Any]],
    ) -> None:
        now_iso = _now_iso()
        for index, creator in enumerate(normalized_creators):
            previous = existing_by_creator_id.get(creator["normalized_creator_id"], {})
            await db.execute(
                """
                INSERT INTO scheduled_crawl_task_creator (
                    task_id, sort_order, raw_input, normalized_creator_id, display_name,
                    xhs_user_id, xhs_xsec_token, xhs_xsec_source, last_success_at,
                    last_error, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    index,
                    creator["raw_input"],
                    creator["normalized_creator_id"],
                    previous.get("display_name") or creator["display_name"],
                    previous.get("xhs_user_id") or creator["xhs_user_id"],
                    previous.get("xhs_xsec_token") or creator["xhs_xsec_token"],
                    previous.get("xhs_xsec_source") or creator["xhs_xsec_source"],
                    previous.get("last_success_at", ""),
                    previous.get("last_error", ""),
                    previous.get("created_at") or now_iso,
                    now_iso,
                ),
            )

    async def _worker_loop(self) -> None:
        try:
            while True:
                request = await self._queue.get()
                self._current_task_id = request.task_id
                try:
                    await self._execute_task_run(request.task_id, request.trigger_type)
                except Exception:
                    utils.logger.exception(
                        "[ScheduledTaskService._worker_loop] failed to execute task %s",
                        request.task_id,
                    )
                finally:
                    self._current_task_id = None
                    self._queue.task_done()
        except asyncio.CancelledError:
            return

    def _remove_queued_requests(self, task_id: int) -> None:
        pending_requests: list[RunRequest] = []
        while True:
            try:
                request = self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break

            self._queue.task_done()
            if request.task_id == task_id:
                continue
            pending_requests.append(request)

        for request in pending_requests:
            self._queue.put_nowait(request)

    async def _execute_task_run(self, task_id: int, trigger_type: str) -> None:
        task = await self.get_task(task_id)
        started_at = _now_iso()
        async with _get_connection() as db:
            cursor = await db.execute(
                """
                INSERT INTO scheduled_crawl_run (
                    task_id, status, trigger_type, started_at, finished_at, error_message, created_at
                ) VALUES (?, 'running', ?, ?, '', '', ?)
                """,
                (task_id, trigger_type, started_at, started_at),
            )
            run_id = cursor.lastrowid
            await db.execute(
                "UPDATE scheduled_crawl_task SET last_run_at = ?, updated_at = ? WHERE id = ?",
                (started_at, started_at, task_id),
            )

        results = []
        for creator in task["creators"]:
            result = await self._execute_creator_run(task=task, creator=creator, run_id=run_id)
            results.append(result)

        statuses = [item["status"] for item in results]
        failed = [item for item in results if item["status"] == "failed"]
        partial = [item for item in results if item["status"] == "partial"]

        if statuses and all(status == "success" for status in statuses):
            final_status = "success"
        elif failed and len(failed) == len(results):
            final_status = "failed"
        else:
            final_status = "partial"

        error_message = "; ".join(
            f"{item['normalized_creator_id']}: {item['error_message']}"
            for item in results
            if item["error_message"]
        )
        finished_at = _now_iso()

        async with _get_connection() as db:
            await db.execute(
                """
                UPDATE scheduled_crawl_run
                SET status = ?, finished_at = ?, error_message = ?
                WHERE id = ?
                """,
                (final_status, finished_at, error_message, run_id),
            )
            await db.execute(
                """
                UPDATE scheduled_crawl_task
                SET last_success_at = CASE WHEN ? != 'failed' THEN ? ELSE last_success_at END,
                    last_error = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    final_status,
                    finished_at,
                    "" if final_status == "success" else error_message,
                    finished_at,
                    task_id,
                ),
            )

    async def _execute_creator_run(
        self,
        task: dict[str, Any],
        creator: dict[str, Any],
        run_id: int,
    ) -> dict[str, Any]:
        started_at = _now_iso()
        effective_creator_arg = creator["raw_input"]
        forced_partial = False
        preflight_error = ""
        pages_fetched = 0
        items_before = await self._count_creator_items(task["platform"], creator)

        if task["platform"] == "xhs":
            refresh_result = await self._prepare_xhs_creator_for_run(creator)
            if refresh_result["status"] == "failed":
                result = {
                    "status": "failed",
                    "error_message": refresh_result["error_message"],
                    "items_fetched": 0,
                    "pages_fetched": 0,
                    "effective_creator_arg": "",
                    "normalized_creator_id": creator["normalized_creator_id"],
                }
                await self._persist_run_item(
                    run_id=run_id,
                    task_id=task["id"],
                    creator=creator,
                    started_at=started_at,
                    finished_at=_now_iso(),
                    result=result,
                )
                await self._update_creator_outcome(
                    creator_id=creator["id"],
                    success=False,
                    error_message=refresh_result["error_message"],
                )
                return result
            effective_creator_arg = refresh_result["effective_creator_arg"]
            forced_partial = refresh_result["partial"]
            preflight_error = refresh_result["error_message"]
        else:
            effective_creator_arg = creator["normalized_creator_id"]

        while crawler_manager.process and crawler_manager.process.poll() is None:
            await asyncio.sleep(0.2)

        save_option = SaveDataOptionEnum(task["save_option"])
        request = CrawlerStartRequest(
            platform=PlatformEnum(task["platform"]),
            login_type=LoginTypeEnum.QRCODE,
            crawler_type=CrawlerTypeEnum.CREATOR,
            creator_ids=effective_creator_arg,
            enable_comments=task["enable_comments"],
            enable_sub_comments=task["enable_sub_comments"],
            save_option=save_option,
            headless=False,
            max_pages=task["max_pages"],
            cdp_attach_only=True,
        )

        success = await crawler_manager.start(request)
        if not success:
            exit_code = -1
            error_message = "Crawler is already running"
        else:
            exit_code = await crawler_manager.wait()
            error_message = "" if exit_code == 0 else f"Crawler exited with code: {exit_code}"

        items_after = await self._count_creator_items(task["platform"], creator)
        items_fetched = max(items_after - items_before, 0)
        if exit_code == 0:
            status = "partial" if forced_partial else "success"
            pages_fetched = task["max_pages"]
            error_message = preflight_error
        else:
            status = "failed"
            pages_fetched = 0

        finished_at = _now_iso()
        result = {
            "status": status,
            "error_message": error_message,
            "items_fetched": items_fetched,
            "pages_fetched": pages_fetched,
            "effective_creator_arg": effective_creator_arg,
            "normalized_creator_id": creator["normalized_creator_id"],
        }
        await self._persist_run_item(
            run_id=run_id,
            task_id=task["id"],
            creator=creator,
            started_at=started_at,
            finished_at=finished_at,
            result=result,
        )
        await self._update_creator_outcome(
            creator_id=creator["id"],
            success=status in ("success", "partial"),
            error_message=error_message,
        )
        return result

    async def _persist_run_item(
        self,
        run_id: int,
        task_id: int,
        creator: dict[str, Any],
        started_at: str,
        finished_at: str,
        result: dict[str, Any],
    ) -> None:
        async with _get_connection() as db:
            await db.execute(
                """
                INSERT INTO scheduled_crawl_run_item (
                    run_id, task_id, creator_id, raw_input, normalized_creator_id,
                    status, started_at, finished_at, pages_fetched, items_fetched,
                    error_message, effective_creator_arg
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    task_id,
                    creator["id"],
                    creator["raw_input"],
                    creator["normalized_creator_id"],
                    result["status"],
                    started_at,
                    finished_at,
                    result["pages_fetched"],
                    result["items_fetched"],
                    result["error_message"],
                    result["effective_creator_arg"],
                ),
            )

    async def _update_creator_outcome(
        self,
        creator_id: int,
        success: bool,
        error_message: str,
    ) -> None:
        async with _get_connection() as db:
            await db.execute(
                """
                UPDATE scheduled_crawl_task_creator
                SET last_success_at = CASE WHEN ? THEN ? ELSE last_success_at END,
                    last_error = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    _bool_to_int(success),
                    _now_iso(),
                    "" if success else error_message,
                    _now_iso(),
                    creator_id,
                ),
            )

    async def _count_creator_items(self, platform: str, creator: dict[str, Any]) -> int:
        table_name, field_name, creator_key = ITEM_COUNT_CONFIG[platform]
        creator_value = creator.get(creator_key) or creator["normalized_creator_id"]
        async with _get_connection() as db:
            table_row = await _fetchone(
                db,
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
                (table_name,),
            )
            if not table_row:
                return 0
            row = await _fetchone(
                db,
                f"SELECT COUNT(*) AS total FROM {table_name} WHERE {field_name} = ?",
                (creator_value,),
            )
            return int(row["total"]) if row else 0

    async def _prepare_xhs_creator_for_run(self, creator: dict[str, Any]) -> dict[str, Any]:
        user_id = creator["xhs_user_id"] or creator["normalized_creator_id"]
        token = creator["xhs_xsec_token"]
        source = creator["xhs_xsec_source"] or "pc_search"

        try:
            refresh = await self._refresh_xhs_creator_token(
                user_id=user_id,
                xsec_token=token,
                xsec_source=source,
            )
        except Exception as exc:
            return {
                "status": "failed",
                "effective_creator_arg": "",
                "partial": False,
                "error_message": f"Failed to refresh xhs token: {exc}",
            }

        if refresh["token"]:
            await self._update_xhs_creator_token(
                creator_id=creator["id"],
                user_id=user_id,
                xsec_token=refresh["token"],
                xsec_source=refresh["source"],
            )
            return {
                "status": "success",
                "effective_creator_arg": self._build_xhs_creator_url(
                    user_id=user_id,
                    xsec_token=refresh["token"],
                    xsec_source=refresh["source"],
                ),
                "partial": False,
                "error_message": "",
            }

        if refresh["html_available"]:
            return {
                "status": "success",
                "effective_creator_arg": user_id,
                "partial": True,
                "error_message": "xsec_token refresh failed, fallback to HTML first-page crawl",
            }

        return {
            "status": "failed",
            "effective_creator_arg": "",
            "partial": False,
            "error_message": "xsec_token refresh failed and creator HTML could not be parsed",
        }

    async def _update_xhs_creator_token(
        self,
        creator_id: int,
        user_id: str,
        xsec_token: str,
        xsec_source: str,
    ) -> None:
        async with _get_connection() as db:
            await db.execute(
                """
                UPDATE scheduled_crawl_task_creator
                SET xhs_user_id = ?, xhs_xsec_token = ?, xhs_xsec_source = ?, updated_at = ?
                WHERE id = ?
                """,
                (user_id, xsec_token, xsec_source, _now_iso(), creator_id),
            )

    def _build_xhs_creator_url(
        self,
        user_id: str,
        xsec_token: str,
        xsec_source: str,
    ) -> str:
        query = urlencode(
            {
                "xsec_token": xsec_token,
                "xsec_source": xsec_source or "pc_search",
            }
        )
        return f"https://www.xiaohongshu.com/user/profile/{user_id}?{query}"

    async def _refresh_xhs_creator_token(
        self,
        user_id: str,
        xsec_token: str,
        xsec_source: str,
    ) -> dict[str, Any]:
        captured: dict[str, str] = {"token": "", "source": xsec_source or "pc_search"}
        extractor = XiaoHongShuExtractor()
        html_available = False

        async with async_playwright() as playwright:
            cdp_manager = CDPBrowserManager()
            browser_context = await cdp_manager.launch_and_connect(
                playwright,
                user_agent=None,
                headless=False,
                attach_only=True,
            )
            page = await browser_context.new_page()

            def on_request(request: Any) -> None:
                if "/api/sns/web/v1/user_posted" not in request.url:
                    return
                parsed = urlparse(request.url)
                params = parse_qs(parsed.query)
                if params.get("user_id", [""])[0] != user_id:
                    return
                captured["token"] = params.get("xsec_token", [""])[0]
                captured["source"] = params.get("xsec_source", ["pc_search"])[0]

            page.on("request", on_request)
            target_url = f"https://www.xiaohongshu.com/user/profile/{user_id}"
            if xsec_token:
                target_url = self._build_xhs_creator_url(
                    user_id=user_id,
                    xsec_token=xsec_token,
                    xsec_source=xsec_source or "pc_search",
                )
            try:
                await page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass

            await asyncio.sleep(2)
            html = await page.content()
            html_available = bool(
                extractor.extract_creator_notes_from_html(
                    html, xsec_source=captured["source"]
                )
            )

            if not captured["token"]:
                page_params = parse_qs(urlparse(page.url).query)
                captured["token"] = page_params.get("xsec_token", [""])[0]
                if page_params.get("xsec_source", [""])[0]:
                    captured["source"] = page_params.get("xsec_source", [""])[0]

            await page.close()
            await cdp_manager.cleanup(force=True)

        return {
            "token": captured["token"],
            "source": captured["source"] or "pc_search",
            "html_available": html_available,
        }


scheduled_task_service = ScheduledTaskService()
