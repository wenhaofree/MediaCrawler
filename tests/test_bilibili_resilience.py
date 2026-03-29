# -*- coding: utf-8 -*-
#
# This file is part of MediaCrawler project.

import pytest
import httpx

import config
from media_platform.bilibili import client as bilibili_client_module
from media_platform.bilibili.client import BilibiliClient
from media_platform.bilibili.core import BilibiliCrawler
from media_platform.bilibili.exception import DataFetchError
from tools.httpx_util import make_async_client


class ClosedPage:
    async def evaluate(self, _expression):
        raise RuntimeError("Target page, context or browser has been closed")


class StoragePage:
    def __init__(self):
        self.calls = 0

    async def evaluate(self, _expression):
        self.calls += 1
        return {
            "wbi_img_urls": (
                "https://i0.hdslb.com/bfs/wbi/first_img_key.png-"
                "https://i0.hdslb.com/bfs/wbi/first_sub_key.png"
            )
        }


@pytest.mark.asyncio
async def test_get_wbi_keys_falls_back_to_nav_when_page_is_closed():
    client = BilibiliClient(
        headers={},
        playwright_page=ClosedPage(),
        cookie_dict={},
    )

    calls = []

    async def fake_request(method, url, **kwargs):
        calls.append((method, url))
        return {
            "wbi_img": {
                "img_url": "https://i0.hdslb.com/bfs/wbi/nav_img_key.png",
                "sub_url": "https://i0.hdslb.com/bfs/wbi/nav_sub_key.png",
            }
        }

    client.request = fake_request  # type: ignore[method-assign]

    assert await client.get_wbi_keys() == ("nav_img_key", "nav_sub_key")
    assert calls == [("GET", "https://api.bilibili.com/x/web-interface/nav")]


@pytest.mark.asyncio
async def test_get_wbi_keys_uses_cached_page_keys():
    page = StoragePage()
    client = BilibiliClient(
        headers={},
        playwright_page=page,
        cookie_dict={},
    )

    async def fail_request(*args, **kwargs):
        raise AssertionError("request fallback should not be used when localStorage keys are cached")

    client.request = fail_request  # type: ignore[method-assign]

    assert await client.get_wbi_keys() == ("first_img_key", "first_sub_key")
    assert await client.get_wbi_keys() == ("first_img_key", "first_sub_key")
    assert page.calls == 1


@pytest.mark.asyncio
async def test_batch_get_video_comments_does_not_fail_on_single_task_error(monkeypatch):
    crawler = BilibiliCrawler()
    monkeypatch.setattr(config, "ENABLE_GET_COMMENTS", True)

    called_video_ids = []

    async def fake_get_comments(video_id, semaphore):
        called_video_ids.append(video_id)
        if video_id == "bad-video":
            raise RuntimeError("boom")
        return None

    crawler.get_comments = fake_get_comments  # type: ignore[method-assign]

    await crawler.batch_get_video_comments(["good-video", "bad-video"])

    assert called_video_ids == ["good-video", "bad-video"]


def test_make_async_client_disables_system_proxy_inheritance_by_default():
    client = make_async_client()
    try:
        assert client.trust_env is False
    finally:
        import asyncio
        asyncio.run(client.aclose())


@pytest.mark.asyncio
async def test_bilibili_request_wraps_transport_errors_as_data_fetch_error(monkeypatch):
    client = BilibiliClient(
        headers={},
        playwright_page=ClosedPage(),
        cookie_dict={},
    )

    attempts = {"count": 0}

    class FailingAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def request(self, method, url, timeout=None, **kwargs):
            attempts["count"] += 1
            raise httpx.RemoteProtocolError("Server disconnected without sending a response.")

    monkeypatch.setattr(
        bilibili_client_module,
        "make_async_client",
        lambda **kwargs: FailingAsyncClient(),
    )

    with pytest.raises(DataFetchError, match="RemoteProtocolError"):
        await client.request("GET", "https://api.bilibili.com/x/web-interface/view/detail")

    assert attempts["count"] == 3
