# -*- coding: utf-8 -*-
import asyncio
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool

import config
from database import db_session
from database.models import Base, DouyinCreator, DyCreator
import store.douyin as ds


def test_douyin_save_creator_dict():
    mock_creator = {
        "user": {
            "nickname": "测试抖音博主",
            "gender": 1,
            "signature": "热爱技术，分享生活",
            "ip_location": "北京",
            "following_count": 150,
            "max_follower_count": 88000,
            "total_favorited": 2300000,
            "aweme_count": 120,
            "avatar_thumb": {"url_list": ["https://example.com/avatar_thumb.jpg"]},
        }
    }
    user_id = "MS4wLjABAAAA_test_sec_uid"
    captured = {}

    class FakeStore:
        async def store_creator(self, creator_item):
            captured.update(creator_item)

    orig = ds.DouyinStoreFactory.create_store
    ds.DouyinStoreFactory.create_store = staticmethod(lambda: FakeStore())
    try:
        asyncio.run(ds.save_creator(user_id, mock_creator))
    finally:
        ds.DouyinStoreFactory.create_store = orig

    assert captured["user_id"] == user_id
    assert captured["nickname"] == "测试抖音博主"
    assert captured["gender"] == "Male"
    assert captured["desc"] == "热爱技术，分享生活"
    assert captured["ip_location"] == "北京"
    assert captured["follows"] == "150"
    assert captured["fans"] == "88000"
    assert captured["interaction"] == "2300000"
    assert captured["videos_count"] == "120"
    assert captured["avatar"] == "https://example.com/avatar_thumb.jpg"


def test_douyin_save_creator_e2e_db(monkeypatch):
    mock_creator = {
        "user": {
            "nickname": "测试博主E2E",
            "gender": 2,
            "signature": "专注美妆护肤",
            "ip_location": "杭州",
            "following_count": 50,
            "max_follower_count": 10000,
            "total_favorited": 50000,
            "aweme_count": 30,
            "avatar_300x300": {"uri": "test_uri_avatar"},
        }
    }
    user_id = "MS4wLjABAAAA_test_e2e_uid"

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
    )
    monkeypatch.setattr(db_session, "get_async_engine", lambda *a, **kw: engine)
    monkeypatch.setattr(config, "SAVE_DATA_OPTION", "db")

    async def _run():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        await ds.save_creator(user_id, mock_creator)

        async with db_session.get_session() as session:
            res = await session.execute(select(DyCreator).where(DyCreator.user_id == user_id))
            row = res.scalar_one_or_none()
        await engine.dispose()
        return row

    row = asyncio.run(_run())
    assert row is not None
    assert row.__tablename__ == "douyin_creator"
    assert DyCreator is DouyinCreator
    assert row.user_id == user_id
    assert row.nickname == "测试博主E2E"
    assert row.gender == "Female"
    assert row.fans == "10000"
    assert row.follows == "50"
    assert row.interaction == "50000"
    assert row.videos_count == "30"
    assert "test_uri_avatar" in row.avatar

