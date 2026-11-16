# -*- coding: utf-8 -*-
from __future__ import annotations

import pytest

from api.routers import xhs as xhs_api


def test_looks_like_xhs_cookies():
    assert xhs_api._looks_like_xhs_cookies("a1=abc; webId=1")
    assert xhs_api._looks_like_xhs_cookies("web_session=xyz")
    assert not xhs_api._looks_like_xhs_cookies("SESSDATA=bili")


def test_resolve_xhs_cookies_priority(monkeypatch):
    monkeypatch.setattr(xhs_api.config, "XHS_COOKIES", "a1=from-config", raising=False)
    monkeypatch.setattr(xhs_api.config, "COOKIES", "a1=fallback", raising=False)
    monkeypatch.delenv("XHS_COOKIES", raising=False)

    assert xhs_api._resolve_xhs_cookies("a1=from-request") == "a1=from-request"
    assert xhs_api._resolve_xhs_cookies(None) == "a1=from-config"

    monkeypatch.setattr(xhs_api.config, "XHS_COOKIES", "", raising=False)
    assert xhs_api._resolve_xhs_cookies(None) == "a1=fallback"

    monkeypatch.setattr(xhs_api.config, "COOKIES", "SESSDATA=wrong-platform", raising=False)
    assert xhs_api._resolve_xhs_cookies(None) == ""


@pytest.mark.asyncio
async def test_add_xhs_creator_rejects_missing_cookies(monkeypatch):
    monkeypatch.setattr(xhs_api.config, "XHS_COOKIES", "", raising=False)
    monkeypatch.setattr(xhs_api.config, "COOKIES", "", raising=False)
    monkeypatch.delenv("XHS_COOKIES", raising=False)

    with pytest.raises(xhs_api.HTTPException) as exc:
        await xhs_api.add_xhs_creator(
            xhs_api.AddCreatorRequest(url="5eb8e1d400000000010075ae")
        )
    assert exc.value.status_code == 400
