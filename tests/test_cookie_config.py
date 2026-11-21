# -*- coding: utf-8 -*-
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool

import config
from api.main import app
from database import config_store, db_session
from database.models import Base


async def _noop_async(*_args, **_kwargs):
    return None


@pytest.fixture
def isolated_cookie_db(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
    monkeypatch.setattr(db_session, "get_async_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr(config_store, "get_async_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr(config, "SAVE_DATA_OPTION", "db")
    monkeypatch.setenv("SAVE_DATA_OPTION", "db")
    monkeypatch.setattr("api.main.ensure_app_config_table", _noop_async)
    monkeypatch.setattr("api.main.scheduled_task_service.start", _noop_async)
    monkeypatch.setattr("api.main.scheduled_task_service.shutdown", _noop_async)
    return engine


def test_cookie_config_page_renders(monkeypatch):
    monkeypatch.setattr("api.main.ensure_app_config_table", _noop_async)
    monkeypatch.setattr("api.main.scheduled_task_service.start", _noop_async)
    monkeypatch.setattr("api.main.scheduled_task_service.shutdown", _noop_async)

    client = TestClient(app)
    resp = client.get("/cookie-config")
    assert resp.status_code == 200
    assert "平台 Cookie 配置中心" in resp.text


def test_cookie_config_requires_password_configured_and_login(isolated_cookie_db, monkeypatch):
    monkeypatch.setenv("COOKIE_ADMIN_PASSWORD", "")
    client = TestClient(app)

    status_resp = client.get("/api/cookie-config/auth/status")
    assert status_resp.status_code == 200
    assert status_resp.json() == {"password_configured": False, "authenticated": False}

    denied_resp = client.get("/api/cookie-config")
    assert denied_resp.status_code == 503

    monkeypatch.setenv("COOKIE_ADMIN_PASSWORD", "secret-pass-123")
    assert client.get("/api/cookie-config").status_code == 401
    assert (
        client.post("/api/cookie-config/auth/login", json={"password": "wrong"}).status_code
        == 401
    )

    login_resp = client.post(
        "/api/cookie-config/auth/login", json={"password": "secret-pass-123"}
    )
    assert login_resp.status_code == 200
    assert login_resp.json() == {"authenticated": True}
    assert "mc_cookie_admin" in login_resp.cookies


@pytest.mark.asyncio
async def test_cookie_config_crud_priority_and_masking(isolated_cookie_db, monkeypatch, tmp_path):
    async with isolated_cookie_db.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    monkeypatch.setenv("COOKIE_ADMIN_PASSWORD", "admin-pass")
    monkeypatch.setenv("BILI_COOKIES", "SESSDATA=env_secret_value_123456; DedeUserID=1")
    monkeypatch.setenv("XHS_COOKIES_RUNTIME_FILE", str(tmp_path / "xhs_runtime"))

    client = TestClient(app)
    login = client.post("/api/cookie-config/auth/login", json={"password": "admin-pass"})
    assert login.status_code == 200

    # Initially falls back to env without leaking full cookie string
    list_resp = client.get("/api/cookie-config")
    assert list_resp.status_code == 200
    items = {item["platform"]: item for item in list_resp.json()["items"]}
    assert items["bili"]["source"] == "env:BILI_COOKIES"
    assert "env_secret_value_123456" not in list_resp.text
    assert items["bili"]["masked_cookie"].startswith("SESSDATA")

    # Save DB override with probe mocked
    async def fake_probe(platform, cookie_override=None):
        return {
            "valid": True,
            "status": "valid",
            "message": f"{platform} ok",
            "checked_at": "2026-11-21T15:40:00+08:00",
            "source": "database",
        }

    monkeypatch.setattr(config_store, "probe_platform_cookie", fake_probe)

    new_bili_cookie = "SESSDATA=db_override_cookie_999999; bili_jct=abc; DedeUserID=20813884"
    put_resp = client.put(
        "/api/cookie-config/bili",
        json={"cookie": new_bili_cookie, "probe": True},
    )
    assert put_resp.status_code == 200
    item = put_resp.json()["item"]
    assert item["source"] == "database"
    assert item["has_db_override"] is True
    assert item["status"] == "valid"
    assert "db_override_cookie_999999" not in put_resp.text

    # DB value wins over env
    assert await config_store.resolve_platform_cookie("bili") == new_bili_cookie
    assert await config_store.resolve_platform_cookie("bili", explicit="SESSDATA=req") == "SESSDATA=req"

    # apply_db_cookie_to_config populates config.COOKIES for crawler subprocesses
    monkeypatch.setattr(config, "COOKIES", "old")
    await config_store.apply_db_cookie_to_config("bili")
    assert config.COOKIES == new_bili_cookie

    # sync_refreshed_cookie_to_db updates existing DB override for xhs
    await config_store.save_platform_cookie(
        "xhs", "a1=initial_xhs; web_session=old_sess", run_probe=False
    )
    await config_store.sync_refreshed_cookie_to_db(
        "xhs", "a1=initial_xhs; web_session=rotated_sess"
    )
    assert await config_store.get_db_cookie("xhs") == "a1=initial_xhs; web_session=rotated_sess"

    # Clearing DB override falls back to env
    del_resp = client.delete("/api/cookie-config/bili")
    assert del_resp.status_code == 200
    assert del_resp.json()["item"]["source"] == "env:BILI_COOKIES"
    assert await config_store.get_db_cookie("bili") == ""

    await isolated_cookie_db.dispose()
