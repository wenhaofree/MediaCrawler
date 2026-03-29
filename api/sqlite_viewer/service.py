# -*- coding: utf-8 -*-
#
# This file is part of MediaCrawler project.

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from math import ceil
from pathlib import Path
from typing import Any, AsyncIterator, Dict, Iterable, List, Set
from zoneinfo import ZoneInfo

import aiosqlite

from config import db_config

from .registry import (
    ENTITY_TYPE_LABELS,
    PLATFORM_LABELS,
    SUPPORTED_ENTITY_TYPES,
    SUPPORTED_PLATFORMS,
    ViewerTableConfig,
    get_config,
    get_configs,
    validate_entity_type,
    validate_platform,
)

SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")
DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
SUPPORTED_TIME_FILTERS = ("all", "today", "week", "custom")


def get_sqlite_db_path() -> Path:
    return Path(db_config.SQLITE_DB_PATH)


def _now_in_shanghai() -> datetime:
    return datetime.now(tz=SHANGHAI_TZ)


@asynccontextmanager
async def _get_connection() -> AsyncIterator[aiosqlite.Connection]:
    async with aiosqlite.connect(get_sqlite_db_path()) as db:
        db.row_factory = aiosqlite.Row
        yield db


async def _get_existing_tables(db: aiosqlite.Connection) -> Set[str]:
    cursor = await db.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    rows = await cursor.fetchall()
    return {row[0] for row in rows}


def _list_select_sql(config: ViewerTableConfig) -> str:
    return f"""
        SELECT
            '{config.platform}' AS platform,
            '{config.entity_type}' AS entity_type,
            '{config.table_name}' AS table_name,
            CAST({config.pk_field} AS TEXT) AS record_pk,
            COALESCE(CAST({config.source_id_expr} AS TEXT), '') AS source_id,
            COALESCE({config.title_expr}, '') AS title,
            COALESCE({config.summary_expr}, '') AS summary,
            COALESCE({config.author_expr}, '') AS author_name,
            COALESCE({config.avatar_expr}, '') AS avatar_url,
            COALESCE(CAST({config.publish_raw_expr} AS TEXT), '') AS publish_raw,
            COALESCE(CAST({config.sort_ts_expr} AS INTEGER), 0) AS sort_ts,
            COALESCE({config.external_url_expr}, '') AS external_url,
            {config.stats_json_expr} AS stats_json,
            COALESCE({config.raw_preview_expr}, '') AS raw_preview
        FROM {config.table_name}
    """


def _format_timestamp(ts_value: Any) -> str:
    try:
        ts_int = int(ts_value or 0)
    except (TypeError, ValueError):
        return ""

    if ts_int <= 0:
        return ""

    # Some crawlers may store ms timestamps in the future.
    if ts_int > 10_000_000_000:
        ts_int = ts_int // 1000

    return datetime.fromtimestamp(ts_int, tz=SHANGHAI_TZ).strftime("%Y-%m-%d %H:%M:%S")


def _safe_stats(stats_json: str | None) -> Dict[str, Any]:
    if not stats_json:
        return {}
    try:
        stats = json.loads(stats_json)
    except json.JSONDecodeError:
        return {}
    return {key: value for key, value in stats.items() if value not in (None, "", [])}


def _parse_date_start(date_text: str, field_name: str) -> datetime:
    try:
        return datetime.strptime(date_text, "%Y-%m-%d").replace(tzinfo=SHANGHAI_TZ)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be in YYYY-MM-DD format") from exc


