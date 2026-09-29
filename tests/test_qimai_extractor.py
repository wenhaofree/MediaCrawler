# -*- coding: utf-8 -*-

from media_platform.qimai.help import QimaiExtractor
from media_platform.qimai.client import QimaiClient
from model.m_qimai import QimaiApp

import pytest


def test_qimai_extractor_finds_nested_apps_once():
    apps = QimaiExtractor.extract_apps(
        {
            "data": {
                "list": [
                    {
                        "appid": 414478124,
                        "appName": "微信",
                        "publisher": "Tencent",
                        "rating": 4.7,
                    },
                    {"appid": 414478124, "appName": "微信"},
                    {"name": "missing id"},
                ]
            }
        }
    )

    assert len(apps) == 1
    assert apps[0].app_id == "414478124"
    assert apps[0].app_name == "微信"
    assert apps[0].publisher == "Tencent"
    assert apps[0].rating_value == "4.7"


def test_qimai_detail_dom_maps_app_info():
    app = QimaiExtractor.app_from_detail_dom(
        {
            "APP ID": "977946724",
            "分类": "教育",
            "价格": "免费",
            "内购": "无",
            "96811个评分": "3.2",
            "教育(免费)": "第1名",
            "昨日下载量": "28,599",
            "最近更新": "2026-09-18",
            "最早发布": "2016-01-18",
        }
    )

    assert app.app_id == "977946724"
    assert app.category == "教育"
    assert app.price == "免费"
    assert app.inner_purchase == "无"
    assert app.rating_count == "96811"
    assert app.rating_value == "3.2"
    assert app.current_rank == "第1名"
    assert app.yesterday_downloads == "28,599"
    assert app.last_update_date == "2026-09-18"
    assert app.release_date == "2016-01-18"


def test_qimai_detail_dom_maps_wan_rating_count():
    app = QimaiExtractor.app_from_detail_dom(
        {
            "app_id": "1488854568",
            "分类": "教育",
            "价格": "免费",
            "内购": "无",
            "67万个评分": "4.6",
            "教育(免费)": "第2名",
            "昨日下载量": "49,130",
            "最近更新": "2026-09-24",
            "最早发布": "2019-11-27",
        }
    )

    assert app.app_id == "1488854568"
    assert app.category == "教育"
    assert app.rating_value == "4.6"
    assert app.rating_count == "670000"
    assert app.current_rank == "第2名"
    assert app.yesterday_downloads == "49,130"


def test_qimai_comment_dom_rows_keep_app_id_and_mask_user():
    comments = QimaiExtractor.comments_from_dom_rows(
        [
            {
                "comment_id": "977946724-0",
                "rating": "1",
                "title": "扫码学习通",
                "user_nickname": "垃圾私募学习通",
                "content": "扫码软件 刷个课那么卡",
                "create_time": "2026-09-27 20:55:50",
                "is_deleted": "0",
            }
        ],
        "977946724",
    )

    assert comments[0].app_id == "977946724"
    assert comments[0].comment_id == "977946724-0"
    assert comments[0].rating == "1"
    assert comments[0].title == "扫码学习通"
    assert comments[0].content == "扫码软件 刷个课那么卡"
    assert comments[0].user_nickname == "垃***通"
    assert comments[0].creator_hash


@pytest.mark.asyncio
async def test_qimai_rank_zero_max_scrolls_until_no_more_payload(monkeypatch):
    client = QimaiClient(None)

    async def fake_goto_and_extract(*_args):
        return [QimaiApp(app_id="1", app_name="A")]

    payloads = [
        {"data": {"list": [{"appid": "2", "appName": "B"}]}},
        {},
    ]

    async def fake_scroll_for_payload(*_args):
        return payloads.pop(0)

    monkeypatch.setattr(client, "_goto_and_extract", fake_goto_and_extract)
    monkeypatch.setattr(client, "_scroll_for_payload", fake_scroll_for_payload)

    apps = await client.get_rank_apps("free", "", "6017", 0)

    assert [app.app_id for app in apps] == ["1", "2"]
    assert all(app.rank_type == "free" for app in apps)
