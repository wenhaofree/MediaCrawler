# -*- coding: utf-8 -*-
#
# This file is part of MediaCrawler project.

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from api.schemas import ScheduledTaskUpsertRequest

from .service import scheduled_task_service


router = APIRouter(tags=["scheduled-tasks"])
STATIC_DIR = Path(__file__).resolve().parent / "static"
INDEX_FILE = STATIC_DIR / "index.html"


@router.get("/schedule-tasks")
async def serve_schedule_tasks_page():
    if not INDEX_FILE.exists():
        raise HTTPException(status_code=404, detail="Schedule tasks page not found")
    return FileResponse(INDEX_FILE)


@router.get("/api/scheduled-tasks")
async def list_scheduled_tasks():
    return await scheduled_task_service.list_tasks()


@router.post("/api/scheduled-tasks")
async def create_scheduled_task(request: ScheduledTaskUpsertRequest):
    try:
        return await scheduled_task_service.create_task(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/scheduled-tasks/cdp-status")
async def get_scheduled_task_cdp_status():
    return await scheduled_task_service.get_cdp_status()


@router.get("/api/scheduled-tasks/{task_id}")
async def get_scheduled_task(task_id: int):
    try:
        return await scheduled_task_service.get_task(task_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/api/scheduled-tasks/{task_id}")
async def update_scheduled_task(task_id: int, request: ScheduledTaskUpsertRequest):
    try:
        return await scheduled_task_service.update_task(task_id, request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/api/scheduled-tasks/{task_id}")
async def delete_scheduled_task(task_id: int):
    try:
        await scheduled_task_service.delete_task(task_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "ok"}


@router.post("/api/scheduled-tasks/{task_id}/run")
async def run_scheduled_task_now(task_id: int):
    try:
        return await scheduled_task_service.run_task_now(task_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/api/scheduled-tasks/{task_id}/runs")
async def list_scheduled_task_runs(task_id: int):
    try:
        return await scheduled_task_service.list_runs(task_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
