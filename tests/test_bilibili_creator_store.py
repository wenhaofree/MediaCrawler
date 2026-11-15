import asyncio

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool

import config
from database import db_session
from database.models import Base, BilibiliUpInfo
import store.bilibili as bili_store
from store.bilibili._store_impl import BiliDbStoreImplement


def test_update_up_info_maps_video_card_to_creator():
    captured = {}

    class FakeStore:
        async def store_creator(self, creator):
            captured.update(creator)

    original = bili_store.BiliStoreFactory.create_store
    bili_store.BiliStoreFactory.create_store = staticmethod(lambda: FakeStore())
    try:
        asyncio.run(
            bili_store.update_up_info(
                {
                    "Card": {
                        "like_num": 456,
                        "card": {
                            "mid": 123,
                            "name": "测试 UP",
                            "sex": "保密",
                            "sign": "公开简介",
                            "face": "https://example.com/avatar.jpg",
                            "fans": 789,
                            "level_info": {"current_level": 6},
                            "official_verify": {"type": 0},
                        },
                    }
                }
            )
        )
    finally:
        bili_store.BiliStoreFactory.create_store = original

    assert captured == {
        "user_id": 123,
        "nickname": "测试 UP",
        "sex": "保密",
        "sign": "公开简介",
        "avatar": "https://example.com/avatar.jpg",
        "total_fans": 789,
        "total_liked": 456,
        "user_rank": 6,
        "is_official": 0,
    }


def test_bili_creator_store_upserts_by_uid(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
    monkeypatch.setattr(db_session, "get_async_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr(config, "SAVE_DATA_OPTION", "db")

    async def run():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        store = BiliDbStoreImplement()
        await store.store_creator({"user_id": "123", "nickname": "old", "total_fans": "1"})
        await store.store_creator({"user_id": 123, "nickname": "new", "total_fans": 2})

        async with db_session.get_session() as session:
            count = await session.scalar(select(func.count()).select_from(BilibiliUpInfo))
            row = (await session.execute(select(BilibiliUpInfo))).scalars().one()
        await engine.dispose()
        return count, row

    count, row = asyncio.run(run())
    assert count == 1
    assert row.user_id == 123
    assert row.nickname == "new"
    assert row.total_fans == 2
