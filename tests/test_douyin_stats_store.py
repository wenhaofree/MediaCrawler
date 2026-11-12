# -*- coding: utf-8 -*-
import asyncio

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool

import config
from database import db_session
from database.models import Base, DouyinAweme, DouyinAwemeStats, DouyinCreatorStats, DyCreator
import store.douyin as ds


def test_save_creator_appends_stats(monkeypatch):
    mock_creator = {
        "user": {
            "nickname": "快照博主",
            "gender": 1,
            "signature": "增长测试",
            "ip_location": "上海",
            "following_count": 10,
            "max_follower_count": 999,
            "total_favorited": 12345,
            "aweme_count": 7,
            "avatar_thumb": {"url_list": ["https://example.com/a.jpg"]},
        }
    }
    user_id = "MS4wLjABAAAA_stats_creator"

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
    monkeypatch.setattr(db_session, "get_async_engine", lambda *a, **kw: engine)
    monkeypatch.setattr(config, "SAVE_DATA_OPTION", "db")

    async def _run():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await ds.save_creator(
            user_id,
            mock_creator,
            write_stats=True,
            source_type="creator_crawl",
            scheduled_slot="morning",
        )
        await ds.save_creator(
            user_id,
            mock_creator,
            write_stats=True,
            source_type="creator_crawl",
            scheduled_slot="morning",
        )
        async with db_session.get_session() as session:
            creator = (
                await session.execute(select(DyCreator).where(DyCreator.user_id == user_id))
            ).scalar_one()
            stats = (
                await session.execute(
                    select(DouyinCreatorStats).where(DouyinCreatorStats.user_id == user_id)
                )
            ).scalars().all()
        await engine.dispose()
        return creator, stats

    creator, stats = asyncio.run(_run())
    assert creator.fans == "999"
    assert len(stats) == 2
    assert stats[0].follower_count == 999
    assert stats[0].scheduled_slot == "morning"
    assert stats[1].total_likes == 12345


def test_update_aweme_appends_stats(monkeypatch):
    aweme_item = {
        "aweme_id": "aweme_stats_1",
        "aweme_type": 0,
        "desc": "测试视频标题",
        "create_time": 1730000000,
        "author": {
            "uid": "uid1",
            "sec_uid": "sec1",
            "short_id": "1",
            "unique_id": "u1",
            "signature": "",
            "nickname": "作者",
            "avatar_thumb": {"url_list": ["https://example.com/a.jpg"]},
        },
        "statistics": {
            "digg_count": 100,
            "collect_count": 20,
            "comment_count": 5,
            "share_count": 3,
            "play_count": 1000,
        },
        "ip_label": "",
    }

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
    monkeypatch.setattr(db_session, "get_async_engine", lambda *a, **kw: engine)
    monkeypatch.setattr(config, "SAVE_DATA_OPTION", "db")

    async def _run():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await ds.update_douyin_aweme(
            aweme_item,
            source_type="detail",
            write_stats=True,
            scheduled_slot="evening",
        )
        aweme_item["statistics"]["digg_count"] = 180
        await ds.update_douyin_aweme(
            aweme_item,
            source_type="detail",
            write_stats=True,
            scheduled_slot="evening",
        )
        # discovery without stats
        await ds.update_douyin_aweme(
            aweme_item,
            source_type="creator_crawl",
            write_stats=False,
            scheduled_slot="afternoon",
        )
        async with db_session.get_session() as session:
            aweme = (
                await session.execute(
                    select(DouyinAweme).where(DouyinAweme.aweme_id == "aweme_stats_1")
                )
            ).scalar_one()
            stats = (
                await session.execute(
                    select(DouyinAwemeStats).where(DouyinAwemeStats.aweme_id == "aweme_stats_1")
                )
            ).scalars().all()
        await engine.dispose()
        return aweme, stats

    aweme, stats = asyncio.run(_run())
    assert aweme.liked_count == "180"
    assert len(stats) == 2
    assert stats[0].liked_count == 100
    assert stats[1].liked_count == 180
    assert stats[0].scheduled_slot == "evening"
    assert stats[0].play_count == 1000
