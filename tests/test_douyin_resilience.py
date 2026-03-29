# -*- coding: utf-8 -*-
#
# This file is part of MediaCrawler project.

from __future__ import annotations

import httpx
import pytest

from media_platform.douyin import client as douyin_client_module
from media_platform.douyin import core as douyin_core_module
from media_platform.douyin.client import DouYinClient
from media_platform.douyin.core import DouYinCrawler
from media_platform.douyin.exception import DataFetchError


@pytest.mark.asyncio
async def test_douyin_request_wraps_transport_errors_as_data_fetch_error(monkeypatch):
    client = DouYinClient(headers={}, playwright_page=None, cookie_dict={})
    attempts = {"count": 0}

    class FailingAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def request(self, method, url, timeout=None, **kwargs):
            attempts["count"] += 1
            raise httpx.RemoteProtocolError("Server disconnected without sending a response.")

    async def fake_sleep(_seconds):
        return None

    monkeypatch.setattr(
        douyin_client_module,
        "make_async_client",
        lambda **kwargs: FailingAsyncClient(),
    )
    monkeypatch.setattr(douyin_client_module.asyncio, "sleep", fake_sleep)

    with pytest.raises(DataFetchError, match="RemoteProtocolError"):
        await client.request("GET", "https://www.douyin.com/aweme/v1/web/aweme/detail/")

    assert attempts["count"] == 3


@pytest.mark.asyncio
async def test_douyin_fetch_creator_video_detail_skips_failed_detail_tasks(monkeypatch):
    crawler = DouYinCrawler()
    saved_aweme_ids = []
    media_aweme_ids = []

    async def fake_get_aweme_detail(aweme_id, semaphore):
        if aweme_id == "bad-aweme":
            raise RuntimeError("boom")
        return {
            "aweme_id": aweme_id,
            "desc": f"title-{aweme_id}",
            "author": {"uid": "u1", "sec_uid": "sec-1", "nickname": "tester", "avatar_thumb": {"url_list": [""]}},
            "statistics": {"digg_count": 1, "collect_count": 0, "comment_count": 0, "share_count": 0},
        }

    async def fake_update_douyin_aweme(aweme_item):
        saved_aweme_ids.append(aweme_item["aweme_id"])

    async def fake_get_aweme_media(aweme_item):
        media_aweme_ids.append(aweme_item["aweme_id"])

    crawler.get_aweme_detail = fake_get_aweme_detail  # type: ignore[method-assign]
    crawler.get_aweme_media = fake_get_aweme_media  # type: ignore[method-assign]
    monkeypatch.setattr(
        douyin_core_module.douyin_store,
        "update_douyin_aweme",
        fake_update_douyin_aweme,
    )

    await crawler.fetch_creator_video_detail(
        [{"aweme_id": "good-aweme"}, {"aweme_id": "bad-aweme"}]
    )

    assert saved_aweme_ids == ["good-aweme"]
    assert media_aweme_ids == ["good-aweme"]
