# -*- coding: utf-8 -*-

from typing import List

import config
from base.base_crawler import AbstractStore
from model.m_goofish import GoofishItem
from tools import utils
from var import source_keyword_var

from ._store_impl import *


class GooFishStoreFactory:
    STORES = {
        "csv": GooFishCsvStoreImplement,
        "db": GooFishDbStoreImplement,
        "postgres": GooFishDbStoreImplement,
        "json": GooFishJsonStoreImplement,
        "jsonl": GooFishJsonlStoreImplement,
        "sqlite": GooFishSqliteStoreImplement,
        "mongodb": GooFishMongoStoreImplement,
        "excel": GooFishExcelStoreImplement,
    }

    @staticmethod
    def create_store() -> AbstractStore:
        store_class = GooFishStoreFactory.STORES.get(config.SAVE_DATA_OPTION)
        if not store_class:
            raise ValueError("[GooFishStoreFactory.create_store] Invalid save option")
        return store_class()


async def batch_update_goofish_items(item_list: List[GoofishItem]):
    for item in item_list or []:
        await update_goofish_item(item)


async def update_goofish_item(item: GoofishItem):
    save_item = item.model_dump()
    save_item["source_keyword"] = source_keyword_var.get()
    save_item["last_modify_ts"] = utils.get_current_timestamp()
    utils.logger.info(f"[store.goofish.update_goofish_item] goofish item: {save_item}")
    await GooFishStoreFactory.create_store().store_content(save_item)
