# -*- coding: utf-8 -*-

from typing import List

import config
from base.base_crawler import AbstractStore
from model.m_qimai import QimaiApp, QimaiComment
from tools import utils
from var import source_keyword_var

from ._store_impl import *


class QimaiStoreFactory:
    STORES = {
        "csv": QimaiCsvStoreImplement,
        "db": QimaiDbStoreImplement,
        "postgres": QimaiDbStoreImplement,
        "json": QimaiJsonStoreImplement,
        "jsonl": QimaiJsonlStoreImplement,
        "sqlite": QimaiSqliteStoreImplement,
        "mongodb": QimaiMongoStoreImplement,
        "excel": QimaiExcelStoreImplement,
    }

    @staticmethod
    def create_store() -> AbstractStore:
        store_class = QimaiStoreFactory.STORES.get(config.SAVE_DATA_OPTION)
        if not store_class:
            raise ValueError("[QimaiStoreFactory.create_store] Invalid save option")
        return store_class()


async def batch_update_qimai_apps(app_list: List[QimaiApp]):
    for app in app_list or []:
        await update_qimai_app(app)


async def update_qimai_app(app: QimaiApp):
    save_item = app.model_dump()
    save_item["source_keyword"] = source_keyword_var.get()
    save_item["last_modify_ts"] = utils.get_current_timestamp()
    utils.logger.info(f"[store.qimai.update_qimai_app] qimai app: {save_item}")
    await QimaiStoreFactory.create_store().store_content(save_item)


async def batch_update_qimai_comments(comment_list: List[QimaiComment]):
    for comment in comment_list or []:
        await update_qimai_comment(comment)


async def update_qimai_comment(comment: QimaiComment):
    save_item = comment.model_dump()
    save_item["source_keyword"] = source_keyword_var.get()
    save_item["last_modify_ts"] = utils.get_current_timestamp()
    utils.logger.info(f"[store.qimai.update_qimai_comment] qimai comment: {save_item}")
    await QimaiStoreFactory.create_store().store_comment(save_item)
