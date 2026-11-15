import asyncio

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool

import config
from database import db_session
from database.models import Base, XhsCreator, XhsCreatorStats, XhsNoteStats
from media_platform.douyin.lifecycle import parse_count
from store.xhs._store_impl import XhsDbStoreImplement
from var import reset_xhs_creator_stats_seen


def test_xhs_creator_and_note_snapshots_are_append_only(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
    monkeypatch.setattr(db_session, "get_async_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr(config, "SAVE_DATA_OPTION", "db")

    async def run():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        reset_xhs_creator_stats_seen()
        store = XhsDbStoreImplement()
        await store.store_creator({"user_id": "xhs-user", "nickname": "old", "fans": "1.2万"})
        await store.store_creator({"user_id": "xhs-user", "nickname": "new", "fans": "13000"})
        await store.store_content({"note_id": "note-1", "liked_count": "2万", "collected_count": "3"})
        await store.store_content({"note_id": "note-1", "liked_count": "21000", "collected_count": "4"})

        async with db_session.get_session() as session:
            creator_count = await session.scalar(select(func.count()).select_from(XhsCreator))
            creator = (await session.execute(select(XhsCreator))).scalars().one()
            creator_stats = (await session.execute(select(XhsCreatorStats))).scalars().all()
            note_stats = (await session.execute(select(XhsNoteStats))).scalars().all()
        await engine.dispose()
        return creator_count, creator, creator_stats, note_stats

    creator_count, creator, creator_stats, note_stats = asyncio.run(run())
    assert creator_count == 1
    assert creator.nickname == "new"
    assert len(creator_stats) == 1
    assert creator_stats[0].follower_count == 12_000
    assert [snapshot.liked_count for snapshot in note_stats] == [20_000, 21_000]
    assert [snapshot.collected_count for snapshot in note_stats] == [3, 4]


def test_parse_count_supports_xhs_abbreviations():
    assert parse_count("1.5万") == 15_000
    assert parse_count("2亿") == 200_000_000
