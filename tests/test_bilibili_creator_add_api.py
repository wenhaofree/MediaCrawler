# -*- coding: utf-8 -*-
import asyncio

from media_platform.bilibili.help import parse_creator_info_from_url
from store import bilibili as bilibili_store


def test_parse_bilibili_creator_url_and_uid():
    assert parse_creator_info_from_url("20813884").creator_id == "20813884"
    assert (
        parse_creator_info_from_url("https://space.bilibili.com/434377496?spm_id_from=333.1007.0.0").creator_id
        == "434377496"
    )


def test_save_creator_maps_profile(monkeypatch):
    captured = {}

    class FakeStore:
        async def store_creator(self, creator):
            captured.update(creator)

    monkeypatch.setattr(
        bilibili_store.BiliStoreFactory,
        "create_store",
        staticmethod(lambda: FakeStore()),
    )

    asyncio.run(
        bilibili_store.save_creator(
            user_id=20813884,
            creator_info={
                "mid": 20813884,
                "name": "测试UP",
                "sex": "男",
                "sign": "hello",
                "face": "https://example.com/a.jpg",
                "level": 6,
                "official": {"type": 0},
            },
            relation_stat={"follower": 12345, "following": 10},
            up_stat={"likes": 999},
        )
    )

    assert captured["user_id"] == 20813884
    assert captured["nickname"] == "测试UP"
    assert captured["total_fans"] == 12345
    assert captured["total_liked"] == 999
    assert captured["avatar"] == "https://example.com/a.jpg"
