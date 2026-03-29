# -*- coding: utf-8 -*-
#
# This file is part of MediaCrawler project.

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from .service import (
    DEFAULT_PAGE,
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    get_options,
    get_record_detail,
    list_records,
)

router = APIRouter(tags=["sqlite-viewer"])

STATIC_DIR = Path(__file__).resolve().parent / "static"
INDEX_FILE = STATIC_DIR / "index.html"


@router.get("/sqlite-viewer")
@router.get("/sqlite-viewer/")
async def serve_sqlite_viewer():
    if not INDEX_FILE.exists():
        raise HTTPException(status_code=404, detail="SQLite viewer page not found")
    return FileResponse(INDEX_FILE)


@router.get("/api/sqlite-viewer/options")
async def sqlite_viewer_options():
    return await get_options()


@router.get("/api/sqlite-viewer/list")
async def sqlite_viewer_list(
    platform: str = Query(default="all"),
    entity_type: str = Query(default="content"),
    time_filter: str = Query(default="all"),
    author_query: str | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    page: int = Query(default=DEFAULT_PAGE, ge=1),
    page_size: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
):
    try:
        return await list_records(
            platform=platform,
            entity_type=entity_type,
            time_filter=time_filter,
            author_query=author_query,
            start_date=start_date,
            end_date=end_date,
            page=page,
            page_size=page_size,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/sqlite-viewer/detail/{entity_type}/{platform}/{record_pk}")
async def sqlite_viewer_detail(entity_type: str, platform: str, record_pk: str):
    try:
        return await get_record_detail(platform=platform, entity_type=entity_type, record_pk=record_pk)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
