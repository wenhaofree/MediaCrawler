# -*- coding: utf-8 -*-
from __future__ import annotations

import httpx
import pytest

from media_platform.xhs import cookies as xhs_cookies
from media_platform.xhs.client import XiaoHongShuClient
from media_platform.xhs.exception import CookieExpiredError


def test_resolve_xhs_cookies_priority(monkeypatch, tmp_path):
    secret = tmp_path / "xhs_cookies"
    runtime = tmp_path / "runtime_cookies"
    secret.write_text("a1=from-secret; web_session=s1", encoding="utf-8")
    runtime.write_text("a1=from-runtime; web_session=s2", encoding="utf-8")

    monkeypatch.setattr(xhs_cookies, "_reload_dotenv", lambda: None)
    monkeypatch.setenv("XHS_COOKIES_FILE", str(secret))
    monkeypatch.setenv("XHS_COOKIES_RUNTIME_FILE", str(runtime))
    monkeypatch.setenv("XHS_COOKIES", "a1=from-env; web_session=s0")
    monkeypatch.delenv("CRAWLER_COOKIES", raising=False)
    monkeypatch.setattr(xhs_cookies.config, "XHS_COOKIES", "a1=from-config", raising=False)
    monkeypatch.setattr(xhs_cookies.config, "COOKIES", "a1=fallback", raising=False)

    assert (
        xhs_cookies.resolve_xhs_cookies("a1=from-request; web_session=r")
        == "a1=from-request; web_session=r"
    )

    # Newer of secret/runtime wins (runtime rewritten after secret → newer).
    runtime.write_text("a1=newer-runtime; web_session=s3", encoding="utf-8")
    assert xhs_cookies.resolve_xhs_cookies(None) == "a1=newer-runtime; web_session=s3"

    runtime.unlink()
    assert xhs_cookies.resolve_xhs_cookies(None) == "a1=from-secret; web_session=s1"

    secret.unlink()
    assert xhs_cookies.resolve_xhs_cookies(None) == "a1=from-env; web_session=s0"


def test_persist_xhs_cookies_atomic(tmp_path, monkeypatch):
    target = tmp_path / "xhs_cookies"
    monkeypatch.setenv("XHS_COOKIES_RUNTIME_FILE", str(target))
    assert xhs_cookies.persist_xhs_cookies("a1=abc; web_session=xyz")
    assert target.read_text(encoding="utf-8") == "a1=abc; web_session=xyz"
    assert not list(tmp_path.glob("*.next"))


def test_client_merges_set_cookie_and_persists(monkeypatch, tmp_path):
    target = tmp_path / "runtime"
    monkeypatch.setenv("XHS_COOKIES_RUNTIME_FILE", str(target))

    client = XiaoHongShuClient(
        headers={"Cookie": "a1=old; web_session=old"},
        playwright_page=None,
        cookie_dict={"a1": "old", "web_session": "old"},
        persist_cookies=True,
    )
    response = httpx.Response(
        200,
        headers=[("set-cookie", "web_session=new-session"), ("set-cookie", "a1=new-a1")],
        json={"success": True, "data": {}},
        request=httpx.Request("GET", "https://edith.xiaohongshu.com/api"),
    )
    assert client._apply_response_cookies(response) is True
    assert client.cookie_dict["web_session"] == "new-session"
    assert client.cookie_dict["a1"] == "new-a1"
    assert "web_session=new-session" in client.headers["Cookie"]
    assert target.read_text(encoding="utf-8")


def test_is_login_expired_payload():
    assert XiaoHongShuClient._is_login_expired_payload({"msg": "登录已过期", "code": 1000})
    assert XiaoHongShuClient._is_login_expired_payload({"code": -100})
    assert not XiaoHongShuClient._is_login_expired_payload({"msg": "ok", "code": 0})


@pytest.mark.asyncio
async def test_request_raises_cookie_expired(monkeypatch):
    client = XiaoHongShuClient(
        headers={"Cookie": "a1=x; web_session=y"},
        playwright_page=None,
        cookie_dict={"a1": "x", "web_session": "y"},
        persist_cookies=False,
    )

    class _Resp:
        status_code = 200
        cookies = httpx.Cookies()
        text = '{"success":false,"msg":"登录已过期","code":-100}'

        def json(self):
            return {"success": False, "msg": "登录已过期", "code": -100}

    class _Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def request(self, *args, **kwargs):
            return _Resp()

    async def _noop_refresh():
        return None

    monkeypatch.setattr(
        "media_platform.xhs.client.make_async_client", lambda **kwargs: _Client()
    )
    monkeypatch.setattr(client, "_refresh_proxy_if_expired", _noop_refresh)

    with pytest.raises(CookieExpiredError):
        await client.request("GET", "https://edith.xiaohongshu.com/api/x")


@pytest.mark.asyncio
async def test_expired_response_does_not_persist_cookies(monkeypatch, tmp_path):
    target = tmp_path / "runtime"
    monkeypatch.setenv("XHS_COOKIES_RUNTIME_FILE", str(target))

    client = XiaoHongShuClient(
        headers={"Cookie": "a1=x; web_session=y"},
        playwright_page=None,
        cookie_dict={"a1": "x", "web_session": "y"},
        persist_cookies=True,
    )

    class _Resp:
        status_code = 200
        cookies = httpx.Cookies([("web_session", "stale-guest")])
        text = '{"success":false,"msg":"登录已过期","code":-100}'

        def json(self):
            return {"success": False, "msg": "登录已过期", "code": -100}

    class _Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, *args, **kwargs):
            return _Resp()

    monkeypatch.setattr(
        "media_platform.xhs.client.make_async_client", lambda **kwargs: _Client()
    )

    with pytest.raises(CookieExpiredError):
        await client.query_self()
    assert not target.exists()