def _build_time_filter(time_filter: str, start_date: str | None, end_date: str | None) -> Dict[str, Any]:
    if time_filter not in SUPPORTED_TIME_FILTERS:
        raise ValueError(
            f"time_filter must be one of: {', '.join(SUPPORTED_TIME_FILTERS)}"
        )

    start_dt: datetime | None = None
    end_dt: datetime | None = None
    normalized_start = ""
    normalized_end = ""

    if time_filter == "today":
        today_start = _now_in_shanghai().replace(hour=0, minute=0, second=0, microsecond=0)
        start_dt = today_start
        end_dt = today_start + timedelta(days=1)
    elif time_filter == "week":
        today_start = _now_in_shanghai().replace(hour=0, minute=0, second=0, microsecond=0)
        start_dt = today_start - timedelta(days=6)
        end_dt = today_start + timedelta(days=1)
    elif time_filter == "custom":
        parsed_start = _parse_date_start(start_date, "start_date") if start_date else None
        parsed_end = _parse_date_start(end_date, "end_date") if end_date else None
        if not parsed_start and not parsed_end:
            raise ValueError("Custom time filter requires start_date or end_date")
        if parsed_start and parsed_end and parsed_start > parsed_end:
            raise ValueError("start_date cannot be later than end_date")

        start_dt = parsed_start
        end_dt = parsed_end + timedelta(days=1) if parsed_end else None
        normalized_start = start_date or ""
        normalized_end = end_date or ""

    clauses: List[str] = []
    params: List[int] = []
    if start_dt is not None:
        clauses.append("sort_ts >= ?")
        params.append(int(start_dt.timestamp()))
    if end_dt is not None:
        clauses.append("sort_ts < ?")
        params.append(int(end_dt.timestamp()))

    return {
        "time_filter": time_filter,
        "start_date": normalized_start,
        "end_date": normalized_end,
        "clauses": clauses,
        "params": params,
    }


def _build_author_filter(author_query: str | None) -> Dict[str, Any]:
    normalized_author_query = (author_query or "").strip()
    if not normalized_author_query:
        return {
            "author_query": "",
            "clauses": [],
            "params": [],
        }

    return {
        "author_query": normalized_author_query,
        "clauses": ["author_name LIKE ?"],
        "params": [f"%{normalized_author_query}%"],
    }


def _normalize_list_row(row: aiosqlite.Row) -> Dict[str, Any]:
    row_data = dict(row)
    return {
        "platform": row_data["platform"],
        "entity_type": row_data["entity_type"],
        "table_name": row_data["table_name"],
        "record_pk": row_data["record_pk"],
        "source_id": row_data["source_id"],
        "title": row_data["title"] or row_data["source_id"] or "-",
        "summary": row_data["summary"] or "",
        "author_name": row_data["author_name"] or "-",
        "avatar_url": row_data["avatar_url"] or "",
        "publish_time_display": _format_timestamp(row_data["sort_ts"]),
        "sort_ts": int(row_data["sort_ts"] or 0),
        "external_url": row_data["external_url"] or "",
        "stats": _safe_stats(row_data.get("stats_json")),
        "raw_preview": row_data["raw_preview"] or row_data["summary"] or "",
    }


