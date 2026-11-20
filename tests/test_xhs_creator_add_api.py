# -*- coding: utf-8 -*-
from __future__ import annotations

import pytest

from api.routers import xhs as xhs_api


def test_looks_like_xhs_cookies():
    assert xhs_api._looks_like_xhs_cookies("a1=abc; webId=1")
    assert xhs_api._looks_like_xhs_cookies("web_session=xyz")
    assert not xhs_api._looks_like_xhs_cookies("SESSDATA=bili")


def test_resolve_xhs_cookies_priority(monkeypatch, tmp_path):
    missing_secret = tmp_path / "missing_secret"
    missing_runtime = tmp_path / "missing_runtime"
    monkeypatch.setattr("media_platform.xhs.cookies._reload_dotenv", lambda: None)
    monkeypatch.setenv("XHS_COOKIES_FILE", str(missing_secret))
    monkeypatch.setenv("XHS_COOKIES_RUNTIME_FILE", str(missing_runtime))
    monkeypatch.setenv("XHS_COOKIES", "a1=from-config")
    monkeypatch.setattr(xhs_api.config, "XHS_COOKIES", "a1=from-config", raising=False)
    monkeypatch.setattr(xhs_api.config, "COOKIES", "a1=fallback", raising=False)

    assert xhs_api._resolve_xhs_cookies("a1=from-request") == "a1=from-request"
    assert xhs_api._resolve_xhs_cookies(None) == "a1=from-config"

    monkeypatch.setenv("XHS_COOKIES", "")
    monkeypatch.setattr(xhs_api.config, "XHS_COOKIES", "", raising=False)
    monkeypatch.delenv("CRAWLER_COOKIES", raising=False)
    assert xhs_api._resolve_xhs_cookies(None) == "a1=fallback"

    monkeypatch.setattr(xhs_api.config, "COOKIES", "SESSDATA=wrong-platform", raising=False)
    assert xhs_api._resolve_xhs_cookies(None) == ""


@pytest.mark.asyncio
async def test_add_xhs_creator_rejects_missing_cookies(monkeypatch, tmp_path):
    monkeypatch.setattr("media_platform.xhs.cookies._reload_dotenv", lambda: None)
    monkeypatch.setattr(xhs_api.config, "XHS_COOKIES", "", raising=False)
    monkeypatch.setattr(xhs_api.config, "COOKIES", "", raising=False)
    monkeypatch.setenv("XHS_COOKIES", "")
    monkeypatch.delenv("CRAWLER_COOKIES", raising=False)
    monkeypatch.setenv("XHS_COOKIES_FILE", str(tmp_path / "no_secret"))
    monkeypatch.setenv("XHS_COOKIES_RUNTIME_FILE", str(tmp_path / "no_runtime"))

    with pytest.raises(xhs_api.HTTPException) as exc:
        await xhs_api.add_xhs_creator(
            xhs_api.AddCreatorRequest(url="5eb8e1d400000000010075ae")
        )
    assert exc.value.status_code == 400
