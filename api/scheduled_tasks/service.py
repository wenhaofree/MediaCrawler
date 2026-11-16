# -*- coding: utf-8 -*-
#
# This file is part of MediaCrawler project.

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import aiosqlite
import httpx

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
from media_platform.xhs.help import parse_creator_info_from_url as parse_xhs_creator
from tools import utils

from ..services import crawler_manager


SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")
SUPPORTED_PLATFORMS = ("xhs", "dy", "bili", "wb", "zhihu", "gzh")
ITEM_COUNT_CONFIG = {
    "xhs": ("xhs_note", "user_id", "xhs_user_id"),
    "dy": ("douyin_aweme", "sec_uid", "normalized_creator_id"),
    "bili": ("bilibili_video", "user_id", "normalized_creator_id"),
    "wb": ("weibo_note", "user_id", "normalized_creator_id"),
    "zhihu": ("zhihu_content", "user_url_token", "normalized_creator_id"),
    "gzh": ("gzh_article", "account_id", "normalized_creator_id"),
}
TASKS_PAGE_SIZE = 20
RUNS_PAGE_SIZE = 20
DEFAULT_DY_SCHEDULE_TASK_NAME = "抖音增长快照(自动)"
DEFAULT_BILI_SCHEDULE_TASK_NAME = "B站增长快照(自动)"
DEFAULT_XHS_SCHEDULE_TASK_NAME = "小红书每日安全快照(自动)"
DEFAULT_GZH_SCHEDULE_TASK_NAME = "公众号每日阅读量快照(自动)"


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "y", "on"}


def _scheduled_crawl_use_pure_api() -> bool:
    return _env_flag("SCHEDULED_CRAWL_PURE_API", default=False)


@dataclass
class RunRequest:
    task_id: int
    trigger_type: str
    scheduled_slot: str = "manual"
    scheduled_hhmm: str = ""


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


def _parse_run_times(run_time: str) -> list[tuple[int, int]]:
    """Parse single '09:00' or multi-slot '09:00,14:00,22:30'."""
    parts = [part.strip() for part in str(run_time or "").split(",") if part.strip()]
    if not parts:
        raise ValueError("run_time must be in HH:MM format")
    times = [_parse_run_time(part) for part in parts]
    # Deduplicate while preserving order
    seen: set[tuple[int, int]] = set()
    unique: list[tuple[int, int]] = []
    for item in times:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique


def _format_hhmm(hour: int, minute: int) -> str:
    return f"{hour:02d}:{minute:02d}"


def _slot_from_hhmm(hour: int, minute: int) -> str:
    try:
        from media_platform.douyin.lifecycle import slot_from_hhmm

        return slot_from_hhmm(hour, minute)
    except Exception:
        if (hour, minute) == (9, 0):
            return "morning"
        if (hour, minute) == (14, 0):
            return "afternoon"
        if (hour, minute) == (22, 30):
            return "evening"
        return "manual"