def _raw_to_json_ready(raw_row: Dict[str, Any]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for key, value in raw_row.items():
        if isinstance(value, bytes):
            result[key] = value.decode("utf-8", errors="ignore")
        else:
            result[key] = value
    return result


async def get_options() -> Dict[str, Any]:
    async with _get_connection() as db:
        existing_tables = await _get_existing_tables(db)
        counts_by_platform: Dict[str, Dict[str, int]] = {
            platform: {entity_type: 0 for entity_type in SUPPORTED_ENTITY_TYPES}
            for platform in SUPPORTED_PLATFORMS
        }

        for platform in SUPPORTED_PLATFORMS:
            for entity_type in SUPPORTED_ENTITY_TYPES:
                config = get_config(platform, entity_type)
                if config.table_name not in existing_tables:
                    continue
                cursor = await db.execute(f"SELECT COUNT(1) FROM {config.table_name}")
                counts_by_platform[platform][entity_type] = int((await cursor.fetchone())[0])

        entity_type_totals = {
            entity_type: sum(counts_by_platform[platform][entity_type] for platform in SUPPORTED_PLATFORMS)
            for entity_type in SUPPORTED_ENTITY_TYPES
        }
        platform_totals = {
            platform: sum(counts_by_platform[platform].values())
            for platform in SUPPORTED_PLATFORMS
        }

        return {
            "platforms": [
                {
                    "value": "all",
                    "label": PLATFORM_LABELS["all"],
                    "count": sum(platform_totals.values()),
                },
                *[
                    {
                        "value": platform,
                        "label": PLATFORM_LABELS[platform],
                        "count": platform_totals[platform],
                    }
                    for platform in SUPPORTED_PLATFORMS
                ],
            ],
            "entity_types": [
                {
                    "value": entity_type,
                    "label": ENTITY_TYPE_LABELS[entity_type],
                    "count": entity_type_totals[entity_type],
                }
                for entity_type in SUPPORTED_ENTITY_TYPES
            ],
            "counts": counts_by_platform,
        }


def _build_union_sql(configs: Iterable[ViewerTableConfig], existing_tables: Set[str]) -> str:
    queries = [_list_select_sql(config) for config in configs if config.table_name in existing_tables]
    if not queries:
        return ""
    return "\nUNION ALL\n".join(queries)


async def list_records(
    platform: str,
    entity_type: str,
    time_filter: str = "all",
    author_query: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    page: int = DEFAULT_PAGE,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> Dict[str, Any]:
    validate_platform(platform)
    validate_entity_type(entity_type)
    time_filter_payload = _build_time_filter(time_filter, start_date, end_date)
    author_filter_payload = _build_author_filter(author_query)

    page = max(1, page)
    page_size = max(1, min(page_size, MAX_PAGE_SIZE))
    offset = (page - 1) * page_size

    async with _get_connection() as db:
        existing_tables = await _get_existing_tables(db)
        configs = get_configs(platform, entity_type)
        union_sql = _build_union_sql(configs, existing_tables)

        if not union_sql:
            return {
                "platform": platform,
                "entity_type": entity_type,
                "items": [],
                "time_filter": time_filter_payload["time_filter"],
                "author_query": author_filter_payload["author_query"],
                "start_date": time_filter_payload["start_date"],
                "end_date": time_filter_payload["end_date"],
                "page": page,
                "page_size": page_size,
                "total": 0,
                "total_pages": 0,
            }
        filter_clauses = [*time_filter_payload["clauses"], *author_filter_payload["clauses"]]
        filter_params = [*time_filter_payload["params"], *author_filter_payload["params"]]
        where_clause = f" WHERE {' AND '.join(filter_clauses)}" if filter_clauses else ""
        filtered_union_sql = f"FROM ({union_sql}) AS combined{where_clause}"
        count_cursor = await db.execute(
            f"SELECT COUNT(1) AS total {filtered_union_sql}",
            tuple(filter_params),
        )
        total = int((await count_cursor.fetchone())["total"])

        list_sql = (
            f"SELECT * {filtered_union_sql} "
            "ORDER BY sort_ts DESC, record_pk DESC "
            "LIMIT ? OFFSET ?"
        )
        list_cursor = await db.execute(
            list_sql,
            tuple([*filter_params, page_size, offset]),
        )
        rows = await list_cursor.fetchall()

        return {
            "platform": platform,
            "entity_type": entity_type,
            "items": [_normalize_list_row(row) for row in rows],
            "time_filter": time_filter_payload["time_filter"],
            "author_query": author_filter_payload["author_query"],
            "start_date": time_filter_payload["start_date"],
            "end_date": time_filter_payload["end_date"],
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": ceil(total / page_size) if total else 0,
        }


async def get_record_detail(platform: str, entity_type: str, record_pk: str) -> Dict[str, Any]:
    validate_platform(platform)
    validate_entity_type(entity_type)
    if platform == "all":
        raise ValueError("Detail lookup requires a specific platform")

    config = get_config(platform, entity_type)

    async with _get_connection() as db:
        existing_tables = await _get_existing_tables(db)
        if config.table_name not in existing_tables:
            raise LookupError("Table not found")

        normalized_sql = f"{_list_select_sql(config)} WHERE {config.pk_field} = ? LIMIT 1"
        normalized_cursor = await db.execute(normalized_sql, (record_pk,))
        normalized_row = await normalized_cursor.fetchone()
        if normalized_row is None:
            raise LookupError("Record not found")

        raw_cursor = await db.execute(
            f"SELECT * FROM {config.table_name} WHERE {config.pk_field} = ? LIMIT 1",
            (record_pk,),
        )
        raw_row = await raw_cursor.fetchone()
        if raw_row is None:
            raise LookupError("Record not found")

        raw_payload = _raw_to_json_ready(dict(raw_row))
        normalized_payload = _normalize_list_row(normalized_row)

        return {
            "platform": platform,
            "entity_type": entity_type,
            "table_name": config.table_name,
            "record_pk": record_pk,
            "normalized": normalized_payload,
            "raw": raw_payload,
            "raw_json": json.dumps(raw_payload, ensure_ascii=False, indent=2),
        }
