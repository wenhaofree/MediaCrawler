# -*- coding: utf-8 -*-
#
# This file is part of MediaCrawler project.

from __future__ import annotations

import hashlib
import hmac
import os
import time
from pathlib import Path
from typing import Optional

from dotenv import dotenv_values
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from database.config_store import (
    PLATFORM_COOKIE_SPECS,
    clear_platform_cookie,
    list_platform_cookie_statuses,
    probe_platform_cookie,
    save_platform_cookie,
)

router = APIRouter(tags=["cookie-config"])
STATIC_DIR = Path(__file__).resolve().parent / "static"
INDEX_FILE = STATIC_DIR / "index.html"
SESSION_COOKIE_NAME = "mc_cookie_admin"
SESSION_TTL_SECONDS = 86400


class LoginRequest(BaseModel):
    password: str = Field(..., min_length=1, description="Cookie 管理页访问密码")


class UpdateCookieRequest(BaseModel):
    cookie: str = Field(..., min_length=1, description="新的 Cookie 字符串")
    probe: bool = Field(default=True, description="保存后是否立即探测有效性")


def _configured_admin_password() -> str:
    val = os.getenv("COOKIE_ADMIN_PASSWORD")
    if val is None:
        try:
            val = str(dotenv_values().get("COOKIE_ADMIN_PASSWORD") or "")
        except Exception:
            val = ""
    return (val or "").strip()


def _signing_key(password: str) -> bytes:
    return hashlib.sha256(f"mc-cookie-admin:{password}".encode("utf-8")).digest()


def _make_session_token(password: str, ttl_seconds: int = SESSION_TTL_SECONDS) -> str:
    exp = int(time.time()) + ttl_seconds
    sig = hmac.new(_signing_key(password), str(exp).encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{exp}.{sig}"


def _verify_session_token(token: Optional[str], password: str) -> bool:
    if not token or not password or "." not in token:
        return False
    exp_str, sig = token.split(".", 1)
    try:
        exp = int(exp_str)
    except ValueError:
        return False
    if exp < int(time.time()):
        return False
    expected = hmac.new(_signing_key(password), exp_str.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, expected)


def _is_authenticated(request: Request, password: str) -> bool:
    if not password:
        return False
    header_pw = (request.headers.get("X-Admin-Password") or "").strip()
    if header_pw and hmac.compare_digest(header_pw, password):
        return True
    token = request.cookies.get(SESSION_COOKIE_NAME)
    return _verify_session_token(token, password)


def _require_auth(request: Request) -> None:
    password = _configured_admin_password()
    if not password:
        raise HTTPException(
            status_code=503,
            detail="未配置 COOKIE_ADMIN_PASSWORD，请在 .env 中设置管理密码后再访问",
        )
    if not _is_authenticated(request, password):
        raise HTTPException(status_code=401, detail="请先输入管理密码登录")


@router.get("/cookie-config")
async def serve_cookie_config_page():
    if not INDEX_FILE.exists():
        raise HTTPException(status_code=404, detail="Cookie config page not found")
    return FileResponse(INDEX_FILE)


@router.get("/api/cookie-config/auth/status")
async def cookie_config_auth_status(request: Request):
    password = _configured_admin_password()
    return {
        "password_configured": bool(password),
        "authenticated": _is_authenticated(request, password),
    }


@router.post("/api/cookie-config/auth/login")
async def cookie_config_login(payload: LoginRequest, response: Response):
    password = _configured_admin_password()
    if not password:
        raise HTTPException(
            status_code=503,
            detail="未配置 COOKIE_ADMIN_PASSWORD，请在 .env 中设置管理密码后再登录",
        )
    if not hmac.compare_digest(payload.password.strip(), password):
        raise HTTPException(status_code=401, detail="管理密码错误")

    token = _make_session_token(password)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        samesite="lax",
    )
    return {"authenticated": True}


@router.post("/api/cookie-config/auth/logout")
async def cookie_config_logout(response: Response):
    response.delete_cookie(key=SESSION_COOKIE_NAME, samesite="lax")
    return {"authenticated": False}


@router.get("/api/cookie-config")
async def get_cookie_configs(request: Request):
    _require_auth(request)
    items = await list_platform_cookie_statuses()
    return {"items": items}


@router.put("/api/cookie-config/{platform}")
async def update_cookie_config(
    platform: str,
    payload: UpdateCookieRequest,
    request: Request,
):
    _require_auth(request)
    if platform not in PLATFORM_COOKIE_SPECS:
        raise HTTPException(status_code=404, detail=f"Unsupported platform: {platform}")
    try:
        item = await save_platform_cookie(
            platform,
            payload.cookie,
            run_probe=payload.probe,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"保存 Cookie 失败: {exc}") from exc
    return {"item": item}


@router.post("/api/cookie-config/{platform}/check")
async def check_cookie_config(platform: str, request: Request):
    _require_auth(request)
    if platform not in PLATFORM_COOKIE_SPECS:
        raise HTTPException(status_code=404, detail=f"Unsupported platform: {platform}")
    result = await probe_platform_cookie(platform)
    items = await list_platform_cookie_statuses()
    matched = next((entry for entry in items if entry["platform"] == platform), None)
    return {"result": result, "item": matched}


@router.delete("/api/cookie-config/{platform}")
async def delete_cookie_override(platform: str, request: Request):
    _require_auth(request)
    if platform not in PLATFORM_COOKIE_SPECS:
        raise HTTPException(status_code=404, detail=f"Unsupported platform: {platform}")
    item = await clear_platform_cookie(platform)
    return {"item": item}
