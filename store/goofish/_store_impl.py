# -*- coding: utf-8 -*-

from typing import Dict

from sqlalchemy import select

from base.base_crawler import AbstractStore
from database.db_session import get_session
from database.models import GoofishItem
from database.mongodb_store_base import MongoDBStoreBase
from store.excel_store_base import ExcelStoreBase
from tools import utils
from tools.async_file_writer import AsyncFileWriter
from var import crawler_type_var


class GooFishCsvStoreImplement(AbstractStore):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.writer = AsyncFileWriter(platform="goofish", crawler_type=crawler_type_var.get())

    async def store_content(self, content_item: Dict):
        await self.writer.write_to_csv(item_type="contents", item=content_item)

    async def store_comment(self, comment_item: Dict):
        pass

    async def store_creator(self, creator: Dict):
        pass


class GooFishJsonStoreImplement(AbstractStore):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.writer = AsyncFileWriter(platform="goofish", crawler_type=crawler_type_var.get())

    async def store_content(self, content_item: Dict):
        await self.writer.write_single_item_to_json(item_type="contents", item=content_item)

    async def store_comment(self, comment_item: Dict):
        pass

    async def store_creator(self, creator: Dict):
        pass


class GooFishJsonlStoreImplement(AbstractStore):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.writer = AsyncFileWriter(platform="goofish", crawler_type=crawler_type_var.get())

    async def store_content(self, content_item: Dict):
        await self.writer.write_to_jsonl(item_type="contents", item=content_item)

    async def store_comment(self, comment_item: Dict):
        pass

    async def store_creator(self, creator: Dict):
        pass


class GooFishDbStoreImplement(AbstractStore):
    async def store_content(self, content_item: Dict):
        item_id = content_item.get("item_id")
        if not item_id:
            return
        async with get_session() as session:
            stmt = select(GoofishItem).where(GoofishItem.item_id == item_id)
            res = await session.execute(stmt)
            db_item = res.scalar_one_or_none()
            if db_item:
                for key, value in content_item.items():
                    if key != "add_ts":
                        setattr(db_item, key, value)
            else:
                content_item["add_ts"] = content_item.get("add_ts") or utils.get_current_timestamp()
                session.add(GoofishItem(**content_item))

    async def store_comment(self, comment_item: Dict):
        pass

    async def store_creator(self, creator: Dict):
        pass


class GooFishSqliteStoreImplement(GooFishDbStoreImplement):
    pass


class GooFishMongoStoreImplement(AbstractStore):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.mongo_store = MongoDBStoreBase(collection_prefix="goofish")

    async def store_content(self, content_item: Dict):
        item_id = content_item.get("item_id")
        if not item_id:
            return
        await self.mongo_store.save_or_update(
            collection_suffix="contents",
            query={"item_id": item_id},
            data=content_item,
        )

    async def store_comment(self, comment_item: Dict):
        pass

    async def store_creator(self, creator: Dict):
        pass


class GooFishExcelStoreImplement:
    def __new__(cls, *args, **kwargs):
        return ExcelStoreBase.get_instance(
            platform="goofish",
            crawler_type=crawler_type_var.get(),
        )
