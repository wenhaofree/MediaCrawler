# -*- coding: utf-8 -*-

from typing import Dict

from sqlalchemy import select

from base.base_crawler import AbstractStore
from database.db_session import get_session
from database.models import QimaiApp
from database.mongodb_store_base import MongoDBStoreBase
from store.excel_store_base import ExcelStoreBase
from tools import utils
from tools.async_file_writer import AsyncFileWriter
from var import crawler_type_var


class QimaiCsvStoreImplement(AbstractStore):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.writer = AsyncFileWriter(platform="qimai", crawler_type=crawler_type_var.get())

    async def store_content(self, content_item: Dict):
        await self.writer.write_to_csv(item_type="contents", item=content_item)

    async def store_comment(self, comment_item: Dict):
        pass

    async def store_creator(self, creator: Dict):
        pass


class QimaiJsonStoreImplement(AbstractStore):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.writer = AsyncFileWriter(platform="qimai", crawler_type=crawler_type_var.get())

    async def store_content(self, content_item: Dict):
        await self.writer.write_single_item_to_json(item_type="contents", item=content_item)

    async def store_comment(self, comment_item: Dict):
        pass

    async def store_creator(self, creator: Dict):
        pass


class QimaiJsonlStoreImplement(AbstractStore):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.writer = AsyncFileWriter(platform="qimai", crawler_type=crawler_type_var.get())

    async def store_content(self, content_item: Dict):
        await self.writer.write_to_jsonl(item_type="contents", item=content_item)

    async def store_comment(self, comment_item: Dict):
        pass

    async def store_creator(self, creator: Dict):
        pass


class QimaiDbStoreImplement(AbstractStore):
    async def store_content(self, content_item: Dict):
        app_id = content_item.get("app_id")
        if not app_id:
            return
        async with get_session() as session:
            stmt = select(QimaiApp).where(QimaiApp.app_id == app_id)
            res = await session.execute(stmt)
            db_item = res.scalar_one_or_none()
            if db_item:
                for key, value in content_item.items():
                    if key != "add_ts":
                        setattr(db_item, key, value)
            else:
                content_item["add_ts"] = content_item.get("add_ts") or utils.get_current_timestamp()
                session.add(QimaiApp(**content_item))

    async def store_comment(self, comment_item: Dict):
        pass

    async def store_creator(self, creator: Dict):
        pass


class QimaiSqliteStoreImplement(QimaiDbStoreImplement):
    pass


class QimaiMongoStoreImplement(AbstractStore):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.mongo_store = MongoDBStoreBase(collection_prefix="qimai")

    async def store_content(self, content_item: Dict):
        app_id = content_item.get("app_id")
        if not app_id:
            return
        await self.mongo_store.save_or_update(
            collection_suffix="contents",
            query={"app_id": app_id},
            data=content_item,
        )

    async def store_comment(self, comment_item: Dict):
        pass

    async def store_creator(self, creator: Dict):
        pass


class QimaiExcelStoreImplement:
    def __new__(cls, *args, **kwargs):
        return ExcelStoreBase.get_instance(
            platform="qimai",
            crawler_type=crawler_type_var.get(),
        )
