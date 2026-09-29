# -*- coding: utf-8 -*-

from sqlalchemy import func, select
import pytest

import config
from config.db_config import sqlite_db_config
from database import db_session
from database.db_session import create_tables, get_session
from database.models import GoofishItem
from store.goofish import GooFishStoreFactory
from store.goofish._store_impl import (
    GooFishCsvStoreImplement,
    GooFishDbStoreImplement,
    GooFishExcelStoreImplement,
    GooFishJsonStoreImplement,
    GooFishJsonlStoreImplement,
    GooFishMongoStoreImplement,
    GooFishSqliteStoreImplement,
)


def test_goofish_store_factory_registers_all_store_types():
    assert GooFishStoreFactory.STORES == {
        "csv": GooFishCsvStoreImplement,
        "db": GooFishDbStoreImplement,
        "postgres": GooFishDbStoreImplement,
        "json": GooFishJsonStoreImplement,
        "jsonl": GooFishJsonlStoreImplement,
        "sqlite": GooFishSqliteStoreImplement,
        "mongodb": GooFishMongoStoreImplement,
        "excel": GooFishExcelStoreImplement,
    }


@pytest.mark.asyncio
async def test_goofish_sqlite_store_upserts_by_item_id(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "SAVE_DATA_OPTION", "sqlite")
    monkeypatch.setitem(sqlite_db_config, "db_path", str(tmp_path / "goofish.db"))
    for engine in db_session._engines.values():
        await engine.dispose()
    db_session._engines.clear()

    await create_tables("sqlite")
    store = GooFishSqliteStoreImplement()
    item = {
        "item_id": "1001",
        "title": "old",
        "desc": "",
        "item_url": "https://www.goofish.com/item?id=1001",
        "price": "99",
        "original_price": "199",
        "discount_label": "2人小刀价",
        "shipping": "包邮",
        "area": "上海",
        "image_url": "",
        "want_count": "1",
        "browse_count": "2",
        "publish_time": "2026-09-28 08:00:00",
        "user_id": "2218417011733",
        "user_nickname": "张三",
        "user_avatar": "https://img.alicdn.com/bao/avatar.webp",
        "user_link": "https://www.goofish.com/personal?userId=2218417011733",
        "creator_hash": "hash",
        "seller_location": "上海",
        "seller_last_active": "10分钟前来过",
        "seller_join_time": "来闲鱼2年",
        "seller_sold_count": "卖出1878件宝贝",
        "seller_good_rate": "好评率98%",
        "source_keyword": "耳机",
        "last_modify_ts": 1,
    }

    await store.store_content(dict(item))
    await store.store_content({**item, "title": "new", "last_modify_ts": 2})

    async with get_session() as session:
        count = await session.scalar(select(func.count()).select_from(GoofishItem))
        row = (await session.execute(select(GoofishItem))).scalars().one()

    assert count == 1
    assert row.title == "new"
    assert row.user_id == "2218417011733"
    assert row.user_avatar == "https://img.alicdn.com/bao/avatar.webp"
    assert row.user_link == "https://www.goofish.com/personal?userId=2218417011733"
    assert row.original_price == "199"
    assert row.seller_good_rate == "好评率98%"
    assert row.add_ts
