# -*- coding: utf-8 -*-
from __future__ import annotations

import pytest

from api.routers import gzh as gzh_api
from media_platform.gzh import weread_cli
from var import reset_gzh_account_stats_seen, should_write_gzh_account_stats


def test_gzh_account_stats_dedupe():
    reset_gzh_account_stats_seen()
    assert should_write_gzh_account_stats("MP_WXS_1") is True
    assert should_write_gzh_account_stats("MP_WXS_1") is False
    assert should_write_gzh_account_stats("MP_WXS_2") is True


def test_resolve_web_cookie_priority(monkeypatch):
    monkeypatch.setattr(weread_cli, "load_dotenv", lambda *a, **k: False, raising=False)
    # Avoid .env override during unit test
    import dotenv

    monkeypatch.setattr(dotenv, "load_dotenv", lambda *a, **k: False)
    monkeypatch.setenv("WEREAD_WEB_COOKIE", "from-weread")
    monkeypatch.setenv("GZH_WEB_COOKIE", "from-gzh-stale")
    monkeypatch.setattr(weread_cli.config, "GZH_WEB_COOKIE", "from-config-stale", raising=False)
    # WEREAD_WEB_COOKIE must win over stale GZH_WEB_COOKIE / config
    assert weread_cli.resolve_web_cookie() == "from-weread"
    assert weread_cli.resolve_web_cookie("from-request") == "from-request"


def test_resolve_web_cookie_strips_quotes(monkeypatch):
    import dotenv

    monkeypatch.setattr(dotenv, "load_dotenv", lambda *a, **k: False)
    monkeypatch.setenv("WEREAD_WEB_COOKIE", "'wr_skey=abc'")
    monkeypatch.delenv("GZH_WEB_COOKIE", raising=False)
    monkeypatch.setattr(weread_cli.config, "GZH_WEB_COOKIE", "", raising=False)
    assert weread_cli.resolve_web_cookie() == "wr_skey=abc"


@pytest.mark.asyncio
async def test_add_gzh_account_requires_id_or_keyword():
    with pytest.raises(gzh_api.HTTPException) as exc:
        await gzh_api.add_gzh_account(gzh_api.AddAccountRequest())
    assert exc.value.status_code == 400