def _compute_next_run(run_time: str, now: datetime | None = None) -> datetime:
    now = now or _now()
    candidates: list[datetime] = []
    for hour, minute in _parse_run_times(run_time):
        next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if next_run <= now:
            next_run += timedelta(days=1)
        candidates.append(next_run)
    return min(candidates)


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
    if platform == "gzh":
        from media_platform.gzh.weread_cli import normalize_account_id

        account_id = normalize_account_id(value)
        return {
            "raw_input": value,
            "normalized_creator_id": account_id,
            "display_name": account_id,
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
    keys = set(row.keys())
    return {
        "id": row["id"],
        "task_id": row["task_id"],
        "status": row["status"],
        "trigger_type": row["trigger_type"],
        "scheduled_slot": row["scheduled_slot"] if "scheduled_slot" in keys else "manual",
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
                    scheduled_slot TEXT NOT NULL DEFAULT 'manual',
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
            # Backward-compatible column for multi-slot runs
            cursor = await db.execute("PRAGMA table_info(scheduled_crawl_run)")
            columns = {row[1] for row in await cursor.fetchall()}
            await cursor.close()
            if "scheduled_slot" not in columns:
                await db.execute(
                    "ALTER TABLE scheduled_crawl_run ADD COLUMN scheduled_slot TEXT NOT NULL DEFAULT 'manual'"
                )

    async def start(self) -> None:
        if self._started:
            return
        await self.ensure_tables()
        await self.ensure_default_douyin_schedule()
        await self.ensure_default_bilibili_schedule()
        await self.ensure_default_xhs_schedule()
        await self.ensure_default_gzh_schedule()
        self._worker_task = asyncio.create_task(self._worker_loop())
        self._started = True
        await self.refresh_all_schedules()

    async def _load_douyin_creator_ids_from_db(self) -> list[str]:
        """Load distinct sec_uid / user_id values from Postgres douyin_creator."""
        from sqlalchemy import select

        from database.db_session import get_session
        from database.models import DouyinCreator

        save_option = os.getenv("DY_SCHEDULE_SAVE_OPTION", "").strip() or getattr(
            config, "SAVE_DATA_OPTION", "postgres"
        )
        if save_option not in {"postgres", "db", "mysql", "sqlite"}:
            return []

        # Ensure crawl DB session uses the same backend as schedule save option.
        previous = getattr(config, "SAVE_DATA_OPTION", None)
        try:
            config.SAVE_DATA_OPTION = save_option
            async with get_session() as session:
                if session is None:
                    return []
                result = await session.execute(
                    select(DouyinCreator.user_id)
                    .where(DouyinCreator.user_id.is_not(None))
                    .where(DouyinCreator.user_id != "")
                    .order_by(DouyinCreator.id.asc())
                )
                ids: list[str] = []
                seen: set[str] = set()
                for row in result.all():
                    value = str(row[0]).strip()
                    if value and value not in seen:
                        seen.add(value)
                        ids.append(value)
                return ids
        except Exception as exc:
            utils.logger.exception(
                "[ScheduledTaskService._load_douyin_creator_ids_from_db] failed: %s",
                exc,
            )
            return []
        finally:
            if previous is not None:
                config.SAVE_DATA_OPTION = previous

    async def _resolve_douyin_schedule_creators(self) -> list[str]:
        """
        Prefer env whitelist when set; otherwise use all accounts in douyin_creator.
        DY_SCHEDULE_CREATOR_IDS is optional.
        """
        creators_raw = os.getenv("DY_SCHEDULE_CREATOR_IDS", "").strip()
        creators = [item.strip() for item in creators_raw.split(",") if item.strip()]
        if creators:
            return creators
        return await self._load_douyin_creator_ids_from_db()

    async def ensure_default_douyin_schedule(self) -> None:
        """
        Seed a Douyin multi-slot analytics schedule for Docker/VPS boots.
        Creator list: DY_SCHEDULE_CREATOR_IDS (optional) or douyin_creator table.
        """
        if not _env_flag("AUTO_SEED_DY_SCHEDULE", default=False):
            return

        creators = await self._resolve_douyin_schedule_creators()
        if not creators:
            utils.logger.warning(
                "[ScheduledTaskService.ensure_default_douyin_schedule] "
                "no creators found in DY_SCHEDULE_CREATOR_IDS or douyin_creator; skip seeding"
            )
            return

        run_time = os.getenv("DY_SCHEDULE_RUN_TIME", "09:00,14:00,22:30").strip() or "09:00,14:00,22:30"
        max_pages = int(os.getenv("DY_SCHEDULE_MAX_PAGES", "3") or "3")
        save_option_raw = os.getenv("DY_SCHEDULE_SAVE_OPTION", "postgres").strip() or "postgres"
        task_name = os.getenv("DY_SCHEDULE_TASK_NAME", DEFAULT_DY_SCHEDULE_TASK_NAME).strip() or DEFAULT_DY_SCHEDULE_TASK_NAME

        try:
            _parse_run_times(run_time)
            save_option = SaveDataOptionEnum(save_option_raw)
        except Exception as exc:
            utils.logger.error(
                "[ScheduledTaskService.ensure_default_douyin_schedule] invalid seed config: %s",
                exc,
            )
            return

        async with _get_connection() as db:
            existing = await _fetchone(
                db,
                "SELECT id FROM scheduled_crawl_task WHERE name = ? AND platform = 'dy' LIMIT 1",
                (task_name,),
            )

        payload = ScheduledTaskUpsertRequest(
            name=task_name,
            platform=PlatformEnum.DOUYIN,
            run_time=run_time,
            max_pages=max_pages,
            enable_comments=False,
            enable_sub_comments=False,
            save_option=save_option,
            status="active",
            creators=creators,
        )

        if existing:
            task_id = int(existing["id"])
            await self.update_task(task_id, payload)
            utils.logger.info(
                "[ScheduledTaskService.ensure_default_douyin_schedule] updated task #%s "
                "run_time=%s creators=%s",
                task_id,
                run_time,
                len(creators),
            )
        else:
            created = await self.create_task(payload)
            utils.logger.info(
                "[ScheduledTaskService.ensure_default_douyin_schedule] created task #%s "
                "run_time=%s creators=%s",
                created.get("id"),
                run_time,
                len(creators),
            )

    async def _load_bilibili_creator_ids_from_db(self) -> list[str]:
        """Load monitored UP IDs from Postgres bilibili_up_info."""
        from sqlalchemy import select

        from database.db_session import get_session
        from database.models import BilibiliUpInfo

        save_option = os.getenv("BILI_SCHEDULE_SAVE_OPTION", "").strip() or getattr(
            config, "SAVE_DATA_OPTION", "postgres"
        )
        if save_option not in {"postgres", "db", "mysql", "sqlite"}:
            return []

        previous = getattr(config, "SAVE_DATA_OPTION", None)
        try:
            config.SAVE_DATA_OPTION = save_option
            async with get_session() as session:
                if session is None:
                    return []
                result = await session.execute(
                    select(BilibiliUpInfo.user_id)
                    .where(BilibiliUpInfo.user_id.is_not(None))
                    .order_by(BilibiliUpInfo.id.asc())
                )
                return list(dict.fromkeys(str(row[0]).strip() for row in result.all() if row[0] is not None))
        except Exception as exc:
            utils.logger.exception(
                "[ScheduledTaskService._load_bilibili_creator_ids_from_db] failed: %s",
                exc,
            )
            return []
        finally:
            if previous is not None:
                config.SAVE_DATA_OPTION = previous

    async def _resolve_bilibili_schedule_creators(self) -> list[str]:
        """Prefer BILI_SCHEDULE_CREATOR_IDS; otherwise reuse stored monitored UPs."""
        creators = [
            item.strip()
            for item in os.getenv("BILI_SCHEDULE_CREATOR_IDS", "").split(",")
            if item.strip()
        ]
        return creators or await self._load_bilibili_creator_ids_from_db()

    async def ensure_default_bilibili_schedule(self) -> None:
        """Seed the Bilibili multi-slot snapshot schedule for the Bilibili container."""
        if not _env_flag("AUTO_SEED_BILI_SCHEDULE", default=False):
            return

        creators = await self._resolve_bilibili_schedule_creators()
        if not creators:
            utils.logger.warning(
                "[ScheduledTaskService.ensure_default_bilibili_schedule] "
                "no creators found in BILI_SCHEDULE_CREATOR_IDS or bilibili_up_info; skip seeding"
            )
            return

        run_time = os.getenv("BILI_SCHEDULE_RUN_TIME", "09:00,14:00,22:30").strip() or "09:00,14:00,22:30"
        max_pages = int(os.getenv("BILI_SCHEDULE_MAX_PAGES", "3") or "3")
        save_option_raw = os.getenv("BILI_SCHEDULE_SAVE_OPTION", "postgres").strip() or "postgres"
        task_name = os.getenv("BILI_SCHEDULE_TASK_NAME", DEFAULT_BILI_SCHEDULE_TASK_NAME).strip() or DEFAULT_BILI_SCHEDULE_TASK_NAME

        try:
            _parse_run_times(run_time)
            save_option = SaveDataOptionEnum(save_option_raw)
        except Exception as exc:
            utils.logger.error(
                "[ScheduledTaskService.ensure_default_bilibili_schedule] invalid seed config: %s",
                exc,
            )
            return

        async with _get_connection() as db:
            existing = await _fetchone(
                db,
                "SELECT id FROM scheduled_crawl_task WHERE name = ? AND platform = 'bili' LIMIT 1",
                (task_name,),
            )

        payload = ScheduledTaskUpsertRequest(
            name=task_name,
            platform=PlatformEnum.BILIBILI,
            run_time=run_time,
            max_pages=max_pages,
            enable_comments=False,
            enable_sub_comments=False,
            save_option=save_option,
            status="active",
            creators=creators,
        )
        if existing:
            task_id = int(existing["id"])
            await self.update_task(task_id, payload)
            utils.logger.info(
                "[ScheduledTaskService.ensure_default_bilibili_schedule] updated task #%s run_time=%s creators=%s",
                task_id,
                run_time,
                len(creators),
            )
        else:
            created = await self.create_task(payload)
            utils.logger.info(
                "[ScheduledTaskService.ensure_default_bilibili_schedule] created task #%s run_time=%s creators=%s",
                created.get("id"),
                run_time,
                len(creators),
            )

    async def ensure_default_xhs_schedule(self) -> None:
        """Seed one conservative Xiaohongshu creator snapshot per day."""
        if not _env_flag("AUTO_SEED_XHS_SCHEDULE", default=False):
            return

        creators = [
            item.strip()
            for item in os.getenv("XHS_CREATOR_IDS", "").split(",")
            if item.strip()
        ]
        if not creators:
            utils.logger.warning(
                "[ScheduledTaskService.ensure_default_xhs_schedule] "
                "XHS_CREATOR_IDS is empty; skip seeding"
            )
            return
        if len(creators) > 1:
            utils.logger.warning(
                "[ScheduledTaskService.ensure_default_xhs_schedule] "
                "only the first XHS creator is scheduled to limit account risk"
            )
            creators = creators[:1]

        run_time = os.getenv("XHS_SCHEDULE_RUN_TIME", "10:30").strip() or "10:30"
        task_name = os.getenv("XHS_SCHEDULE_TASK_NAME", DEFAULT_XHS_SCHEDULE_TASK_NAME).strip() or DEFAULT_XHS_SCHEDULE_TASK_NAME
        try:
            if len(_parse_run_times(run_time)) != 1:
                raise ValueError("XHS schedule must contain exactly one daily run time")
        except Exception as exc:
            utils.logger.error(
                "[ScheduledTaskService.ensure_default_xhs_schedule] invalid seed config: %s",
                exc,
            )
            return

        async with _get_connection() as db:
            existing = await _fetchone(
                db,
                "SELECT id FROM scheduled_crawl_task WHERE name = ? AND platform = 'xhs' LIMIT 1",
                (task_name,),
            )

        payload = ScheduledTaskUpsertRequest(
            name=task_name,
            platform=PlatformEnum.XHS,
            run_time=run_time,
            max_pages=1,
            enable_comments=False,
            enable_sub_comments=False,
            save_option=SaveDataOptionEnum.POSTGRES,
            status="active",
            creators=creators,
        )
        if existing:
            task_id = int(existing["id"])
            await self.update_task(task_id, payload)
            utils.logger.info(
                "[ScheduledTaskService.ensure_default_xhs_schedule] updated task #%s run_time=%s",
                task_id,
                run_time,
            )
        else:
            created = await self.create_task(payload)
            utils.logger.info(
                "[ScheduledTaskService.ensure_default_xhs_schedule] created task #%s run_time=%s",
                created.get("id"),
                run_time,
            )

    async def _load_gzh_account_ids_from_db(self) -> list[str]:
        from sqlalchemy import select

        from database.db_session import get_session
        from database.models import GzhAccount

        try:
            async with get_session() as session:
                result = await session.execute(
                    select(GzhAccount.account_id).order_by(GzhAccount.id.asc())
                )
                rows = result.scalars().all()
            return [str(item).strip() for item in rows if str(item).strip()]
        except Exception as exc:
            utils.logger.warning(
                "[ScheduledTaskService._load_gzh_account_ids_from_db] failed: %s",
                exc,
            )
            return []

    async def ensure_default_gzh_schedule(self) -> None:
        """Seed one daily WeChat official-account stats refresh task."""
        if not _env_flag("AUTO_SEED_GZH_SCHEDULE", default=False):
            return

        creators = [
            item.strip()
            for item in os.getenv("GZH_ACCOUNT_IDS", "").split(",")
            if item.strip()
        ]
        if not creators:
            creators = await self._load_gzh_account_ids_from_db()
        if not creators:
            utils.logger.warning(
                "[ScheduledTaskService.ensure_default_gzh_schedule] "
                "no GZH_ACCOUNT_IDS / gzh_account rows; skip seeding"
            )
            return

        run_time = os.getenv("GZH_SCHEDULE_RUN_TIME", "11:00").strip() or "11:00"
        task_name = (
            os.getenv("GZH_SCHEDULE_TASK_NAME", DEFAULT_GZH_SCHEDULE_TASK_NAME).strip()
            or DEFAULT_GZH_SCHEDULE_TASK_NAME
        )
        try:
            _parse_run_times(run_time)
        except Exception as exc:
            utils.logger.error(
                "[ScheduledTaskService.ensure_default_gzh_schedule] invalid seed config: %s",
                exc,
            )
            return

        async with _get_connection() as db:
            existing = await _fetchone(
                db,
                "SELECT id FROM scheduled_crawl_task WHERE name = ? AND platform = 'gzh' LIMIT 1",
                (task_name,),
            )

        payload = ScheduledTaskUpsertRequest(
            name=task_name,
            platform=PlatformEnum.GZH,
            run_time=run_time,
            max_pages=1,
            enable_comments=False,
            enable_sub_comments=False,
            save_option=SaveDataOptionEnum.POSTGRES,
            status="active",
            creators=creators,
        )
        if existing:
            task_id = int(existing["id"])
            await self.update_task(task_id, payload)
            utils.logger.info(
                "[ScheduledTaskService.ensure_default_gzh_schedule] updated task #%s run_time=%s creators=%s",
                task_id,
                run_time,
                len(creators),
            )
        else:
            created = await self.create_task(payload)
            utils.logger.info(
                "[ScheduledTaskService.ensure_default_gzh_schedule] created task #%s run_time=%s creators=%s",
                created.get("id"),
                run_time,
                len(creators),
            )

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
                slot = _slot_from_hhmm(next_run.hour, next_run.minute)
                await self._queue.put(
                    RunRequest(
                        task_id=task_id,
                        trigger_type="schedule",
                        scheduled_slot=slot,
                        scheduled_hhmm=_format_hhmm(next_run.hour, next_run.minute),
                    )
                )
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
        _parse_run_times(payload.run_time)
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
        _parse_run_times(payload.run_time)
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
                    await self._execute_task_run(
                        request.task_id,
                        request.trigger_type,
                        scheduled_slot=request.scheduled_slot,
                    )
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

    async def _execute_task_run(
        self,
        task_id: int,
        trigger_type: str,
        scheduled_slot: str = "manual",
    ) -> None:
        task = await self.get_task(task_id)
        # Auto platform tasks refresh their creator list from the primary table when no whitelist is set.
        task_name = os.getenv("DY_SCHEDULE_TASK_NAME", DEFAULT_DY_SCHEDULE_TASK_NAME).strip() or DEFAULT_DY_SCHEDULE_TASK_NAME
        if (
            task.get("platform") == "dy"
            and task.get("name") == task_name
            and _env_flag("DY_SCHEDULE_SYNC_FROM_DB", default=True)
            and not os.getenv("DY_SCHEDULE_CREATOR_IDS", "").strip()
        ):
            creators = await self._load_douyin_creator_ids_from_db()
            if creators:
                await self.update_task(
                    task_id,
                    ScheduledTaskUpsertRequest(
                        name=task["name"],
                        platform=PlatformEnum.DOUYIN,
                        run_time=task["run_time"],
                        max_pages=task["max_pages"],
                        enable_comments=task["enable_comments"],
                        enable_sub_comments=task["enable_sub_comments"],
                        save_option=SaveDataOptionEnum(task["save_option"]),
                        status=task["status"],
                        creators=creators,
                    ),
                )
                task = await self.get_task(task_id)
                utils.logger.info(
                    "[ScheduledTaskService._execute_task_run] synced %s creators from douyin_creator",
                    len(creators),
                )

        bili_task_name = os.getenv("BILI_SCHEDULE_TASK_NAME", DEFAULT_BILI_SCHEDULE_TASK_NAME).strip() or DEFAULT_BILI_SCHEDULE_TASK_NAME
        if (
            task.get("platform") == "bili"
            and task.get("name") == bili_task_name
            and _env_flag("BILI_SCHEDULE_SYNC_FROM_DB", default=True)
            and not os.getenv("BILI_SCHEDULE_CREATOR_IDS", "").strip()
        ):
            creators = await self._load_bilibili_creator_ids_from_db()
            if creators:
                await self.update_task(
                    task_id,
                    ScheduledTaskUpsertRequest(
                        name=task["name"],
                        platform=PlatformEnum.BILIBILI,
                        run_time=task["run_time"],
                        max_pages=task["max_pages"],
                        enable_comments=task["enable_comments"],
                        enable_sub_comments=task["enable_sub_comments"],
                        save_option=SaveDataOptionEnum(task["save_option"]),
                        status=task["status"],
                        creators=creators,
                    ),
                )
                task = await self.get_task(task_id)
                utils.logger.info(
                    "[ScheduledTaskService._execute_task_run] synced %s creators from bilibili_up_info",
                    len(creators),
                )

        started_at = _now_iso()
        slot = scheduled_slot or "manual"
        if trigger_type == "manual":
            slot = "manual"
        async with _get_connection() as db:
            cursor = await db.execute(
                """
                INSERT INTO scheduled_crawl_run (
                    task_id, status, trigger_type, scheduled_slot, started_at, finished_at, error_message, created_at
                ) VALUES (?, 'running', ?, ?, ?, '', '', ?)
                """,
                (task_id, trigger_type, slot, started_at, started_at),
            )
            run_id = cursor.lastrowid
            await db.execute(
                "UPDATE scheduled_crawl_task SET last_run_at = ?, updated_at = ? WHERE id = ?",
                (started_at, started_at, task_id),
            )

        results = []
        for creator in task["creators"]:
            result = await self._execute_creator_run(
                task=task,
                creator=creator,
                run_id=run_id,
                scheduled_slot=slot,
            )
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
        scheduled_slot: str = "manual",
    ) -> dict[str, Any]:
        started_at = _now_iso()
        effective_creator_arg = creator["raw_input"]
        forced_partial = False
        preflight_error = ""
        pages_fetched = 0
        items_before = await self._count_creator_items(task["platform"], creator)

        if task["platform"] != "xhs":
            effective_creator_arg = creator["normalized_creator_id"]

        while crawler_manager.process and crawler_manager.process.poll() is None:
            await asyncio.sleep(0.2)

        save_option = SaveDataOptionEnum(task["save_option"])
        # Bilibili snapshots share the same schedule slots as Douyin trend snapshots.
        slot = scheduled_slot if task["platform"] in {"dy", "bili"} else "manual"
        use_pure_api = task["platform"] == "xhs" or _scheduled_crawl_use_pure_api()
        request = CrawlerStartRequest(
            platform=PlatformEnum(task["platform"]),
            login_type=LoginTypeEnum.COOKIE if task["platform"] == "xhs" else LoginTypeEnum.QRCODE,
            crawler_type=CrawlerTypeEnum.CREATOR,
            creator_ids=effective_creator_arg,
            enable_comments=task["enable_comments"],
            enable_sub_comments=task["enable_sub_comments"],
            save_option=save_option,
            headless=task["platform"] == "xhs",
            max_pages=task["max_pages"],
            cdp_attach_only=task["platform"] != "xhs" and not use_pure_api,
            pure_api=use_pure_api,
            scheduled_slot=slot,
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

scheduled_task_service = ScheduledTaskService()
