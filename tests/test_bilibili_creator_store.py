import asyncio

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool

import config
from database import db_session
from database.models import Base, BilibiliUpInfo, BilibiliUpStats, BilibiliVideoStats
import store.bilibili as bili_store
from store.bilibili._store_impl import BiliDbStoreImplement
from var import reset_bili_creator_stats_seen


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

        reset_bili_creator_stats_seen()
        store = BiliDbStoreImplement()
        await store.store_creator({"user_id": "123", "nickname": "old", "total_fans": "1"})
        await store.store_creator({"user_id": 123, "nickname": "new", "total_fans": 2})

        await store.store_content(
            {
                "video_id": "BV1test",
                "video_url": "https://www.bilibili.com/video/av1",
                "title": "old video",
                "liked_count": "10",
                "create_time": 1,
                "video_play_count": "100",
                "video_comment": "2",
            }
        )
        await store.store_content(
            {
                "video_id": "BV1test",
                "video_url": "https://www.bilibili.com/video/av1",
                "title": "new video",
                "liked_count": "20",
                "create_time": 1,
                "video_play_count": "200",
                "video_comment": "3",
            }
        )

        async with db_session.get_session() as session:
            count = await session.scalar(select(func.count()).select_from(BilibiliUpInfo))
            row = (await session.execute(select(BilibiliUpInfo))).scalars().one()
            up_stats = (await session.execute(select(BilibiliUpStats))).scalars().all()
            video_stats = (await session.execute(select(BilibiliVideoStats))).scalars().all()
        await engine.dispose()
        return count, row, up_stats, video_stats

    count, row, up_stats, video_stats = asyncio.run(run())
    assert count == 1
    assert row.user_id == 123
    assert row.nickname == "new"
    assert row.total_fans == 2
    assert row.is_monitored == 0
    assert len(up_stats) == 1
    assert up_stats[0].follower_count == 1
    assert len(video_stats) == 2
    assert [snapshot.play_count for snapshot in video_stats] == [100, 200]


def test_bili_monitored_flag_and_migration_backfill(monkeypatch):
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.pool import StaticPool

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
    monkeypatch.setattr(db_session, "get_async_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr(config, "SAVE_DATA_OPTION", "db")

    async def run():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        reset_bili_creator_stats_seen()
        await bili_store.save_creator(
            user_id=20813884,
            creator_info={"mid": 20813884, "name": "monitored"},
            relation_stat={"follower": 100},
        )
        await bili_store.update_up_info(
            {
                "View": {"owner": {"mid": 999999, "name": "collab"}},
                "Card": {"like_num": 10, "card": {"mid": 999999, "name": "collab", "fans": 5}},
            }
        )
        # Subsequent video card update for an already-monitored UP must keep is_monitored=1.
        await bili_store.update_up_info(
            {
                "View": {"owner": {"mid": 20813884, "name": "monitored-updated"}},
                "Card": {"like_num": 20, "card": {"mid": 20813884, "name": "monitored-updated", "fans": 105}},
            }
        )

        async with db_session.get_session() as session:
            rows = (await session.execute(select(BilibiliUpInfo).order_by(BilibiliUpInfo.user_id.asc()))).scalars().all()
            by_uid = {row.user_id: row for row in rows}
            assert by_uid[999999].is_monitored == 0
            assert by_uid[20813884].is_monitored == 1
            assert by_uid[20813884].nickname == "monitored-updated"

            # Simulate legacy upgrade where both rows start at 0, only api_add has stats history.
            by_uid[20813884].is_monitored = 0
            session.add(
                BilibiliUpStats(
                    user_id=20813884,
                    follower_count=100,
                    total_likes=10,
                    collected_at="2026-11-16T11:00:00+08:00",
                    scheduled_slot="manual",
                    source_type="api_add",
                )
            )
            await session.commit()

        async with engine.begin() as conn:
            await conn.run_sync(db_session._migrate_bilibili_monitored_creators)

        async with db_session.get_session() as session:
            rows = (await session.execute(select(BilibiliUpInfo).order_by(BilibiliUpInfo.user_id.asc()))).scalars().all()
            by_uid = {row.user_id: row for row in rows}
            assert by_uid[20813884].is_monitored == 1
            assert by_uid[999999].is_monitored == 0
        await engine.dispose()

    asyncio.run(run())


def test_bili_creator_videos_skips_collab_author_up_info(monkeypatch):
    from types import SimpleNamespace
    from media_platform.bilibili.core import BilibiliCrawler
    from media_platform.bilibili.field import SearchOrderType
    from media_platform.bilibili.help import BilibiliSign

    signed = BilibiliSign("a" * 32, "b" * 32).sign({"mid": 20813884, "order": SearchOrderType.LAST_PUBLISH})
    assert signed["order"] == "pubdate"

    crawler = BilibiliCrawler()
    saved_videos = []
    updated_ups = []

    async def fake_get_creator_videos(creator_id, pn, ps):
        return {
            "list": {"vlist": [{"bvid": "BV1own"}, {"bvid": "BV1collab"}]},
            "page": {"count": 2},
        }

    async def fake_get_video_info(aid=0, bvid=""):
        owner_mid = 20813884 if bvid == "BV1own" else 888888
        return {
            "View": {"aid": 1 if bvid == "BV1own" else 2, "owner": {"mid": owner_mid, "name": f"up-{owner_mid}"}},
            "Card": {"card": {"mid": owner_mid, "name": f"up-{owner_mid}"}},
        }

    async def fake_update_video(detail):
        saved_videos.append(detail["View"]["aid"])

    async def fake_update_up(detail):
        updated_ups.append(detail["View"]["owner"]["mid"])

    async def fake_noop(*_args, **_kwargs):
        return None

    crawler.bili_client = SimpleNamespace(
        get_creator_videos=fake_get_creator_videos,
        get_video_info=fake_get_video_info,
    )
    monkeypatch.setattr(config, "CRAWLER_MAX_PAGES", 1)
    monkeypatch.setattr(config, "CRAWLER_MAX_SLEEP_SEC", 0)
    monkeypatch.setattr(bili_store, "update_bilibili_video", fake_update_video)
    monkeypatch.setattr(bili_store, "update_up_info", fake_update_up)
    monkeypatch.setattr(crawler, "download_media", fake_noop)
    monkeypatch.setattr(crawler, "batch_get_video_comments", fake_noop)

    asyncio.run(crawler.get_creator_videos(20813884))

    assert saved_videos == [1, 2]
    assert updated_ups == [20813884]
