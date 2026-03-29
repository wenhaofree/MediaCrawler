# -*- coding: utf-8 -*-
#
# This file is part of MediaCrawler project.

from __future__ import annotations

from types import SimpleNamespace

import pytest

import config
from media_platform.bilibili import core as bilibili_core_module
from media_platform.bilibili.core import BilibiliCrawler
from media_platform.douyin import client as douyin_client_module
from media_platform.douyin.client import DouYinClient
from media_platform.weibo import client as weibo_client_module
from media_platform.weibo.client import WeiboClient
from media_platform.xhs import client as xhs_client_module
from media_platform.xhs.client import XiaoHongShuClient
from media_platform.zhihu import client as zhihu_client_module
from media_platform.zhihu.client import ZhiHuClient
from model.m_zhihu import ZhihuCreator


async def _noop_sleep(_seconds):
    return None


@pytest.mark.asyncio
async def test_xhs_creator_crawl_respects_max_pages(monkeypatch):
    client = XiaoHongShuClient(headers={}, playwright_page=None, cookie_dict={})
    monkeypatch.setattr(config, "CRAWLER_MAX_PAGES", 2)
    monkeypatch.setattr(xhs_client_module.asyncio, "sleep", _noop_sleep)

    calls = []
    responses = [
        {"has_more": True, "cursor": "cursor-1", "notes": [{"id": "n1"}]},
        {"has_more": True, "cursor": "cursor-2", "notes": [{"id": "n2"}]},
        {"has_more": False, "cursor": "", "notes": [{"id": "n3"}]},
    ]

    async def fake_get_notes_by_creator(user_id, cursor, page_size=30, xsec_token="", xsec_source="pc_feed"):
        calls.append((user_id, cursor))
        return responses[len(calls) - 1]

    client.get_notes_by_creator = fake_get_notes_by_creator  # type: ignore[method-assign]

    result = await client.get_all_notes_by_creator("user-1")

    assert len(calls) == 2
    assert [item["id"] for item in result] == ["n1", "n2"]


@pytest.mark.asyncio
async def test_douyin_creator_crawl_respects_max_pages(monkeypatch):
    client = DouYinClient(headers={}, playwright_page=None, cookie_dict={})
    monkeypatch.setattr(config, "CRAWLER_MAX_PAGES", 2)

    calls = []
    responses = [
        {"has_more": 1, "max_cursor": "cursor-1", "aweme_list": [{"aweme_id": "a1"}]},
        {"has_more": 1, "max_cursor": "cursor-2", "aweme_list": [{"aweme_id": "a2"}]},
        {"has_more": 0, "max_cursor": "", "aweme_list": [{"aweme_id": "a3"}]},
    ]

    async def fake_get_user_aweme_posts(sec_user_id, max_cursor=""):
        calls.append((sec_user_id, max_cursor))
        return responses[len(calls) - 1]

    client.get_user_aweme_posts = fake_get_user_aweme_posts  # type: ignore[method-assign]

    result = await client.get_all_user_aweme_posts("MS4w-test")

    assert len(calls) == 2
    assert [item["aweme_id"] for item in result] == ["a1", "a2"]


@pytest.mark.asyncio
async def test_weibo_creator_crawl_respects_max_pages(monkeypatch):
    client = WeiboClient(headers={}, playwright_page=None, cookie_dict={})
    monkeypatch.setattr(config, "CRAWLER_MAX_PAGES", 2)
    monkeypatch.setattr(weibo_client_module.asyncio, "sleep", _noop_sleep)

    calls = []
    responses = [
        {
            "cardlistInfo": {"since_id": "1", "total": 30},
            "cards": [{"card_type": 9, "mblog": {"id": "w1"}}],
        },
        {
            "cardlistInfo": {"since_id": "2", "total": 30},
            "cards": [{"card_type": 9, "mblog": {"id": "w2"}}],
        },
        {
            "cardlistInfo": {"since_id": "3", "total": 30},
            "cards": [{"card_type": 9, "mblog": {"id": "w3"}}],
        },
    ]

    async def fake_get_notes_by_creator(creator_id, container_id, since_id):
        calls.append((creator_id, container_id, since_id))
        return responses[len(calls) - 1]

    client.get_notes_by_creator = fake_get_notes_by_creator  # type: ignore[method-assign]

    result = await client.get_all_notes_by_creator_id("123456", "107603123456")

    assert len(calls) == 2
    assert [item["mblog"]["id"] for item in result] == ["w1", "w2"]


@pytest.mark.asyncio
async def test_zhihu_creator_crawl_respects_max_pages(monkeypatch):
    client = ZhiHuClient(headers={"cookie": "d_c0=test"}, playwright_page=None, cookie_dict={"d_c0": "test"})
    monkeypatch.setattr(config, "CRAWLER_MAX_PAGES", 2)
    monkeypatch.setattr(zhihu_client_module.asyncio, "sleep", _noop_sleep)

    calls = []
    creator = ZhihuCreator(url_token="morgancheng")
    client._extractor.extract_content_list_from_creator = lambda data: data  # type: ignore[method-assign]

    responses = [
        {"paging": {"is_end": False}, "data": [{"content_id": "z1"}]},
        {"paging": {"is_end": False}, "data": [{"content_id": "z2"}]},
        {"paging": {"is_end": True}, "data": [{"content_id": "z3"}]},
    ]

    async def fake_get_creator_articles(url_token, offset, limit):
        calls.append((url_token, offset, limit))
        return responses[len(calls) - 1]

    client.get_creator_articles = fake_get_creator_articles  # type: ignore[method-assign]

    result = await client.get_all_articles_by_creator(creator)

    assert len(calls) == 2
    assert [item["content_id"] for item in result] == ["z1", "z2"]


@pytest.mark.asyncio
async def test_bilibili_creator_crawl_respects_max_pages(monkeypatch):
    crawler = BilibiliCrawler()
    monkeypatch.setattr(config, "CRAWLER_MAX_PAGES", 2)
    monkeypatch.setattr(bilibili_core_module.asyncio, "sleep", _noop_sleep)

    page_calls = []
    fetched_bvids = []

    async def fake_get_creator_videos(creator_id, pn, ps):
        page_calls.append((creator_id, pn, ps))
        return {
            "list": {"vlist": [{"bvid": f"BV{pn}"}]},
            "page": {"count": 999},
        }

    async def fake_get_specified_videos(video_bvids_list):
        fetched_bvids.append(video_bvids_list)

    crawler.bili_client = SimpleNamespace(get_creator_videos=fake_get_creator_videos)
    crawler.get_specified_videos = fake_get_specified_videos  # type: ignore[method-assign]

    await crawler.get_creator_videos(20813884)

    assert [item[1] for item in page_calls] == [1, 2]
    assert fetched_bvids == [["BV1"], ["BV2"]]
